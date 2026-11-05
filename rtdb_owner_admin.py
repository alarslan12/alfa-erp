"""Owner-only Firebase RTDB administration without Supabase or secret keys."""
from __future__ import annotations
import base64
import copy
from datetime import datetime, timezone
import uuid

from alfa_rtdb import DeviceError, Workstation, WORKSPACE_ID
from inventory_batches import stock_batches, batch_stock_quantity


def _owner(client):
    if not client.paired:
        raise DeviceError("Önce Firebase cihazını etkinleştir.")
    me = client._get("members/" + client.uid)
    if not isinstance(me, dict) or me.get("role") != "owner" or me.get("active") is not True:
        raise DeviceError("Bu işlem yalnızca yetkili Yönetici cihazında yapılabilir.", 403)


def _catalog(client, incoming):
    if not isinstance(incoming,list) or not 1 <= len(incoming) <= 2000:
        raise DeviceError("Katalog 1-2000 kitap içermeli.", 422)
    codes = [str(x.get("code") or "").strip() for x in incoming]
    if not all(codes) or len(set(codes)) != len(codes):
        raise DeviceError("Katalogda tekrarlanan veya boş kitap kodu var", 422)
    if any(any(c in x for c in '.#$[]/') for x in codes):
        raise DeviceError("Firebase'de kullanılamayan kitap kodu.", 422)
    current=client._get("books") or {}
    by_code={str(book.get("code")):(id,book) for id,book in current.items()}
    fresh={}
    public={}
    now=datetime.now(timezone.utc).isoformat()
    for incoming_row in incoming:
        code=str(incoming_row["code"]).strip()
        old_id,old=by_code.get(code,(str(uuid.uuid4()),{}))
        row={**old, "id":old_id, "workspace_id":WORKSPACE_ID,
             "code":code, "name":str(incoming_row["name"])[:350],
             "group_name":str(incoming_row.get("group_name") or "")[:200],
             "page_count":int(incoming_row.get("page_count") or 0),
             "supports_color":bool(incoming_row.get("supports_color")),
             "is_active":True, "updated_at":now,
             "version":int(old.get("version") or 0)+1,
             "created_at":old.get("created_at") or now}
        if row["page_count"] < 0:
            raise DeviceError("Sayfa sayısı geçersiz", 422)
        fresh[old_id]=row
        public[code]={k:row[k] for k in (
            "code","name","group_name","page_count","supports_color")}
    for id,book in current.items():
        if id not in fresh:
            fresh[id]={**book,"is_active":False,"updated_at":now,
                       "version":int(book.get("version") or 0)+1}
    # No blanket parent PUT (which could bypass audit or erase children):
    # write each permitted book location, then public catalogue.
    for id,row in fresh.items():
        client._request("PUT","books/"+id,row)
    client._request("PUT","public_catalog",public)
    client._catalog_cache=public
    client._bump("catalog")
    return {"count":len(public)}


def _upsert_product(client,product):
    """Edit master-product metadata without touching quantities or batches."""
    if not isinstance(product,dict):
        raise DeviceError("Ürün bilgileri geçersiz",422)
    pid=str(product.get("id") or uuid.uuid4())
    if not pid or any(ch in pid for ch in ".#$[]/"):
        raise DeviceError("Geçersiz ürün kimliği",422)
    title=str(product.get("title") or "").strip()
    if not title:
        raise DeviceError("Ürün adı zorunlu",422)
    allowed=("sku","title","category","tags","description",
             "attributes","image_url","active")
    for _ in range(8):
        old,etag,_=client._request("GET","inventory/products/"+pid,etag=True)
        if old is not None and not isinstance(old,dict):
            raise DeviceError("Ürün kaydı bozuk",422)
        now=datetime.now(timezone.utc).isoformat()
        fresh=copy.deepcopy(old) if old else {
            "quantity":0,"cost_price":0.0,"sale_price":0.0,
            "in_inventory":False,"sales_history":{}}
        for key in allowed:
            if key in product:
                fresh[key]=copy.deepcopy(product[key])
        fresh.update(id=pid,title=title,workspace_id=WORKSPACE_ID,
                     updated_at=now,created_at=(old or {}).get("created_at") or now)
        fresh["version"]=int((old or {}).get("version") or 0)+1
        if old is None:
            fresh["in_inventory"]=False
        try:
            client._request("PUT","inventory/products/"+pid,fresh,match=etag)
            try:client._bump("inventory")
            except DeviceError:pass
            return {"product":fresh}
        except DeviceError as exc:
            if exc.status!=409:raise
    raise DeviceError("Ürün eşzamanlı düzenleniyor; yeniden deneyin",409)



