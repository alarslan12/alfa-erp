"""Owner-only Firebase RTDB administration without Supabase or secret keys."""
from __future__ import annotations
import base64
import copy
from datetime import datetime, timezone
import uuid

from alfa_rtdb import DeviceError, Workstation, WORKSPACE_ID


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
    if not isinstance(product,dict):
        raise DeviceError("Ürün bilgileri geçersiz", 422)
    pid=str(product.get("id") or uuid.uuid4())
    if not pid or any(c in pid for c in '.#$[]/'):
        raise DeviceError("Geçersiz ürün kimliği", 422)
    title=str(product.get("title") or "").strip()
    if not title:
        raise DeviceError("Ürün adı zorunlu", 422)
    for _ in range(8):
        old,etag,_=client._request("GET","inventory/products/"+pid,etag=True)
        now=datetime.now(timezone.utc).isoformat()
        fresh={**(old or {}),**product,"id":pid,"title":title,
               "workspace_id":WORKSPACE_ID,"updated_at":now,
               "created_at":(old or {}).get("created_at") or now}
        fresh["version"]=int((old or {}).get("version") or 0)+1
        fresh["quantity"]=max(0,int(fresh.get("quantity") or 0))
        try:
            client._request("PUT","inventory/products/"+pid,fresh,match=etag)
            client._bump("inventory")
            return {"product":fresh}
        except DeviceError as error:
            if error.status!=409:raise
    raise DeviceError("Ürün eşzamanlı düzenleniyor; tekrar deneyin", 409)


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
