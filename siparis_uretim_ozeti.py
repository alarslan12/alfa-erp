"""Read-only active-order production totals (copies, not distinct codes)."""

def production_summary(orders, page_count):
    totals = dict(orders=0, books=0, sb=0, rnk=0, ready=0, boxed=0,
                  print_sb=0, print_rnk=0, pages=0, print_pages=0,
                  unknown_pages=0, unknown_print=0, revenue=0.0)
    for order in orders:
        totals['orders'] += 1
        totals['revenue'] += float(order.get('ciro') or 0)
        for item in order.get('kitaplar', []):
            try:
                qty = max(0, int(item.get('adet', 0) or 0))
                ready = min(qty, max(0, int(item.get('hazir', 0) or 0)))
                boxed = min(ready, max(0, int(item.get('koli', 0) or 0)))
                pages = max(0, int(page_count(item) or 0))
            except (TypeError, ValueError):
                continue
            kind = 'rnk' if str(item.get('tur','SB')).upper() in ('RNK','RENKLİ','RENKLI') else 'sb'
            waiting = qty - ready
            totals['books'] += qty
            totals[kind] += qty
            totals['ready'] += ready
            totals['boxed'] += boxed
            totals['print_'+kind] += waiting
            totals['pages'] += qty * pages
            totals['print_pages'] += waiting * pages
            if not pages:
                totals['unknown_pages'] += qty
                totals['unknown_print'] += waiting
    totals['print_waiting'] = totals['books'] - totals['ready']
    totals['pack_ready'] = totals['ready'] - totals['boxed']
    totals['remaining'] = totals['books'] - totals['boxed']
    totals['packed_percent'] = round(100 * totals['boxed'] / totals['books']) if totals['books'] else 0
    return totals


def count_text(n):
    return f'{int(n):,}'.replace(',', '.')


def money_text(n):
    return f'{float(n):,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.') + ' TL'