def _archive_product(client,product_id,active):
    """Soft archive/restore; never remove purchases or sales from Firebase."""
    pid=str(product_id or "")
    if not pid:
        raise DeviceError("Ürün kimliği gerekli",422)
    for _ in range(8):
        old,etag,_=client._request("GET","inventory/products/"+pid,etag=True)
        if not isinstance(old,dict):
            raise DeviceError("Ürün bulunamadı",404)
        updated=copy.deepcopy(old)
        now=datetime.now(timezone.utc).isoformat()
        updated["active"]=bool(active)
        updated["archived_at"]=None if active else now
        updated["archived_by"]=None if active else client.uid
        updated["version"]=int(old.get("version") or 0)+1
        updated["updated_at"]=now
        try:
            client._request("PUT","inventory/products/"+pid,updated,match=etag)
            try:client._bump("inventory")
            except DeviceError:pass
            return {"active":bool(active),"product_id":pid}
        except DeviceError as exc:
            if exc.status!=409:raise
    raise DeviceError("Ürün başka cihazda değiştiriliyor; yeniden dene",409)


def _cancel_sale(client,product_id,sale_id,reason):
    """Compensate a completed sale inside ONE conditional product write.

    Keep the original sale, purchase lot and costs for immutable audit.
    Exactly one reversal is possible, even when two owners click together.
    """
    pid=str(product_id or "")
    sid=str(sale_id or "")
    reason=str(reason or "").strip()[:180]
    if not pid or not sid or not reason:
        raise DeviceError("Satış, ürün ve iptal nedeni zorunludur",422)
    for _ in range(8):
        old,etag,_=client._request("GET","inventory/products/"+pid,etag=True)
        if not isinstance(old,dict):
            raise DeviceError("Satışa ait ürün bulunamadı",404)
        updated=copy.deepcopy(old)
        history=updated.get("sales_history") or {}
        sale=history.get(sid)
        if not isinstance(sale,dict):
            raise DeviceError("Bu satış kaydı bulunamadı",404)
        if sale.get("cancelled_at"):
            return {"already_cancelled":True,"sale_id":sid}
        batches=stock_batches(updated)
        lot_id=str(sale.get("batch_id") or "")
        batch=batches.get(lot_id)
        if not isinstance(batch,dict):
            raise DeviceError("Eski alım partisi bulunamadı; otomatik iptal güvenli değil",409)
        qty=int(sale.get("quantity") or 0)
        total=int(batch.get("quantity") or 0)
        remaining=int(batch.get("remaining") or 0)
        if qty<1 or remaining<0 or remaining+qty>total:
            raise DeviceError("Stok hareketleri tutarsız; iptal için manuel inceleme gerekli",409)
        if batch_stock_quantity(updated)!=int(updated.get("quantity") or 0):
            raise DeviceError("Stok ve parti toplamları farklı; iptal engellendi",409)
        batch["remaining"]=remaining+qty
        batches[lot_id]=batch
        now=datetime.now(timezone.utc).isoformat()
        sale.update(cancelled_at=now,cancelled_by=client.uid,cancel_reason=reason)
        history[sid]=sale
        updated.update(stock_batches=batches,sales_history=history,
                       quantity=int(old.get("quantity") or 0)+qty,
                       updated_at=now,version=int(old.get("version") or 0)+1)
        try:
            client._request("PUT","inventory/products/"+pid,updated,match=etag)
            try:client._bump("inventory")
            except DeviceError:pass
            return {"cancelled":True,"sale_id":sid,"restored_quantity":qty}
        except DeviceError as exc:
            if exc.status!=409:raise
    raise DeviceError("İptal sırasında eşzamanlı stok değişikliği; yeniden dene",409)


