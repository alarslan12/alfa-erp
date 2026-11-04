"""Validate and map Supabase orders into pre-existing desktop order JSON structure."""
from datetime import datetime


def _timestamp(value):
    raw = str(value or '').strip()
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00')).astimezone().isoformat(timespec='seconds')
    except (TypeError, ValueError, OverflowError):
        return datetime.now().astimezone().isoformat(timespec='seconds')


def convert_mobile_order(row, items, catalog):
    """Reject partial/broken imports so the normal Havuz never receives bad cards."""
    uuid = str(row.get('id', '')).strip()
    if not uuid:
        raise ValueError('Bulut siparişi kimliği boş.')
    status = str(row.get('status', 'havuz'))
    if status not in ('havuz', 'aktif', 'tamamlandi'):
        raise ValueError('Bulut siparişinde bilinmeyen durum: ' + status)
    if not isinstance(items, list) or not items:
        raise ValueError('Bulut siparişinin kitap satırları bulunamadı: ' + uuid)
    book_list = []
    for item in items:
        code = str(item.get('book_code', '')).strip()
        kind = str(item.get('print_type', 'SB')).upper()
        if not code or code not in catalog:
            raise ValueError('Yerel katalogda bulunmayan kitap: ' + code)
        if kind not in ('SB', 'RNK'):
            raise ValueError('Geçersiz baskı türü: ' + kind)
        count = int(item['quantity'])
        ready = int(item.get('prepared_count', 0))
        boxed = int(item.get('boxed_count', 0))
        if not 0 <= boxed <= ready <= count or not count:
            raise ValueError('Geçersiz mobil hazırlık/koli sayısı: ' + code)
        book_list.append({'kod': code, 'tur': kind, 'adet': count,
                          'hazir': ready, 'koli': boxed,
                          'sayfa_birim': max(0,int(item.get('page_count_snapshot') or 0))})
    if len({(i['kod'],i['tur']) for i in book_list}) != len(book_list):
        raise ValueError('Bulut siparişinde yinelenen kitap türü.')
    output = {
        'tarih': _timestamp(row.get('created_at')),
        'platform': str(row.get('platform') or 'Manuel'),
        'kod': str(row.get('shipping_reference') or ''),
        'siparis_turu': str(row.get('order_type') or ''),
        'ciro': float(row.get('gross_amount') or 0),
        'durum': status,
        'kitaplar': book_list,
        'bulut_id': uuid,
        'bulut_siparis_no': int(row.get('order_number') or 0),
        'bulut_version': int(row.get('version') or 1),
    }
    if row.get('shipping_fee') is not None:
        output['kargo_ucreti'] = float(row['shipping_fee'])
    if status in ('aktif', 'tamamlandi'):
        output['isleme_alinma_tarihi'] = _timestamp(row.get('started_at') or row.get('created_at'))
    if status == 'tamamlandi':
        output['tamamlanma_tarihi'] = _timestamp(row.get('completed_at') or row.get('created_at'))
    return output
