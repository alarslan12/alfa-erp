"""Read-only Firebase checkout -> order diagnostics for ALFA ERP.
Print counts and validation categories, never customer names, address, tokens, or codes.
Run only in a trusted Google Cloud Shell with ADC and repo venv.
"""
import uuid
from collections import Counter
from rtdb_migrate import request, session

WSID = "e2fc57b1-ef52-47b2-a6c9-ecd2e3832756"
ROOT = "alfa/" + WSID


def read(client, node):
    value, _, _ = request(client, "GET", ROOT + "/" + node)
    return value or {}


def rows(obj):
    if isinstance(obj, dict):
        return list(obj.values())
    if isinstance(obj, list):
        return [v for v in obj if v is not None]
    return []


def diagnose():
    client = session()
    print("ALFA ERP Firebase RTDB — salt okunur kontrol")
    meta = read(client, "meta")
    orders = read(client, "orders")
    public = read(client, "public_catalog")
    inbox = read(client, "checkout")
    if not isinstance(orders, dict) or not isinstance(inbox, dict):
        raise RuntimeError("Beklenmeyen orders/checkout veri biçimi")
    active_orders = sum(1 for x in orders.values() if isinstance(x, dict) and not x.get("deleted_at"))
    print("Şema:", meta.get("schema", "YOK"))
    print("Mevcut siparişler:", len(orders), "| silinmemiş:", active_orders)
    print("Katalog kitapları:", len(public))
    print("Sipariş sıra sayacı:", meta.get("order_counter", "YOK"))
    request_counts = Counter()
    issues = Counter()
    for uid, values in inbox.items():
        if not isinstance(values, dict):
            issues["İstek sahibi altında beklenmeyen yapı"] += 1
            continue
        for request_id, entry in values.items():
            request_counts["gelen"] += 1
            if not isinstance(entry, dict):
                issues["İstek yapısı hatalı"] += 1
                continue
            expected_id = str(uuid.uuid5(uuid.UUID(WSID), "checkout:" + uid + ":" + request_id))
            if expected_id in orders:
                request_counts["havuza_aktarılmış"] += 1
                continue
            request_counts["aktarılmamış"] += 1
            lines = rows(entry.get("items"))
            if not 1 <= len(lines) <= 300:
                issues["Sipariş kalemi sayısı hatalı"] += 1
            for line in lines:
                if not isinstance(line, dict):
                    issues["Kalem yapısı hatalı"] += 1
                    continue
                book = public.get(str(line.get("code") or "")) if isinstance(public, dict) else None
                if not isinstance(book, dict):
                    issues["Katalogda bulunmayan kitap"] += 1
                if line.get("print_type") not in ("SB", "RNK"):
                    issues["Baskı türü geçersiz"] += 1
                if isinstance(book, dict) and line.get("print_type") == "RNK" and not book.get("supports_color"):
                    issues["Renkli seçeneği kapalı kitap"] += 1
                try:
                    quantity = int(line.get("quantity"))
                    if not 1 <= quantity <= 100000:
                        issues["Adet sınırı aşıldı"] += 1
                except (ValueError, TypeError):
                    issues["Adet geçersiz"] += 1
            if not entry.get("shipping_reference"):
                issues["Kargo/adres alanı boş"] += 1
    print("Mobil gönderimler:", request_counts["gelen"])
    print("Havuza aktarılmış:", request_counts["havuza_aktarılmış"])
    print("Havuzda bulunmayan mobil istek:", request_counts["aktarılmamış"])
    if issues:
        print("Tespit edilen veri doğrulama sorunları:")
        for key in sorted(issues):
            print(" -", key + ":", issues[key])
    elif request_counts["aktarılmamış"]:
        print("İstek verileri yapısal olarak geçerli görünüyor; aktarma yazması/izinleri incelenmeli.")
    else:
        print("Bekleyen mobil istek yok.")
    print("Bu komut Firebase'e hiçbir şey YAZMADI.")


if __name__ == "__main__":
    diagnose()