def _acquire_product(client,product_id,quantity,unit_cost):
    """Owner adds a distinct timestamped purchase-cost batch with ETag CAS."""
    pid=str(product_id or "")
    try:
        qty=int(quantity)
        cost=round(float(unit_cost),2)
    except (TypeError,ValueError,OverflowError):
        raise DeviceError("Alım adedi veya maliyeti geçersiz",422) from None
    if qty<1 or qty>100000 or not 0<=cost<=999999999:
        raise DeviceError("Alım adedi veya maliyeti geçersiz",422)
    batch_id=str(uuid.uuid4())
    for _ in range(8):
        current,etag,_=client._request("GET","inventory/products/"+pid,etag=True)
        if not isinstance(current,dict) or not current.get("active",True):
            raise DeviceError("Katalog ürünü bulunamadı",404)
        fresh=copy.deepcopy(current)
        if batch_stock_quantity(fresh)!=int(fresh.get("quantity") or 0):
            raise DeviceError("Stok toplamı ile parti kayıtları uyuşmuyor",409)
        batches=stock_batches(fresh)
        now=datetime.now(timezone.utc).isoformat()
        batch={"id":batch_id,"quantity":qty,"remaining":qty,
               "unit_cost":cost,"received_at":now,"device_id":client.uid}
        batches[batch_id]=batch
        fresh.update(stock_batches=batches,
                     quantity=int(fresh.get("quantity") or 0)+qty,
                     cost_price=cost,in_inventory=True,
                     updated_at=now,version=int(fresh.get("version") or 0)+1)
        try:
            client._request("PUT","inventory/products/"+pid,fresh,match=etag)
            try:client._bump("inventory")
            except DeviceError:pass
            return {"product_id":pid,"batch":batch,"quantity":fresh["quantity"]}
        except DeviceError as exc:
            if exc.status!=409:raise
    raise DeviceError("Stok başka bilgisayarda değişti; yeniden deneyin",409)



def _void_acquisition(client,product_id,batch_id,reason):
    """Undo a mistaken, fully unused purchase lot without deleting its audit."""
    pid=str(product_id or "")
    bid=str(batch_id or "")
    reason=str(reason or "").strip()[:180]
    if not pid or not bid or not reason:
        raise DeviceError("Ürün, parti ve iptal gerekçesi gerekli",422)
    for _ in range(8):
        current,etag,_=client._request("GET","inventory/products/"+pid,etag=True)
        if not isinstance(current,dict):
            raise DeviceError("Envanter ürünü bulunamadı",404)
        batches=stock_batches(current)
        # Virtual legacy batches must not be rewritten as new acquisitions.
        raw_batches=current.get("stock_batches")
        lot=batches.get(bid)
        if not isinstance(raw_batches,dict) or bid not in raw_batches or not isinstance(lot,dict):
            raise DeviceError("Bu alım partisi geri alınabilir bir kayıt değil",409)
        if lot.get("voided_at"):
            return {"already_voided":True,"product_id":pid,"batch_id":bid}
        amount=int(lot.get("quantity") or 0)
        remaining=int(lot.get("remaining") or 0)
        if lot.get("legacy") or amount<=0 or remaining!=amount:
            raise DeviceError("Bu partiden satış yapılmış veya stok kullanılmış; önce ilgili işlemleri düzeltin",409)
        # A completed or reversed sale is part of the audit chain. Refuse
        # automatic withdrawal of an acquisition referenced by any sale.
        history=current.get("sales_history") or {}
        if any(isinstance(sale,dict) and str(sale.get("batch_id"))==bid
               for sale in history.values()):
            raise DeviceError("Partiye bağlı satış geçmişi var; otomatik alım iptali güvenli değil",409)
        if batch_stock_quantity(current)!=int(current.get("quantity") or 0):
            raise DeviceError("Parti toplamı ile mevcut stok uyuşmuyor",409)
        updated=copy.deepcopy(current)
        modified=stock_batches(updated)
        now=datetime.now(timezone.utc).isoformat()
        modified[bid].update(remaining=0,voided_at=now,
                             voided_by=client.uid,void_reason=reason)
        updated.update(stock_batches=modified,
                       quantity=int(current.get("quantity") or 0)-amount,
                       updated_at=now,
                       version=int(current.get("version") or 0)+1)
        try:
            client._request("PUT","inventory/products/"+pid,updated,match=etag)
            try:client._bump("inventory")
            except DeviceError:pass
            return {"product_id":pid,"batch_id":bid,
                    "voided_quantity":amount}
        except DeviceError as exc:
            if exc.status!=409:raise
    raise DeviceError("Stok başka bir cihazda değiştirildi; yeniden deneyin",409)


