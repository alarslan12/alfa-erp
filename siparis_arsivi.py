"""Tamamlanan siparişlerin son 5 gün ve istek üzerine açılan arşiv ayrımı.

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


def ayir_tamamlananlar(orders, today=None, window_days=5):
    """[bugün-4, bugün] aralığı güncel; daha eskiler/bilinmeyenler arşivdir."""
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
