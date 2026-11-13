"""Owner-only Firebase RTDB administration with Firebase Rules and no embedded admin secrets."""
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


def staff_catalog_import(client, incoming):
    """Approved staff/owner may update books but not other admin settings."""
    if not isinstance(client,Workstation) or not client.paired:
        raise DeviceError("Önce Firebase cihaz yetkisini etkinleştir.",403)
    member=client._get("members/"+client.uid)
    if not isinstance(member,dict) or member.get("active") is not True or member.get("role") not in ("staff","owner"):
        raise DeviceError("Excel yükleme için onaylı Personel/Yönetici yetkisi gerekli.",403)
    return _catalog(client,incoming)


def _catalog(client, incoming):
    """Replace the active Firebase book catalog by the Excel's BOOK CODE.

    Never map titles by array position: older RTDB imports shifted code 508/
    509/510 while still looking plausible in the card list. Do not publish a
    new revision until the server confirms all active books and mobile data.
    """
    from pathlib import Path
    import json
    import os
    import tempfile
    from cihaz_sifreleme import DATA

    if not isinstance(incoming,list) or not 1 <= len(incoming) <= 2000:
        raise DeviceError("Katalog 1–2000 kitap içermeli.",422)
    prepared={}
    for raw in incoming:
        if not isinstance(raw,dict):
            raise DeviceError("Excel kitap kaydı geçersiz.",422)
        code=str(raw.get("code") or "").strip()
        name=str(raw.get("name") or "").strip()
        if not code or not name or len(code)>80 or len(name)>350:
            raise DeviceError("Excel'de kodu veya adı boş/geçersiz kitap var.",422)
        if any(ch in code for ch in '.#$[]/') or code in prepared:
            raise DeviceError("Tekrarlanan veya Firebase'de geçersiz kitap kodu: "+code,422)
        try:
            pages=int(raw.get("page_count") or 0)
        except (TypeError,ValueError,OverflowError):
            raise DeviceError("Sayfa sayısı geçersiz: "+code,422) from None
        if pages<0 or pages>100000:
            raise DeviceError("Sayfa sayısı aralık dışında: "+code,422)
        prepared[code]={
            "code":code,"name":name,
            "group_name":str(raw.get("group_name") or "Tekil Kitaplar")[:200],
            "page_count":pages,
            "supports_color":bool(raw.get("supports_color")),
        }
    current=client._get("books") or {}
    if not isinstance(current,dict):
        raise DeviceError("Firebase kitap arşivi beklenmeyen biçimde; yazma yapılmadı.",422)
    prev_public=client._get("public_catalog")
    if not isinstance(prev_public,(dict,list,type(None))):
        raise DeviceError("Firebase mobil katalog biçimi geçersiz; yazma yapılmadı.",422)

    # Preserve the old catalog as a local recoverable backup before ANY write.
    backup_dir=Path(DATA)/"catalog_backups"
    backup_dir.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat()
    with tempfile.NamedTemporaryFile(
            mode="w",encoding="utf-8",prefix="before_excel_",
            suffix=".json",dir=backup_dir,delete=False) as snapshot:
        json.dump({"saved_at":now,"workspace_id":WORKSPACE_ID,
                   "books":current,"public_catalog":prev_public},
                  snapshot,ensure_ascii=False)
        backup_path=snapshot.name
    os.chmod(backup_path,0o600)

    grouped={}
    for uid,old in current.items():
        if not isinstance(old,dict):continue
        code=str(old.get("code") or "").strip()
        if code:grouped.setdefault(code,[]).append((uid,old))
    updates={};public={}
    for code,book in prepared.items():
        candidates=grouped.get(code,[])
        # Reuse the record with the matching book name if present, otherwise
        # keep a stable existing UUID. All duplicates become inactive.
        ordered=sorted(candidates,key=lambda x:(
            str(x[1].get("name") or "").casefold()!=book["name"].casefold(),
            x[1].get("is_active") is not True,str(x[0])))
        chosen_id,previous=(ordered[0] if ordered else (str(uuid.uuid4()),{}))
        pages=book["page_count"]
        # Blank/unknown page count does not erase a valid previous page count
        # when both code and title match. A renamed code needs Excel authority.
        if pages==0 and previous.get("name")==book["name"]:
            pages=max(0,int(previous.get("page_count") or 0))
        book=dict(book,page_count=pages)
        public[code]=dict(book)
        data={**previous,**book,
              "id":chosen_id,"workspace_id":WORKSPACE_ID,
              "is_active":True,"updated_at":now,
              "created_at":previous.get("created_at") or now,
              "version":int(previous.get("version") or 0)+1}
        if any(data.get(k)!=previous.get(k) for k in
               ("code","name","group_name","page_count","supports_color","is_active")):
            updates[chosen_id]=data
        for duplicate_id,duplicate in ordered[1:]:
            if duplicate.get("is_active") is not False:
                updates[duplicate_id]={**duplicate,"is_active":False,
                                      "updated_at":now,
                                      "version":int(duplicate.get("version") or 0)+1}
    for uid,old in current.items():
        if not isinstance(old,dict):continue
        if str(old.get("code") or "") not in prepared and old.get("is_active") is not False:
            updates[uid]={**old,"is_active":False,"updated_at":now,
                          "version":int(old.get("version") or 0)+1}

    # A single PATCH avoids an hours-long 500-item update and is atomic for
    # the books subtree. Some older rules reject parent PATCH while allowing
    # child PUT; in that case retry only at individual permitted leaf paths.
    if updates:
        try:
            client._request("PATCH","books",updates,timeout=45)
        except DeviceError as error:
            if error.status not in (400,403,405):
                raise
            for uid,data in updates.items():
                client._request("PUT","books/"+uid,data)

    actual=client._get("books") or {}
    if not isinstance(actual,dict):
        raise DeviceError("Katalog doğrulanamadı; eski yedek korundu.",409)
    active={}
    for row in actual.values():
        if not isinstance(row,dict) or row.get("is_active") is not True:
            continue
        code=str(row.get("code") or "").strip()
        if code in active:
            raise DeviceError("Bulutta yinelenen aktif kitap kodu "+code+
                              "; önceki katalog yedeği korundu.",409)
        active[code]=row
    if set(active)!=set(public):
        raise DeviceError("Katalog sunucu doğrulaması başarısız: "+
                          str(len(active))+" aktif / "+str(len(public))+
                          " Excel kitabı. Önceki yedek korundu.",409)
    for code,book in public.items():
        remote=active[code]
        if any(remote.get(k)!=book.get(k) for k in book):
            raise DeviceError("Firebase kitap kodu "+code+
                              " Excel'deki bilgiyle uyuşmuyor; yedek korundu.",409)

    # RTDB can decode dense numeric-key maps as JSON arrays, so normalize
    # readback by each book's explicit code instead of list indexes.
    def as_code_map(raw):
        rows=raw.values() if isinstance(raw,dict) else raw
        return {str(row["code"]):row for row in (rows or [])
                if isinstance(row,dict) and row.get("code") is not None}

    client._request("PUT","public_catalog",public)
    public_readback=as_code_map(client._get("public_catalog"))
    if public_readback!=public:
        raise DeviceError("Mobil katalog yazıldı ancak doğrulanamadı; "
                          "revizyon artırılmadı, yedek saklandı.",409)
    client._bump("catalog")
    client._catalog_cache=public
    return {"count":len(public),"updated":len(updates),
            "verified":True,"backup":str(backup_path)}


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
    if action=="admin_prune_devices":
        members=client._get("members") or {}
        if not isinstance(members,dict):
            raise DeviceError("Cihaz kayıtları okunamadı",422)
        candidates=[uid for uid,record in members.items()
                    if isinstance(record,dict) and record.get("active") is False
                    and uid!=client.uid][:80]
        removed=0
        for uid in candidates:
            record=client._get("members/"+uid)
            if not isinstance(record,dict) or record.get("active") is not False:
                continue
            client._request("DELETE","members/"+uid)
            try:
                client._request("DELETE","device_requests/"+uid)
            except DeviceError:
                pass
            removed+=1
        return {"removed":removed}
    if action=="admin_delete_error":
        key=str(kwargs.get("id") or "")
        if not key or len(key)>90 or any(c in key for c in ".#$[]/"):
            raise DeviceError("Hata raporu kimliği geçersiz",422)
        if client._get("error_acks/"+key) is not None:
            client._request("DELETE","error_acks/"+key)
        client._request("DELETE","error_reports/"+key)
        return {"deleted":1}
    if action=="admin_purge_reviewed_errors":
        ids=kwargs.get("ids")
        if not isinstance(ids,list) or len(ids)>70:
            raise DeviceError("En fazla 70 hata kaydı temizlenebilir",422)
        reviewed=client.read_error_acks()
        removed=0
        for raw in list(dict.fromkeys(ids)):
            key=str(raw)
            if not key or len(key)>90 or any(c in key for c in ".#$[]/"):
                continue
            if key not in reviewed:
                continue
            client._request("DELETE","error_acks/"+key)
            client._request("DELETE","error_reports/"+key)
            removed+=1
        return {"removed":removed}
    if action=="admin_audit":
        # Archived legacy records are intentionally NOT readable by
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