def _remove_from_inventory(client,product_id):
    """Hide a zero-stock item from inventory; retain the master and history."""
    pid=str(product_id or "")
    if not pid:raise DeviceError("Ürün kimliği gerekli",422)
    for _ in range(8):
        current,etag,_=client._request("GET","inventory/products/"+pid,etag=True)
        if not isinstance(current,dict):
            raise DeviceError("Ürün bulunamadı",404)
        if current.get("in_inventory") is False:
            return {"already_removed":True,"product_id":pid}
        if int(current.get("quantity") or 0)!=0 or batch_stock_quantity(current)!=0:
            raise DeviceError("Envanterden çıkarmak için mevcut stok 0 olmalı. Yanlış alım partisini önce geri alın.",409)
        updated=copy.deepcopy(current)
        now=datetime.now(timezone.utc).isoformat()
        updated.update(in_inventory=False,inventory_removed_at=now,
                       inventory_removed_by=client.uid,
                       updated_at=now,version=int(current.get("version") or 0)+1)
        try:
            client._request("PUT","inventory/products/"+pid,updated,match=etag)
            try:client._bump("inventory")
            except DeviceError:pass
            return {"removed":True,"product_id":pid}
        except DeviceError as exc:
            if exc.status!=409:raise
    raise DeviceError("Envanter ürünü başka cihazda değiştirildi; yeniden deneyin",409)


def _payment(client,days,paid,fingerprints):
    rows=client._get("accounting") or {}
    existing={str(v.get("accounting_day")):v for v in rows.values()}
    now=datetime.now(timezone.utc).isoformat()
    result=[]
    for day in days:
        day=str(day)
        previous=existing.get(day)
        fingerprint=str((fingerprints or {}).get(day) or "")
        if previous and previous.get("completion_fingerprint") not in (
              None, "", fingerprint):
            raise DeviceError("Muhasebe günü değişmiş; yeniden hesaplayın", 409)
        uid=str(uuid.uuid5(uuid.UUID(WORKSPACE_ID),"accounting:"+day))
        row={**(previous or {}),"id":(previous or {}).get("id") or uid,
             "workspace_id":WORKSPACE_ID,"accounting_day":day,
             "paid":bool(paid), "completion_fingerprint":fingerprint,
             "paid_at":now if paid else None, "updated_at":now}
        client._request("PUT","accounting/"+str(row["id"]),row)
        result.append(row)
    # Accounting is included in the order revision snapshot protocol.
    client._bump("orders")
    return {"accounting_days":list((client._get("accounting") or {}).values())}


