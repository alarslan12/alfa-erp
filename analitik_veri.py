"""Qt bağımsız ALFA ERP analitik hesapları.

Önemli: Bu sürüm yalnızca o an kayıtlı siparişlerin durumları üzerinden hesap
üretir. Eski siparişlere geçmişte olmayan işlem/zaman bilgisi atamaz.
Kargo sonrası tutar, net kâr DEĞİLDİR; baskı/işçilik/komisyon düşülmez.
"""
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta
from statistics import mean
from utils import tr_kucult


def num(value):
    try: return float(value or 0)
    except (TypeError, ValueError): return 0.0


def read_date(value):
    try:
        if not value: return None
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def read_datetime(value):
    try:
        if not value: return None
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def shipping_group(order):
    # Önceden tamamlanmış kayıtların kategorisi geriye dönük anlaşılabilir;
    # ancak kargo gideri yalnızca kaydedildiyse düşülür.
    if order.get('kargo_turu') in ('telafi','acik_adres'):
        return order['kargo_turu']
    if 'telafi' in tr_kucult(order.get('siparis_turu','')):
        return 'telafi'
    if 'acik adres' in tr_kucult(order.get('platform','')) or 'acik adres' in tr_kucult(order.get('siparis_turu','')):
        return 'acik_adres'
    return None


