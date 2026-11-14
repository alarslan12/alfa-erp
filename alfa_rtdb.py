"""ALFA ERP Firebase Realtime Database transport (Spark-capable).

No Firebase Admin SDK and no secret key in the Windows EXE.
Staff/owner get anonymous Firebase Auth identity once; the project owner
must grant that UID a role in RTDB before business access is possible.
"""
from __future__ import annotations
import copy
import json
import os
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from siparis_uyari import clean_note, pending_notice, make_notice, revision, acknowledge

API_KEY = "AIzaSyAnp5yiDLGE6nCb-Lrl8DeZx5dDaYuopCM"
DB_URL = "https://alfa-erp-8700c-default-rtdb.europe-west1.firebasedatabase.app"
WORKSPACE_ID = "e2fc57b1-ef52-47b2-a6c9-ecd2e3832756"
ROOT = "alfa/" + WORKSPACE_ID


class DeviceError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status
    @property
    def permanent(self):
        return self.status in (400, 409, 412, 422)


def _http_json(url, method="GET", body=None, headers=None, timeout=20):
    data = None if body is None else json.dumps(
        body, ensure_ascii=False, allow_nan=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method,
                                      headers={"Accept": "application/json",
                                               **({"Content-Type": "application/json"} if data is not None else {}),
                                               **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            return (json.loads(payload) if payload.strip() else None,
                    response.headers.get("ETag"), response.status)
    except urllib.error.HTTPError as error:
        # Avoid printing response bodies which might contain sensitive records.
        if error.code == 401:
            # RTDB also returns 401 for Security Rules "Permission denied".
            # An inaccessible legacy path is not proof of an expired login.
            try:
                message = json.loads(error.read(1024)).get("error", "")
            except (ValueError, OSError, TypeError, AttributeError):
                message = ""
            if "permission denied" in str(message).lower():
                raise DeviceError(
                    "Firebase erişim izni reddedildi; veritabanı kuralları veya cihaz rolünü kontrol et.",
                    403) from None
            raise DeviceError("Firebase oturumu geçersiz; cihaz bağlantısını kontrol et.", 401) from None
        if error.code == 403:
            raise DeviceError("Bu cihaz henüz yönetici tarafından yetkilendirilmedi.", 403) from None
        if error.code == 412:
            raise DeviceError("Başka bilgisayarda işlem yapıldı; yeniden eşitleniyor.", 409) from None
        raise DeviceError("Firebase HTTP " + str(error.code), error.code) from None
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        raise DeviceError("Firebase bağlantısı kurulamadı (" +
                          type(getattr(error, "reason", error)).__name__ + ").") from None


def _session_path():
    from cihaz_sifreleme import DATA, OWNER_APP
    return Path(DATA) / ("firebase_owner_session.bin" if OWNER_APP
                         else "firebase_staff_session.bin")


def load_identity():
    from cihaz_sifreleme import crypt
    try:
        state = json.loads(crypt(_session_path().read_bytes(), True))
        if not all(state.get(k) for k in ("refresh_token", "uid")):
            return None
        return state
    except (OSError, ValueError, RuntimeError, TypeError):
        return None


def save_identity(identity):
    from cihaz_sifreleme import crypt
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_bytes(crypt(json.dumps(identity).encode("utf-8")))
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


class Workstation:
    """Drop-in cloud contract for bulut_canli.Sync and bildirim_servisi.Reader."""

    def __init__(self):
        self._lock = threading.RLock()
        self._identity = load_identity()
        self._id_token = None
        self._token_expires = 0.0
        self._checkout_dirty = True
        self._checkout_last_checked = 0.0
        self._catalog_cache = None
        self._last_catalog_revision = None
        self.token = self._identity.get("refresh_token") if self._identity else None

    @property
    def paired(self):
        return bool(self._identity and self._identity.get("refresh_token"))

    @property
    def uid(self):
        return self._identity.get("uid") if self._identity else None

    def reload(self):
        with self._lock:
            self._identity = load_identity()
            self._id_token = None
            self._token_expires = 0.0
            self.token = self._identity.get("refresh_token") if self._identity else None

    def enroll_anonymous(self, name=None):
        """One-time device identity; never grants staff or owner role."""
        if self.paired:
            return self.uid
        url = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + API_KEY
        answer, _, _ = _http_json(url, "POST", {"returnSecureToken": True})
        identity = {"uid": str(answer["localId"]),
                    "refresh_token": str(answer["refreshToken"])}
        with self._lock:
            save_identity(identity)
            self._identity = identity
            self._id_token = answer["idToken"]
            self._token_expires = time.monotonic() + int(answer.get("expiresIn", 3600))
            self.token = identity["refresh_token"]
        payload = {"name": str(name or socket.gethostname())[:120],
                   "created_at": datetime.now(timezone.utc).isoformat()}
        try:
            self._request("PUT", "device_requests/" + self.uid, payload)
        except DeviceError:
            # Identity is already securely persisted; user can retry request.
            pass
        return self.uid

    def _get_id_token(self):
        with self._lock:
            if not self.paired:
                raise DeviceError("Cihaz etkinleştirilmedi.")
            if self._id_token and time.monotonic() < self._token_expires - 90:
                return self._id_token
            url = "https://securetoken.googleapis.com/v1/token?key=" + API_KEY
            body = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": self._identity["refresh_token"],
            }).encode("ascii")
            request = urllib.request.Request(url, body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST")
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    fresh = json.loads(response.read())
            except urllib.error.HTTPError:
                raise DeviceError("Firebase cihaz oturumu iptal edildi; yeniden kaydet.", 401) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                raise DeviceError("Firebase kimlik sunucusuna erişilemiyor.") from None
            identity = {"uid": str(fresh["user_id"]),
                        "refresh_token": str(fresh["refresh_token"])}
            if identity["uid"] != self._identity["uid"]:
                raise DeviceError("Cihaz kimliği değişti; işlem durduruldu.", 403)
            save_identity(identity)
            self._identity = identity
            self.token = identity["refresh_token"]
            self._id_token = fresh["id_token"]
            self._token_expires = time.monotonic() + int(fresh.get("expires_in", 3600))
            return self._id_token

    def _request(self, method, path, body=None, *, etag=False, match=None, timeout=20, query=None):
        safe_path = "/".join(urllib.parse.quote(p, safe="") for p in
                             (ROOT + "/" + path.strip("/")).split("/"))
        token = urllib.parse.quote(self._get_id_token(), safe="")
        url = DB_URL + "/" + safe_path + ".json?auth=" + token
        if query:
            url += "&" + urllib.parse.urlencode(query)
        headers = {}
        if etag:
            headers["X-Firebase-ETag"] = "true"
        if match is not None:
            headers["if-match"] = match
        return _http_json(url, method, body, headers, timeout)

    def _get(self, path):
        return self._request("GET", path)[0]

    def send_error_report(self,report,timeout=15):
        """One sanitized exception event; Firebase Rules reject impostor UIDs."""
        if not isinstance(report,dict):
            raise DeviceError("Hata kaydı geçersiz",422)
        key=str(report.get("id") or "")
        if not key or any(c in key for c in ".#$[]/") or len(key)>80:
            raise DeviceError("Hata kaydı kimliği geçersiz",422)
        if str(report.get("device_id"))!=str(self.uid):
            raise DeviceError("Hata raporu cihaz kimliği uyuşmuyor",403)
        if len(json.dumps(report,ensure_ascii=False))>7500:
            raise DeviceError("Hata raporu çok büyük",422)
        self._request("PUT","error_reports/"+key,report,timeout=timeout)
        return key

    def read_error_reports(self,limit=70):
        """Owner-only, bounded reads; no full history download."""
        maximum=max(1,min(100,int(limit)))
        payload=self._request("GET","error_reports",
              query={"orderBy":'"$key"',"limitToLast":maximum})[0]
        return payload if isinstance(payload,dict) else {}

    def review_error_report(self,report_id):
        """Owner-only acknowledgement stored separately from immutable event."""
        report_id=str(report_id)
        if not report_id or any(c in report_id for c in ".#$[]/"):
            raise DeviceError("Hata kaydı kimliği geçersiz",422)
        payload={"reviewed_by":str(self.uid),
                 "reviewed_at":datetime.now(timezone.utc).isoformat(timespec="seconds")}
        self._request("PUT","error_acks/"+report_id,payload)
        return payload

    def read_error_acks(self):
        """Bound acknowledgement downloads; never read the entire history."""
        records=self._request("GET","error_acks",
            query={"orderBy":'"$key"',"limitToLast":150})[0]
        return records if isinstance(records,dict) else {}


    def _bump(self, kind):
        if kind not in ("orders", "catalog", "inventory"):
            raise ValueError("Unknown revision")
        for _ in range(8):
            current, etag, _ = self._request("GET", "meta/revisions/" + kind, etag=True)
            try:
                self._request("PUT", "meta/revisions/" + kind,
                              max(0, int(current or 0)) + 1, match=etag)
                return
            except DeviceError as error:
                if error.status != 409:
                    raise
        raise DeviceError("Eşitleme revision çakışması", 409)

    def sync(self, known=None, notification=False, last_order_number=0):
        meta = self._get("meta")
        if not isinstance(meta, dict) or not meta.get("epoch"):
            raise DeviceError("Firebase'de doğrulanmış ALFA ERP verisi bulunamadı.", 403)
        rev = meta.get("revisions") or {}
        pulse = {
            "epoch": str(meta["epoch"]),
            "orders_revision": int(rev.get("orders") or 1),
            "catalog_revision": int(rev.get("catalog") or 1),
            "inventory_revision": int(rev.get("inventory") or 1),
        }
        known = known or {}
        # The checkout worker may otherwise hold old numeric-code titles
        # indefinitely even after an Excel replacement. Refresh from the
        # public catalog before adopting any pending mobile checkout.
        if self._last_catalog_revision != pulse["catalog_revision"]:
            self._catalog_cache = None
            self._checkout_dirty = True
            self._last_catalog_revision = pulse["catalog_revision"]
        # Mobile requests are promoted to the SAME orders pool, even when
        # different workstations detect them concurrently. Order IDs and
        # conditional writes prevent duplicate order creation.
        self._adopt_checkout()
        refreshed = self._get("meta/revisions/orders")
        if refreshed:
            pulse["orders_revision"] = int(refreshed)
        if notification:
            if not known or pulse["orders_revision"] != known.get("orders_revision"):
                rows = self._get("orders") or {}
                pulse["orders_brief"] = [
                    {"id": key, "order_number": value.get("order_number", 0)}
                    for key, value in rows.items()
                    if isinstance(value, dict) and not value.get("deleted_at")]
            return pulse
        if (not known or known.get("orders_revision") != pulse["orders_revision"] or
                known.get("epoch") != pulse["epoch"]):
            source = self._get("orders") or {}
            order_rows = []
            lines = []
            for order_id, row in source.items():
                if not isinstance(row, dict):
                    continue
                fresh = dict(row)
                nested = fresh.pop("items", {})
                fresh.pop("ops", None)
                fresh["id"] = order_id
                order_rows.append(fresh)
                if isinstance(nested, dict):
                    for item_id, item in nested.items():
                        if isinstance(item, dict):
                            lines.append({**item, "id": item_id, "order_id": order_id})
            pulse["orders"] = order_rows
            pulse["items"] = lines
            pulse["accounting_days"] = list((self._get("accounting") or {}).values())
        if (not known or known.get("catalog_revision") != pulse["catalog_revision"] or
                known.get("epoch") != pulse["epoch"]):
            pulse["books"] = list((self._get("books") or {}).values())
        if (not known or known.get("inventory_revision") != pulse["inventory_revision"] or
                known.get("epoch") != pulse["epoch"]):
            inventory = self._get("inventory") or {}
            products = list((inventory.get("products") or {}).values())
            sales = list((inventory.get("sales") or {}).values())
            for product in products:
                if isinstance(product,dict):
                    sales.extend((product.get("sales_history") or {}).values())
            pulse["inventory_products"] = products
            pulse["inventory_sales"] = sales
        return pulse

    def snapshot(self):
        return self.sync()

    def pulse(self):
        meta = self._get("meta")
        rev = meta.get("revisions") or {}
        return {"epoch": meta["epoch"],
                "orders_revision": int(rev.get("orders") or 1),
                "catalog_revision": int(rev.get("catalog") or 1),
                "inventory_revision": int(rev.get("inventory") or 1)}

    def _reserve_order_number(self):
        for _ in range(20):
            old, etag, _ = self._request("GET", "meta/order_counter", etag=True)
            proposed = int(old or 0) + 1
            try:
                self._request("PUT", "meta/order_counter", proposed, match=etag)
                return proposed
            except DeviceError as exc:
                if exc.status != 409:
                    raise
        raise DeviceError("Sipariş sıra numarası çakışması", 409)

    def _atomic_order(self, order_id, mutate, allow_create=False):
        for _ in range(8):
            row, etag, _ = self._request("GET", "orders/" + order_id, etag=True)
            if row is None and not allow_create:
                raise DeviceError("Bulut siparişi bulunamadı", 409)
            updated, result = mutate(copy.deepcopy(row))
            if updated is None:
                return result
            try:
                self._request("PUT", "orders/" + order_id, updated,
                              match="null_etag" if row is None else etag)
                try:
                    self._bump("orders")
                except DeviceError:
                    # The row is committed. SSE on /orders still broadcasts;
                    # the periodic reconciliation repairs missed revisions.
                    pass
                return result
            except DeviceError as error:
                if error.status != 409:
                    raise
        # Exhausted conditional ETag retries are transient contention, not
        # a permanently invalid business operation. Keep the durable outbox
        # and retry instead of quarantining an otherwise valid user action.
        raise DeviceError("Sipariş yoğun biçimde değişiyor; işlem güvenle sırada tutuldu", 503)

    @staticmethod
    def _make_items(order_id, local_rows, existing=None):
        rows = {}
        old_by_key = {}
        for value in (existing or {}).values():
            old_by_key[(str(value.get("book_code")), str(value.get("print_type")))] = value
        for entry in local_rows:
            code = str(entry.get("kod") or "").strip()
            kind = str(entry.get("tur") or "SB").upper()
            qty = int(entry.get("adet") or 0)
            if not code or kind not in ("SB", "RNK") or qty < 1 or qty > 100000:
                raise DeviceError("Sipariş kitap satırı geçersiz", 422)
            key = (code, kind)
            if key in rows:
                raise DeviceError("Tekrarlanan kitap satırı", 422)
            prior = old_by_key.get(key, {})
            item_id = str(uuid.uuid5(uuid.UUID(order_id), code + "|" + kind))
            rows[key] = {**prior,
                "id": item_id, "order_id": order_id, "workspace_id": WORKSPACE_ID,
                "book_code": code,
                "book_name_snapshot": str(entry.get("isim") or
                    prior.get("book_name_snapshot") or code),
                "page_count_snapshot": max(0,int(
                    entry.get("sayfa_birim") or entry.get("sayfa") or
                    prior.get("page_count_snapshot") or 0)),
                "print_type": kind, "quantity": qty,
                "prepared_count": min(qty, int(prior.get("prepared_count") or 0)),
                "boxed_count": min(qty, int(prior.get("boxed_count") or 0)),
                "version": int(prior.get("version") or 1)}
        return {v["id"]: v for v in rows.values()}

    def commit(self, edits):
        results = []
        for edit in edits:
            local_id = str(edit["local_id"])
            request_id = str(edit.get("request_id") or "")
            if edit.get("uuid"):
                order_id = str(edit["uuid"])
                expected = int(edit.get("version") or 0)
                if edit.get("delete"):
                    def delete(previous):
                        if int(previous.get("version") or 0) != expected:
                            raise DeviceError("Sipariş başka cihazda değişti", 409)
                        previous["deleted_at"] = datetime.now(timezone.utc).isoformat()
                        previous["version"] = expected + 1
                        return previous, {"local_id":local_id, "uuid":order_id,
                                          "version":previous["version"],
                                          "order_number":previous["order_number"]}
                    results.append(self._atomic_order(order_id, delete))
                    continue
                local = edit["order"]
                def edit_existing(previous):
                    if int(previous.get("version") or 0) != expected:
                        raise DeviceError("Sipariş başka cihazda değişti", 409)
                    before = copy.deepcopy(previous)
                    note = clean_note(local.get("order_note", previous.get("order_note")))
                    if note != clean_note(previous.get("order_note")):
                        member = self._get("members/" + self.uid) or {}
                        if member.get("role") != "owner" or member.get("active") is not True:
                            raise DeviceError("Sipariş notunu yalnızca Yönetici düzenleyebilir", 403)
                    if note or "order_note" in previous:
                        previous["order_note"] = note
                    previous["platform"] = str(local.get("platform") or "")
                    previous["shipping_reference"] = str(local.get("kod") or "")
                    previous["order_type"] = str(local.get("siparis_turu") or "")
                    previous["gross_amount"] = float(local.get("ciro") or 0)
                    previous["items"] = self._make_items(
                        order_id, local.get("kitaplar") or [], previous.get("items") or {})
                    notice = make_notice(before, previous, revision(local))
                    if notice:
                        previous["order_notice"] = notice
                    previous["version"] = expected + 1
                    result = {"local_id":local_id,"uuid":order_id,
                              "version":previous["version"],
                              "order_number":previous["order_number"]}
                    if "order_notice" in previous or "order_notice" in local:
                        result["notice_state"] = {"order_notice":previous.get("order_notice"),
                                                  "order_note":previous.get("order_note","")}
                    return previous, result
                results.append(self._atomic_order(order_id, edit_existing))
                continue
            if not request_id:
                raise DeviceError("Tekrarlanabilir sipariş isteği kimliği yok", 422)
            try:
                uuid.UUID(request_id)
            except ValueError:
                raise DeviceError("Geçersiz istek kimliği", 422) from None
            order_id = str(uuid.uuid5(uuid.UUID(WORKSPACE_ID), "manual:" + request_id))
            local = edit["order"]
            def create(previous):
                if previous is not None:
                    if previous.get("client_request_id") != request_id:
                        raise DeviceError("Sipariş kimliği çakıştı", 409)
                    result = {"local_id":local_id, "uuid":order_id,
                              "version":int(previous["version"]),
                              "order_number":int(previous["order_number"])}
                    if "order_notice" in previous or "order_notice" in local:
                        result["notice_state"] = {"order_notice":previous.get("order_notice"),
                                                  "order_note":previous.get("order_note","")}
                    return None, result
                number = self._reserve_order_number()
                now = datetime.now(timezone.utc).isoformat()
                entry = {"id":order_id,"workspace_id":WORKSPACE_ID,
                         "order_number":number,
                         "client_request_id":request_id,
                         "legacy_local_id":int(local_id) if local_id.isdigit() else None,
                         "status":str(local.get("durum") or "havuz"),
                         "platform":str(local.get("platform") or "Manuel"),
                         "shipping_reference":str(local.get("kod") or ""),
                         "order_type":str(local.get("siparis_turu") or ""),
                         "gross_amount":float(local.get("ciro") or 0),
                         "shipping_fee":local.get("kargo_ucreti"),
                         "placed_at":str(local.get("tarih") or now),
                         "created_at":now,"updated_at":now,
                         "version":1,
                         "event_log":{request_id:{
                            "id":request_id,"action":"commit","device_id":self.uid,
                            "device_name":socket.gethostname()[:120],"order_ids":[order_id],
                            "created_at":now,"details":{}}},
                         "items":self._make_items(order_id,local.get("kitaplar") or [])}
                note = clean_note(local.get("order_note"))
                result = {"local_id":local_id, "uuid":order_id,
                          "version":1, "order_number":number}
                if note:
                    entry["order_note"] = note
                    entry["order_notice"] = make_notice(None, entry, revision(local))
                    result["notice_state"] = {"order_note":note, "order_notice":entry["order_notice"]}
                elif local.get("order_notice"):
                    result["notice_state"] = {"order_note":"","order_notice":None}
                return entry, result
            results.append(self._atomic_order(order_id, create, allow_create=True))
        return results

    def acknowledge_order_notice(self, order_id, expected):
        """Atomic exact-revision acknowledgment; never clear a newer notice."""
        def mutate(row):
            if row.get("deleted_at"):
                raise DeviceError("Sipariş artık mevcut değil",409)
            try:
                notice = acknowledge(row, expected, self.uid)
            except ValueError as exc:
                raise DeviceError(str(exc),409) from None
            base_version = int(row.get("version") or 1)
            if not pending_notice(row):
                return None, {"notice":notice,"base_version":base_version,"version":base_version}
            row["order_notice"] = notice
            row["version"] = base_version + 1
            row["updated_at"] = datetime.now(timezone.utc).isoformat()
            event_id = str(uuid.uuid4())
            row.setdefault("event_log",{})[event_id] = {
                "id":event_id, "action":"order_notice_acknowledged",
                "device_id":self.uid, "device_name":socket.gethostname()[:120],
                "order_ids":[order_id], "created_at":row["updated_at"],
                "details":{"revision":expected}}
            return row, {"notice":notice,"base_version":base_version,"version":row["version"]}
        return self._atomic_order(order_id, mutate)

    def acknowledge_notices(self, events):
        results=[]
        for event in events:
            order_id=str(event.get("order_id") or "")
            if not order_id:
                raise DeviceError("Sipariş bulut kimliği bulunamadı",409)
            receipt=self.acknowledge_order_notice(order_id,str(event["notice_revision"]))
            results.append({**receipt,"op_id":event["op_id"],"order_id":order_id,
                            "local_id":event["local_id"]})
        return results

    def _apply_progress_events(self, events):
        """Commit every consecutive progress change for ONE order in ONE CAS.

        A bulk 'Hepsini seç' action records one local batch of per-book
        deltas. Previously each event performed an independent Firebase PUT;
        remote workstations saw dozens of intermediate order snapshots.
        Keep op_id history so a network retry or partial previous delivery
        never applies a delta twice.
        """
        results=[]
        groups=[]
        for event in events:
            order_id=str(event.get("order_id") or "")
            if not order_id:raise DeviceError("Sipariş bulut kimliği bulunamadı",409)
            if not groups or groups[-1][0]!=order_id:
                groups.append((order_id,[]))
            groups[-1][1].append(event)

        for order_id, group in groups:
            def mutate(row):
                processed=row.setdefault("ops",{})
                # An already-acknowledged replay stays valid even if another
                # device has since completed or moved this order.
                if all(str(event["op_id"]) in processed for event in group):
                    return None,[{"op_id":str(event["op_id"]),
                                  "order_id":order_id,
                                  "version":int(processed[str(event["op_id"])])}
                                 for event in group]
                if pending_notice(row):
                    raise DeviceError("Sipariş güncellemesi okunup onaylanmalı",422)
                if row.get("status")!="aktif":
                    raise DeviceError("İşlem için sipariş aktif olmalı",409)
                items=row.get("items") or {}
                if not isinstance(items,dict):
                    raise DeviceError("Sipariş kitap satırları geçersiz",422)
                by_key={(str(item.get("book_code")),str(item.get("print_type"))):item
                        for item in items.values() if isinstance(item,dict)}
                changed=[]
                for event in group:
                    op_id=str(event["op_id"])
                    if op_id in processed:
                        continue
                    if str(event.get("notice_revision") or "") != revision(row):
                        raise DeviceError("Sipariş içeriği değişti; ilerlemeyi yeniden kontrol edin",409)
                    key=(str(event.get("book_code")),str(event.get("print_type")))
                    match=by_key.get(key)
                    if match is None:
                        raise DeviceError("Sipariş kitap satırı bulunamadı",422)
                    qty=int(match.get("quantity") or 0)
                    ready=int(match.get("prepared_count") or 0)+int(event.get("delta_ready") or 0)
                    boxed=int(match.get("boxed_count") or 0)+int(event.get("delta_boxed") or 0)
                    if not 0<=boxed<=ready<=qty:
                        raise DeviceError("Hazırlanan/kolilenen adet sınır dışında",422)
                    match["prepared_count"]=ready
                    match["boxed_count"]=boxed
                    match["version"]=int(match.get("version") or 1)+1
                    changed.append(event)
                if not changed:
                    return None,[{"op_id":str(event["op_id"]),
                                  "order_id":order_id,
                                  "version":int(processed[str(event["op_id"])])}
                                 for event in group]
                now=datetime.now(timezone.utc).isoformat()
                row["version"]=int(row.get("version") or 1)+1
                row["updated_at"]=now
                version=row["version"]
                history=row.setdefault("event_log",{})
                for event in changed:
                    processed[str(event["op_id"])]=version
                # Store ONE audit entry for the whole user action, not one
                # duplicate event_log object per selected book. The op_id map
                # still provides exact per-book idempotency on network retries.
                batch_id=str(changed[0]["op_id"])
                history[batch_id]={
                    "id":batch_id,"action":"progress_bulk",
                    "device_id":self.uid,
                    "device_name":socket.gethostname()[:120],
                    "order_ids":[order_id],"created_at":now,
                    "details":{"events":[{
                        "book_code":str(event.get("book_code") or ""),
                        "print_type":str(event.get("print_type") or ""),
                        "delta_ready":int(event.get("delta_ready") or 0),
                        "delta_boxed":int(event.get("delta_boxed") or 0),
                    } for event in changed]}}
                return row,[{"op_id":str(event["op_id"]),
                             "order_id":order_id,
                             "version":int(processed[str(event["op_id"])])}
                            for event in group]
            # One conditional Firebase PUT for all selected books in this
            # order; a concurrent change retries the whole group with ETag.
            results.extend(self._atomic_order(order_id,mutate))
        return results

    def _apply_events(self, events, kind):
        if kind=="progress":
            return self._apply_progress_events(events)
        results=[]
        for event in events:
            order_id=str(event.get("order_id") or "")
            if not order_id:raise DeviceError("Sipariş bulut kimliği bulunamadı",409)
            op_id=str(event["op_id"])
            def mutate(row):
                processed = row.setdefault("ops", {})
                if op_id in processed:
                    return None, {"op_id":op_id,"order_id":order_id,
                                  "version":int(processed[op_id])}
                if kind=="status":
                    src = str(event["from_status"])
                    dst = str(event["to_status"])
                    if (src,dst) not in (
                        ("havuz","aktif"),("aktif","havuz"),("aktif","tamamlandi"),("tamamlandi","aktif")
                    ):
                        raise DeviceError("Geçersiz sipariş durumu geçişi",422)
                    if str(row.get("status"))==dst:
                        # Another fast action/device already reached our intended
                        # status. Acknowledge without overwriting the latest row.
                        return None,{"op_id":op_id,"order_id":order_id,
                                     "version":int(row.get("version") or 0)}
                    if str(row.get("status")) != src:
                        raise DeviceError("Sipariş durumu başka cihazda değişti; yenile",409)
                    if dst in ("aktif","tamamlandi"):
                        if pending_notice(row):
                            raise DeviceError("Sipariş güncellemesi okunup onaylanmalı",422)
                        if str(event.get("notice_revision") or "") != revision(row):
                            raise DeviceError("Sipariş içeriği değişti; güncel siparişi tekrar kontrol edin",409)
                    if dst=="tamamlandi":
                        items=(row.get("items") or {}).values()
                        if not all(int(x.get("boxed_count") or 0)>=int(x.get("quantity") or 0)
                                   for x in items):
                            raise DeviceError("Siparişin tüm kitapları kolilenmedi", 422)
                        row["completed_at"]=datetime.now(timezone.utc).isoformat()
                        row["shipping_fee"]=event.get("shipping_fee")
                    if dst=="aktif":
                        row["started_at"]=datetime.now(timezone.utc).isoformat()
                        row["completed_at"]=None
                    row["status"]=dst
                else:
                    if row.get("status") != "aktif":
                        raise DeviceError("İşlem için sipariş aktif olmalı", 409)
                    match = next((x for x in (row.get("items") or {}).values()
                        if x.get("book_code")==event.get("book_code") and
                           x.get("print_type")==event.get("print_type")),None)
                    if not match:
                        raise DeviceError("Sipariş kitap satırı bulunamadı", 422)
                    qty=int(match.get("quantity") or 0)
                    next_ready=int(match.get("prepared_count") or 0)+int(event.get("delta_ready") or 0)
                    next_boxed=int(match.get("boxed_count") or 0)+int(event.get("delta_boxed") or 0)
                    if not (0 <= next_ready <= qty and 0 <= next_boxed <= qty):
                        raise DeviceError("Hazırlanan/kolilenen adet sınır dışında", 422)
                    match["prepared_count"]=next_ready
                    match["boxed_count"]=next_boxed
                    match["version"]=int(match.get("version") or 1)+1
                row["version"]=int(row.get("version") or 1)+1
                row["updated_at"]=datetime.now(timezone.utc).isoformat()
                processed[op_id]=row["version"]
                history=row.setdefault("event_log",{})
                history[op_id]={"id":op_id,"action":"transition" if kind=="status" else "progress",
                    "device_id":self.uid,"device_name":socket.gethostname()[:120],
                    "order_ids":[order_id],"created_at":row["updated_at"],
                    "details":{"events":[copy.deepcopy(event)]}}
                return row, {"op_id":op_id,"order_id":order_id,"version":row["version"]}
            results.append(self._atomic_order(order_id, mutate))
        return results

    def transition(self, events):
        return self._apply_events(events, "status")

    def progress(self, events):
        return self._apply_events(events, "progress")

    def inventory_sale(self,product_id,quantity,sale_price,batch_id=None):
        """Atomic sale from ONE purchase lot with its historical unit cost.

        ETag conflicts re-fetch available quantity; sale history is committed
        with the product's batch decrement in a single Firebase PUT.
        """
        from inventory_batches import stock_batches,batch_stock_quantity
        pid=str(product_id)
        try:
            qty=int(quantity)
            price=round(float(sale_price),2)
        except (TypeError,ValueError,OverflowError):
            raise DeviceError("Satış adedi veya fiyatı geçersiz",422) from None
        if qty<1 or qty>100000 or not 0<=price<=999999999:
            raise DeviceError("Satış adedi veya fiyatı geçersiz",422)
        sale_id=str(uuid.uuid4())
        for _ in range(8):
            current,etag,_=self._request("GET","inventory/products/"+pid,etag=True)
            if not isinstance(current,dict):
                raise DeviceError("Envanter ürünü bulunamadı",404)
            before=int(current.get("quantity") or 0)
            if before<qty:
                raise DeviceError("Stok adedi yeterli değil",422)
            if batch_stock_quantity(current)!=before:
                raise DeviceError("Stok partileri ile mevcut adet uyuşmuyor",409)
            batches=stock_batches(current)
            if batch_id is None:
                compatible=sorted((x for x in batches.values()
                    if int(x.get("remaining") or 0)>=qty),
                    key=lambda x:(str(x.get("received_at") or ""),str(x.get("id") or "")))
                selected=str(compatible[0]["id"]) if compatible else ""
            else:
                selected=str(batch_id)
            chosen=batches.get(selected)
            if not chosen or int(chosen.get("remaining") or 0)<qty:
                raise DeviceError("Seçilen alım partisinde yeterli stok yok; yenile",409)
            updated=copy.deepcopy(current)
            chosen["remaining"]=int(chosen["remaining"])-qty
            batches[selected]=chosen
            now=datetime.now(timezone.utc).isoformat()
            updated.update(stock_batches=batches,quantity=before-qty,
                           sale_price=price,updated_at=now,
                           version=int(updated.get("version") or 0)+1)
            sale={"id":sale_id,"workspace_id":WORKSPACE_ID,
                  "product_id":pid,"batch_id":selected,
                  "purchase_at":str(chosen.get("received_at") or ""),
                  "quantity":qty,"sale_price":price,
                  "cost_price":float(chosen.get("unit_cost") or 0),
                  "device_id":self.uid,"created_at":now}
            history=updated.setdefault("sales_history",{})
            if not isinstance(history,dict):
                raise DeviceError("Satış geçmişi geçersiz",422)
            history[sale_id]=sale
            try:
                self._request("PUT","inventory/products/"+pid,updated,match=etag)
                try:self._bump("inventory")
                except DeviceError:pass
                return {"sale":sale,"remaining":updated["quantity"]}
            except DeviceError as exc:
                if exc.status!=409:raise
        raise DeviceError("Stok eşzamanlı değişti; yeniden deneyin",409)


    def _adopt_checkout(self):
        """Promote public inbox to the existing orders pool.

        Never trusts customer-supplied order status, order number or page count.
        Duplicate adoption across workstations is prevented with an ETag.
        """
        # SSE is best-effort. Periodically re-check pending anonymous checkout
        # requests, even if a Windows firewall interrupted the Firebase stream.
        now = time.monotonic()
        if not self._checkout_dirty and now - self._checkout_last_checked < 45:
            return
        inbox = self._get("checkout") or {}
        if not isinstance(inbox, dict):
            raise DeviceError("Firebase mobil sipariş isteklerinin veri biçimi beklenmiyor.")
        if self._catalog_cache is None:
            raw_catalog = self._get("public_catalog") or {}
            # Every ALFA book code is numeric (29..513). RTDB automatically
            # serializes sufficiently dense numeric-key maps as JSON arrays.
            # Mobile browsers handle Object.values(array), but the Windows
            # importer previously called .get() on the resulting Python list.
            if isinstance(raw_catalog, (dict, list)):
                values = (raw_catalog.values() if isinstance(raw_catalog, dict)
                          else raw_catalog)
                self._catalog_cache = {
                    str(book["code"]): book for book in values
                    if isinstance(book, dict) and book.get("code") is not None
                }
            else:
                raise DeviceError("Firebase mobil kitap kataloğu okunamadı.")
        books = self._catalog_cache
        self._checkout_last_checked = now
        self._checkout_dirty = False
        # Historical checkout entries may be retained for audit. Avoid one
        # extra GET per old entry: once the inbox grows, fetch order IDs only.
        inbox_count=sum(len(entries) for entries in inbox.values()
                        if isinstance(entries,dict))
        use_shallow_lookup=inbox_count>=8
        existing_order_ids=None
        for uid, requests in inbox.items():
            if not isinstance(requests, dict):
                continue
            for request_id, entry in requests.items():
                if not isinstance(entry, dict) or not isinstance(entry.get("items"), (dict, list)):
                    continue
                try:
                    order_id = str(uuid.uuid5(uuid.UUID(WORKSPACE_ID),
                                              "checkout:" + uid + ":" + request_id))
                    if use_shallow_lookup and existing_order_ids is None:
                        try:
                            keys=self._request("GET","orders",
                                query={"shallow":"true"})[0]
                            if keys is not None and not isinstance(keys,dict):
                                raise DeviceError("Sipariş anahtar listesi geçersiz")
                            existing_order_ids=set((keys or {}).keys())
                        except DeviceError:
                            # Some installations may reject shallow reads.
                            # Fall back once to the original per-order lookup.
                            use_shallow_lookup=False
                    if use_shallow_lookup:
                        if order_id in existing_order_ids:
                            continue
                    elif self._get("orders/" + order_id) is not None:
                        continue
                    raw_items = (list(entry["items"].values())
                                 if isinstance(entry["items"],dict) else entry["items"])
                    if not 1 <= len(raw_items) <= 300:
                        continue
                    items=[]
                    for item in raw_items:
                        book = books.get(str(item.get("code") or ""))
                        qty = int(item.get("quantity") or 0)
                        kind = str(item.get("print_type") or "")
                        if not book or not 1 <= qty <= 100000 or kind not in ("SB","RNK"):
                            raise ValueError("Invalid public item")
                        if kind=="RNK" and not book.get("supports_color"):
                            raise ValueError("Color not supported")
                        items.append({"kod":book["code"],"isim":book["name"],
                                      "sayfa":book["page_count"],"tur":kind,"adet":qty})
                    if sum(x["adet"] for x in items)>1000000:
                        continue
                    shipping=str(entry.get("shipping_reference") or "")[:500]
                    if not shipping:
                        continue
                    def create(current):
                        if current is not None:
                            return None, None
                        number=self._reserve_order_number()
                        now=datetime.now(timezone.utc).isoformat()
                        order={
                            "id":order_id, "workspace_id":WORKSPACE_ID,
                            "order_number":number,
                            "client_request_id":request_id,
                            "status":"havuz",
                            "platform":str(entry.get("platform") or "Mobil")[:100],
                            "shipping_reference":shipping,
                            "order_type":str(entry.get("order_type") or "")[:100],
                            "gross_amount":float(entry.get("gross_amount") or 0),
                            "placed_at":now,"created_at":now,"updated_at":now,
                            "version":1,
                            "event_log":{request_id:{
                                "id":request_id,"action":"commit","device_id":self.uid,
                                "device_name":socket.gethostname()[:120],"order_ids":[order_id],
                                "created_at":now,"details":{"source":"mobile"}}},
                            "items":self._make_items(order_id, items)}
                        return order,None
                    self._atomic_order(order_id, create, allow_create=True)
                    if existing_order_ids is not None:
                        existing_order_ids.add(order_id)
                except (DeviceError, ValueError, TypeError, OverflowError):
                    # Leave the source request intact for review/retry.
                    continue

    def watch(self, callback, stop_requested, location="meta/revisions", query=None):
        """Server-Sent Events: no repeated full REST snapshot polling."""
        pause=1
        while not stop_requested():
            try:
                path="/".join(urllib.parse.quote(p,safe="") for p in
                              (ROOT+"/"+location).split("/"))
                token=urllib.parse.quote(self._get_id_token(),safe="")
                req=urllib.request.Request(
                    DB_URL+"/"+path+".json?auth="+token+
                    ("&"+urllib.parse.urlencode(query) if query else ""),
                    headers={"Accept":"text/event-stream"})
                with urllib.request.urlopen(req,timeout=75) as stream:
                    pause=1
                    event=""
                    while not stop_requested():
                        line=stream.readline().decode("utf-8","replace").strip()
                        if not line:
                            if event in ("put","patch"):
                                if location == "checkout":
                                    self._checkout_dirty = True
                                callback()
                            if event in ("auth_revoked","cancel"):
                                break
                            event=""
                            continue
                        if line.startswith("event:"):
                            event=line[6:].strip()
            except (urllib.error.URLError,OSError,TimeoutError,DeviceError):
                pass
            if stop_requested():
                break
            time.sleep(pause)
            pause=min(60,pause*2)