def admin_request(cloud,action,timeout=None,**kwargs):
    client=cloud if isinstance(cloud,Workstation) else Workstation()
    _owner(client)
    if action=="admin_catalog":
        return _catalog(client,kwargs.get("books"))
    if action=="admin_devices":
        members=client._get("members") or {}
        requests=client._get("device_requests") or {}
        return {"devices":[{"id":uid, "device_name":row.get("name") or
                (requests.get(uid) or {}).get("name") or uid,
                "active":bool(row.get("active")),
                "device_role":row.get("role"),
                "last_seen_at":row.get("last_seen_at")}
                for uid,row in members.items() if isinstance(row,dict)]}
    if action=="admin_revoke":
        uid=str(kwargs.get("id") or "")
        if not uid or uid==client.uid:
            raise DeviceError("Kendi yönetici cihazını iptal edemezsin", 422)
        old=client._get("members/"+uid)
        if not old:
            raise DeviceError("Cihaz bulunamadı", 404)
        client._request("PUT","members/"+uid,{**old,"active":False})
        return {"revoked":True}
    if action=="admin_audit":
        # Archive from Supabase migration is intentionally NOT readable by
        # staff/owner RTDB rules. Fetching it used to return HTTP 401, falsely
        # shown as "Firebase oturumu gecersiz".
        # Only user-requested refresh accesses this data; no background loop.
        orders=client._get("orders") or {}
        activities=[]
        for row in orders.values():
            if not isinstance(row,dict):continue
            for event in (row.get("event_log") or {}).values():
                if isinstance(event,dict):activities.append(event)
        # Old imported audit records can be large; read only once on demand.
        # Production reset removes legacy audit while preserving book catalog.
        audit=client._get("audit") or {}
        return {"device_activity":activities,
                "audit_events":list(audit.values()) if isinstance(audit,dict) else []}
    if action=="admin_inventory_upsert":
        return _upsert_product(client,kwargs.get("product"))
    if action=="admin_inventory_archive":
        return _archive_product(client,kwargs.get("product_id"),kwargs.get("active"))
    if action=="admin_inventory_cancel_sale":
        return _cancel_sale(client,kwargs.get("product_id"),
                            kwargs.get("sale_id"),kwargs.get("reason"))
    if action=="admin_inventory_void_acquisition":
        return _void_acquisition(client,kwargs.get("product_id"),
                                 kwargs.get("batch_id"),kwargs.get("reason"))
    if action=="admin_inventory_remove":
        return _remove_from_inventory(client,kwargs.get("product_id"))
    if action=="admin_inventory_acquire":
        return _acquire_product(client,kwargs.get("product_id"),
                                kwargs.get("quantity"),kwargs.get("unit_cost"))
    if action=="admin_inventory_image":
        if kwargs.get("mime")!="image/jpeg":
            raise DeviceError("Sadece JPEG görsel destekleniyor",422)
        data=str(kwargs.get("image_base64") or "")
        try:picture=base64.b64decode(data,validate=True)
        except Exception:raise DeviceError("Resim verisi geçersiz",422) from None
        if not 0<len(picture)<=262144:
            raise DeviceError("Firebase ücretsiz kota için görsel en fazla 256KB olmalı",413)
        # Embedding a tiny image is intentionally explicit: avoids needing
        # paid Cloud Storage for Firebase. Never store Admin SDK credentials.
        return {"url":"data:image/jpeg;base64,"+data}
    if action=="admin_payment":
        return _payment(client,kwargs.get("days") or [],kwargs.get("paid"),
                        kwargs.get("fingerprints") or {})
    if action=="admin_setup_code":
        raise DeviceError(
            "Firebase'de kurulum kodu gerekmez. Personel uygulamasını kurup "
            "Cihaz yetkisi düğmesinden UID'yi oluşturun; Yönetici panelinden onaylayın.")
    raise DeviceError("Bu yönetici işlemi Firebase'de henüz etkin değil: "+str(action),503)