def build_dashboard(db, *, days=30, status='all', platform='all', order_kind='all', today=None):
    today = today or date.today()
    start = today - timedelta(days=int(days)-1) if days else None
    selected = []
    for order in db.siparisler:
        created = read_date(order.get('tarih'))
        if days and (created is None or not (start <= created <= today)):
            continue
        stage = db.siparis_durumu(order)
        if status != 'all' and stage != status:
            continue
        if platform != 'all' and str(order.get('platform','')) != platform:
            continue
        ship_kind = shipping_group(order)
        if order_kind != 'all' and ship_kind != order_kind:
            if order_kind != 'diger' or ship_kind is not None:
                continue
        selected.append(order)

    n = len(selected)
    stats = Counter({k:0 for k in (
        'order_havuz','order_aktif','order_tamamlandi',
        'gross','copies_sb','copies_rnk','pages_sb','pages_rnk',
        'ready_sb','ready_rnk','boxed_sb','boxed_rnk',
        'pages_ready','pages_boxed','total_copies_in_orders',
        'shipping_telafi','shipping_acik_adres','shipping_recorded_count',
        'shipping_missing_count','telafi_orders','address_orders',
        'completed_without_date','open_over_7_days'
    )})
    trends_created = Counter()
    trends_completed = Counter()
    trends_revenue = defaultdict(float)
    trends_shipping = defaultdict(float)
    platform_stats = defaultdict(lambda:{'orders':0, 'revenue':0.0})
    books = defaultdict(lambda:{'name':'','group':'','sb':0,'rnk':0,'ready':0,'boxed':0,'pages':0})
    groups = defaultdict(lambda:{'orders':set(),'copies':0,'pages':0})
    completion_hours = []
    for o in selected:
        stage = db.siparis_durumu(o)
        stats['order_'+stage] += 1
        gross = 0.0 if shipping_group(o) == 'telafi' else num(o.get('ciro'))
        stats['gross'] += gross
        created = read_date(o.get('tarih'))
        if stage != 'tamamlandi' and created and (today-created).days >= 7:
            stats['open_over_7_days'] += 1
        completed = read_date(o.get('tamamlanma_tarihi')) if stage == 'tamamlandi' else None
        if created:
            trends_created[created] += 1
            trends_revenue[created] += gross
        if completed:
            trends_completed[completed] += 1
            c_time = read_datetime(o.get('tamamlanma_tarihi'))
            o_time = read_datetime(o.get('tarih'))
            if c_time and o_time:
                try:
                    hrs = (c_time - o_time).total_seconds()/3600
                    if hrs >= 0: completion_hours.append(hrs)
                except TypeError: pass
        elif stage == 'tamamlandi':
            stats['completed_without_date'] += 1
        cat = shipping_group(o)
        if cat == 'telafi': stats['telafi_orders'] += 1
        if cat == 'acik_adres': stats['address_orders'] += 1
        if stage == 'tamamlandi' and o.get('kargo_ucreti') is not None and cat:
            cost = max(0, num(o.get('kargo_ucreti')))
            stats['shipping_'+cat] += cost
            stats['shipping_recorded_count'] += 1
            if completed: trends_shipping[completed] += cost
        elif stage == 'tamamlandi' and cat:
            stats['shipping_missing_count'] += 1
        plat = str(o.get('platform', 'Bilinmiyor')).strip() or 'Bilinmiyor'
        platform_stats[plat]['orders'] += 1
        platform_stats[plat]['revenue'] += gross
        total = 0
        for item in o.get('kitaplar', []):
            code = str(item.get('kod',''))
            book = db.katalog.get(code, {})
            page = max(0, int(num(book.get('sayfa'))))
            qty = max(0, int(num(item.get('adet'))))
            ready = max(0, min(qty, int(num(item.get('hazir')))))
            boxed = max(0, min(ready, int(num(item.get('koli')))))
            kind = 'rnk' if str(item.get('tur','SB')).upper() == 'RNK' else 'sb'
            stats['copies_'+kind] += qty
            stats['pages_'+kind] += qty*page
            stats['ready_'+kind] += ready
            stats['boxed_'+kind] += boxed
            stats['pages_ready'] += ready*page
            stats['pages_boxed'] += boxed*page
            entry = books[code]
            entry['name'] = book.get('isim') or f'Kitap #{code}'
            entry['group'] = book.get('grup') or 'Diğer'
            entry[kind] += qty
            entry['ready'] += ready
            entry['boxed'] += boxed
            entry['pages'] += qty*page
            group = entry['group']
            groups[group]['orders'].add(str(o.get('id')))
            groups[group]['copies'] += qty
            groups[group]['pages'] += qty*page
            total += qty
        stats['total_copies_in_orders'] += total

    sb, rnk = stats['copies_sb'], stats['copies_rnk']
    copies = sb+rnk
    pages = stats['pages_sb']+stats['pages_rnk']
    prepared = stats['ready_sb']+stats['ready_rnk']
    boxed = stats['boxed_sb']+stats['boxed_rnk']
    costs = stats['shipping_telafi']+stats['shipping_acik_adres']
    stats.update({
        'orders':n, 'copies':copies, 'pages':pages, 'ready':prepared, 'boxed':boxed,
        'pending':copies-prepared, 'unboxed':prepared-boxed,
        'shipping_total':costs, 'net_after_shipping':stats['gross']-costs,
        'average_order': stats['gross']/n if n else 0,
        'average_pages': pages/n if n else 0,
        'average_copies':copies/n if n else 0,
        'revenue_per_page':stats['gross']/pages if pages else 0,
        'remaining_pages':pages-stats['pages_ready'],
        'ready_unboxed_pages':stats['pages_ready']-stats['pages_boxed'],
        'ready_rate':prepared/copies*100 if copies else 0,
        'boxed_rate':boxed/copies*100 if copies else 0,
        'completion_rate':stats['order_tamamlandi']/n*100 if n else 0,
        'color_ratio':rnk/copies*100 if copies else 0,
        'telafi_ratio':stats['telafi_orders']/n*100 if n else 0,
        'shipping_telafi_avg':stats['shipping_telafi']/sum(
            1 for o in selected if db.siparis_durumu(o)=='tamamlandi' and
            shipping_group(o)=='telafi' and o.get('kargo_ucreti') is not None) if stats['shipping_telafi'] else 0,
        'shipping_address_avg':stats['shipping_acik_adres']/sum(
            1 for o in selected if db.siparis_durumu(o)=='tamamlandi' and
            shipping_group(o)=='acik_adres' and o.get('kargo_ucreti') is not None) if stats['shipping_acik_adres'] else 0,
        'average_completion_hours':mean(completion_hours) if completion_hours else 0,
        'completion_time_count':len(completion_hours),
    })

    # Günlük seri: filtreye giren siparişler için oluşturma/tamamlama tarihleri.
    # "Tümü" seçilince son 60 gün ile sınırlı grafik, tüm kayıtlar KPI'da.
    span_days = min(int(days or 60), 180)
    chart_start = today - timedelta(days=span_days-1)
    daily=[]
    for i in range(span_days):
        d = chart_start+timedelta(days=i)
        daily.append({'date':d.isoformat(), 'label':d.strftime('%d.%m'),
                      'created':trends_created[d], 'completed':trends_completed[d],
                      'gross':round(trends_revenue[d],2), 'shipping':round(trends_shipping[d],2)})
    all_books = sorted(
        ({'code':k, **v, 'total':v['sb']+v['rnk']} for k,v in books.items()),
        key=lambda b:(-b['total'],-b['pages'],b['name']))
    top_books = all_books[:15]
    all_groups = sorted(({'name':key, 'orders':len(value['orders']),
                            'copies':value['copies'], 'pages':value['pages']}
                           for key, value in groups.items()),key=lambda x:-x['copies'])
    group_result = all_groups[:12]
    if daily:
        stats['daily_completed_avg'] = sum(d['completed'] for d in daily)/len(daily)
        stats['daily_completed_peak'] = max(d['completed'] for d in daily)
        stats['daily_orders_peak'] = max(d['created'] for d in daily)
    platforms = sorted(({'name':k, **v} for k,v in platform_stats.items()),
                       key=lambda v:-v['orders'])
    return {'metrics':dict(stats), 'selected':selected, 'daily':daily,
            'top_books':top_books, 'all_books':all_books, 'groups':group_result,
            'all_groups':all_groups, 'platforms':platforms,
            'start':start, 'today':today, 'days':days}
