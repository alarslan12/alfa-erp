"""Tamamlanan siparişlerin son 3 gün ve istek üzerine açılan arşiv ayrımı.

Qt bağımsız tutulur. Sipariş verisi taşınmaz / silinmez; yalnızca
pencerede çizilecek siparişler ayrılır.
"""
from datetime import date, timedelta


def tamamlanma_gunu(order):
    value = str(order.get('tamamlanma_tarihi') or '')[:10]
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def ayir_tamamlananlar(orders, today=None, window_days=3):
    """[bugün-2, bugün] aralığı güncel; daha eskiler/bilinmeyenler arşivdir."""
    today = today or date.today()
    cutoff = today - timedelta(days=max(1, int(window_days)) - 1)
    recent, archive = [], []
    for order in orders:
        day = tamamlanma_gunu(order)
        if day is not None and cutoff <= day <= today:
            recent.append(order)
        else:
            archive.append(order)
    return recent, archive


PAGE_SIZE=20

def completed_page(orders, page=0, page_size=PAGE_SIZE):
    size=max(1,int(page_size))
    pages=max(1,(len(orders)+size-1)//size)
    page=max(0,min(int(page),pages-1))
    return orders[page*size:(page+1)*size],page,pages


def shipping_fee_entered(order):
    from decimal import Decimal, InvalidOperation
    try:
        value=Decimal(str(order.get('kargo_ucreti') or 0).replace(',', '.'))
        return value.is_finite() and value>0
    except (ValueError, InvalidOperation, TypeError):
        return False


def is_returned(order):
    return bool(order.get('iade_tarihi'))
