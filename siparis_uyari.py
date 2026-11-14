"""Order notes and revision-scoped operational notices; no network or Qt."""
import copy
import uuid
from datetime import datetime, timezone

MAX_NOTE = 2000
FIELDS = (
    ("kod", "shipping_reference", "Kargo kodu / adres"),
    ("platform", "platform", "Platform"),
    ("siparis_turu", "order_type", "Sipariş türü"),
    ("ciro", "gross_amount", "Ciro"),
    ("order_note", "order_note", "Sipariş notu"),
)

def clean_note(value):
    note = str(value or "").strip()
    if len(note) > MAX_NOTE:
        raise ValueError("Sipariş notu en fazla 2000 karakter olabilir.")
    return note

def revision(order):
    data = order.get("order_notice") or {}
    return str(data.get("revision") or "") if isinstance(data, dict) else ""

def pending_notice(order):
    data = order.get("order_notice") or {}
    return bool(revision(order) and data.get("ack_revision") != revision(order))

def initial_note_notice(order):
    """Recognize old v31/32 initial-note records without rewriting cloud data."""
    notice = order.get("order_notice") or {}
    if not isinstance(notice,dict):return False
    if notice.get("kind") == "initial_note":
        return True
    changes = notice.get("changes") or {}
    if notice.get("kind") or not isinstance(changes,dict) or len(changes)!=1:return False
    first=next(iter(changes.values()))
    return isinstance(first,dict) and first.get("label")=="Yeni sipariş notu"


def _val(row, local, remote):
    result = row.get(local, row.get(remote))
    if local == "ciro":
        return round(float(result or 0), 2)
    return str(result or "").strip()

def _books(row):
    raw = row.get("kitaplar", row.get("items")) or []
    if isinstance(raw, dict):
        raw = raw.values()
    result = {}
    for entry in raw:
        code = str(entry.get("kod", entry.get("book_code")) or "")
        kind = str(entry.get("tur", entry.get("print_type")) or "SB").upper()
        qty = int(entry.get("adet", entry.get("quantity")) or 0)
        if code and qty:
            key = (code, kind)
            prior = result.get(key, {})
            result[key] = {"qty": int(prior.get("qty", 0)) + qty,
                           "name": str(entry.get("isim") or entry.get("book_name_snapshot") or prior.get("name") or code)}
    return result

def make_notice(before, after, requested_revision=None):
    """Only semantic business edits trigger warnings, never status/count clicks.
    Preserve all unread changes across consecutive edits; each edit invalidates
    the previous acknowledgment. Initial creation warns only for a nonempty note.
    """
    changes = []
    if before is None:
        note = clean_note(after.get("order_note"))
        if not note:
            return None
        changes.append({"type":"field","label":"Yeni sipariş notu","old":"","new":note})
    else:
        for local, remote, label in FIELDS:
            a, b = _val(before, local, remote), _val(after, local, remote)
            if a != b:
                changes.append({"type":"field","label":label,"old":str(a),"new":str(b)})
        old, new = _books(before), _books(after)
        for code, kind in sorted(set(old) | set(new)):
            a, b = old.get((code,kind), {}), new.get((code,kind), {})
            aq, bq = int(a.get("qty",0)), int(b.get("qty",0))
            if aq != bq:
                changes.append({"type":"book", "code":code, "kind":kind,
                                "name":b.get("name") or a.get("name") or code,
                                "old":aq, "new":bq})
        if not changes:
            return None
        if pending_notice(before):
            previous = before["order_notice"].get("changes") or {}
            if isinstance(previous,dict):
                changes = [copy.deepcopy(previous[k]) for k in sorted(previous)] + changes
    if len(changes) > 3000:
        raise ValueError("Çok fazla okunmamış değişiklik var; önce mevcut güncellemeleri onaylayın.")
    candidate = str(requested_revision or "")
    try:
        if str(uuid.UUID(candidate)) != candidate:
            candidate = ""
    except (ValueError, TypeError, AttributeError):
        candidate = ""
    if not candidate or (before and candidate == revision(before)):
        candidate = str(uuid.uuid4())
    return {"revision":candidate, "kind":"initial_note" if before is None else "update",
            "created_at":datetime.now(timezone.utc).isoformat(),
            "changes":{f"c{i:06d}": change for i,change in enumerate(changes)}}

def acknowledge(order, expected, actor="local"):
    if not expected or revision(order) != expected:
        raise ValueError("Sipariş yeniden değişti; güncel uyarıyı açın.")
    notice = copy.deepcopy(order["order_notice"])
    if pending_notice(order):
        notice.update(ack_revision=expected, ack_by=str(actor),
                      ack_at=datetime.now(timezone.utc).isoformat())
    return notice
