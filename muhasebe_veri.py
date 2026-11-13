"""Tamamlanan siparişlerin muhasebe özeti ve gün bazlı ödeme durumu.

Muhasebe dönemi tamamlanma_tarihi üzerinden belirlenir; havuz ve aktif
siparişlerden hiçbir tutar/kitap/sayfa muhasebe toplamına eklenmez.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from html import escape
import json
import os
import tempfile
import hashlib

from analitik_veri import read_date, num, shipping_group


def accounting_revenue(order):
    """A compensation shipment is not a sale, even for legacy records."""
    return 0.0 if shipping_group(order) == "telafi" else num(order.get('ciro'))



class PaymentDays:
    """Kullanıcı veri klasöründe atomik kayıt. Geçersiz dosyayı sessizce ezmez."""
    filename = 'alfa_muhasebe_gunleri.json'

    def __init__(self, data_dir):
        self.path = Path(data_dir) / self.filename
        self.paid = set()
        self.snapshots = {}
        if self.path.exists():
            try:
                value = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(value, dict) or not isinstance(value.get('paid', []), list):
                    raise ValueError('Ödeme günleri dosyası geçersiz.')
                for value_str in value['paid']:
                    day = date.fromisoformat(value_str)
                    self.paid.add(day.isoformat())
                stored = value.get('snapshots', {})
                if not isinstance(stored, dict):
                    raise ValueError('Muhasebe kontrol dosyasında beklenmeyen imza formatı.')
                self.snapshots = {str(k):str(v) for k,v in stored.items() if k in self.paid}
            except (ValueError, OSError, TypeError) as exc:
                raise RuntimeError('Muhasebe ödeme dosyası okunamadı; eski kayıt korunuyor.') from exc

    def apply_cloud(self, rows):
        """Authoritative Supabase payment-day mirror; do not write another local copy."""
        valid=[x for x in rows if isinstance(x,dict) and x.get('accounting_day')]
        self.paid={str(x['accounting_day']) for x in valid if x.get('paid')}
        self.snapshots={str(x['accounting_day']):str(x['completion_fingerprint'])
                        for x in valid if x.get('paid') and x.get('completion_fingerprint')}

    def effective_paid(self, signatures):
        # A new completed order or changed ciro/kargo invalidates a day's approval.
        return {day for day in self.paid if not self.snapshots.get(day) or
                self.snapshots[day] == signatures.get(day)}

    def set_paid(self, keys, paid, signatures=None):
        keys = {date.fromisoformat(str(d)).isoformat() for d in keys}
        newer = (self.paid | keys) if paid else (self.paid - keys)
        snapshots = dict(self.snapshots)
        if paid and signatures is not None:
            snapshots.update({day:signatures[day] for day in keys if day in signatures})
        elif not paid:
            for day in keys:
                snapshots.pop(day, None)
        if newer == self.paid and snapshots == self.snapshots:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.alfa_payment_', suffix='.tmp', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump({'version':2, 'paid':sorted(newer), 'snapshots':snapshots}, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        self.paid = newer
        self.snapshots = snapshots
        return True


def completion_fingerprints(db):
    """Signature by completed date; a newly completed or edited order requires review."""
    groups = defaultdict(list)
    for order in db.siparisler:
        if db.siparis_durumu(order) != 'tamamlandi':
            continue
        day = read_date(order.get('tamamlanma_tarihi'))
        if day:
            groups[day.isoformat()].append((str(order.get('bulut_id') or order.get('id','')),
                order.get('ciro'),order.get('kargo_turu'),order.get('kargo_ucreti'),
                order.get('kitaplar')))
    result={}
    for day,rows in groups.items():
        payload=json.dumps(sorted(rows,key=lambda row:row[0]),ensure_ascii=False,
                           sort_keys=True,default=str,separators=(',',':'))
        result[day]=hashlib.sha256(payload.encode('utf-8')).hexdigest()
    return result


def accounting_days(db):
    """Returns completion dates and *informational* active-only creation dates."""
    completed = Counter()
    active = Counter()
    for order in db.siparisler:
        stage = db.siparis_durumu(order)
        if stage == 'tamamlandi':
            d = read_date(order.get('tamamlanma_tarihi'))
            if d:
                completed[d.isoformat()] += 1
        elif stage == 'aktif':
            d = read_date(order.get('tarih'))
            if d:
                active[d.isoformat()] += 1
    return completed, active


def completed_summary(db, start, end):
    """Report strictly of completed orders whose completion date is in [start,end]."""
    if start is None or end is None:
        raise ValueError('Rapor tarih aralığı seçilmedi.')
    start, end = sorted((date.fromisoformat(str(start)),date.fromisoformat(str(end))))
    chosen = []
    counts = Counter()
    daily = defaultdict(lambda: {'orders':0, 'gross':0.0, 'shipping':0.0, 'pages':0, 'sb':0, 'rnk':0})
    platform = defaultdict(lambda: {'orders':0,'gross':0.0,'pages':0,'books':0})
    book_totals = {}
    for order in db.siparisler:
        if db.siparis_durumu(order) != 'tamamlandi':
            continue
        completion = read_date(order.get('tamamlanma_tarihi'))
        if completion is None or not start <= completion <= end:
            continue
        chosen.append(order)
        day = daily[completion.isoformat()]
        gross = accounting_revenue(order)
        group = shipping_group(order)
        ship = max(0.0,num(order.get('kargo_ucreti'))) if group in ('telafi','acik_adres') and order.get('kargo_ucreti') is not None else 0.0
        day['orders'] += 1; day['gross'] += gross; day['shipping'] += ship
        counts['gross'] += gross; counts['orders'] += 1
        counts['shipping'] += ship
        if group in ('telafi', 'acik_adres'):
            counts['shipping_' + group] += ship
            if order.get('kargo_ucreti') is None:
                counts['shipping_missing'] += 1
        label = str(order.get('platform') or 'Bilinmiyor').strip() or 'Bilinmiyor'
        platform[label]['orders'] += 1; platform[label]['gross'] += gross
        for item in order.get('kitaplar', []):
            qty = max(0, int(num(item.get('adet'))))
            book = db.katalog.get(str(item.get('kod')), {})
            page = max(0, int(num(item.get('sayfa_birim') if item.get('sayfa_birim') is not None else book.get('sayfa'))))
            pages = qty * page
            kind = 'rnk' if str(item.get('tur','SB')).upper() == 'RNK' else 'sb'
            counts[kind] += qty; counts['pages_'+kind] += pages
            counts['pages'] += pages; counts['books'] += qty
            day[kind] += qty; day['pages'] += pages
            day['books'] = day.get('books', 0) + qty
            code = str(item.get('kod', ''))
            bentry = book_totals.setdefault(code, {
                'kod': code, 'isim': str(book.get('isim') or f'Kitap #{code}'),
                'sb': 0, 'rnk': 0, 'pages': 0,
            })
            bentry[kind] += qty
            bentry['pages'] += pages
            platform[label]['books'] += qty
            platform[label]['pages'] += pages
    orders = counts['orders']
    days = (end - start).days + 1
    result = {
        'orders': orders,
        'gross': round(counts['gross'],2),
        'shipping_total': round(counts['shipping'],2),
        'shipping_telafi': round(counts['shipping_telafi'],2),
        'shipping_acik_adres': round(counts['shipping_acik_adres'],2),
        'shipping_missing': counts['shipping_missing'],
        'after_shipping': round(counts['gross']-counts['shipping'],2),
        'avg_order': counts['gross']/orders if orders else 0.0,
        'pages': counts['pages'], 'pages_sb':counts['pages_sb'], 'pages_rnk':counts['pages_rnk'],
        'books':counts['books'], 'sb':counts['sb'], 'rnk':counts['rnk'],
        'avg_pages':counts['pages']/orders if orders else 0.0,
        'avg_books':counts['books']/orders if orders else 0.0,
        'per_page': counts['gross']/counts['pages'] if counts['pages'] else 0.0,
        'avg_daily_completed':orders/days if days else 0.0,
        'unique_books':len(book_totals),
        'rnk_share':100*counts['rnk']/counts['books'] if counts['books'] else 0.0,
        'avg_pages_book':counts['pages']/counts['books'] if counts['books'] else 0.0,
        'shipping_ratio':100*counts['shipping']/counts['gross'] if counts['gross']>0 else 0.0,
        'working_days':sum(1 for value in daily.values() if value['orders']),
    }
    # Bounded data series: dates missing activity intentionally hold zero.
    points=[]
    for i in range(days):
        day = (start+timedelta(days=i)).isoformat()
        point = daily[day]
        points.append({'date':day,'label':day[5:7]+'/'+day[8:10], **point})
    platforms=sorted(({'name':key,**value} for key,value in platform.items()), key=lambda d:-d['orders'])
    books=sorted(({**value,'adet':value['sb']+value['rnk']} for value in book_totals.values()),
                 key=lambda row:(-row['adet'],str(row['isim']).casefold()))
    return {'start':start.isoformat(), 'end':end.isoformat(), 'metrics':result,
            'orders':sorted(chosen,key=lambda o:str(o.get('tamamlanma_tarihi','')),reverse=True),
            'daily':points,'platforms':platforms,'books_ranked':books}


def html_report(data, paid_days, review_days=None):
    """Single-file, print-friendly HTML with escaped user-controlled text."""
    review_days = set(review_days or [])
    def esc(val): return escape(str(val), quote=True)
    def money(v): return f'{v:,.2f} TL'
    metric=data['metrics']
    paid_amount=sum(accounting_revenue(o) for o in data['orders']
                    if str(o.get('tamamlanma_tarihi',''))[:10] in paid_days)
    rows=[('Tamamlanan sipariş',metric['orders']),('Toplam ciro',money(metric['gross'])),
          ('Ödenen ciro',money(paid_amount)),
          ('Ödenmeyen ciro',money(metric['gross']-paid_amount)),
          ('Telafi kargo',money(metric['shipping_telafi'])),('Açık adres kargo',money(metric['shipping_acik_adres'])),
          ('Toplam kargo',money(metric['shipping_total'])),('Kargo sonrası ciro',money(metric['after_shipping'])),
          ('Ortalama sipariş',money(metric['avg_order'])),('Toplam kitap',metric['books']),
          ('SB / RNK kitap',f"{metric['sb']} / {metric['rnk']}"),('Toplam sayfa',metric['pages']),
          ('SB / RNK sayfa',f"{metric['pages_sb']} / {metric['pages_rnk']}"),
          ('Sipariş başı sayfa',f"{metric['avg_pages']:.1f}"),
          ('Sipariş başı kitap',f"{metric['avg_books']:.1f}"),
          ('Sayfa başına ciro',money(metric['per_page'])),
          ('Renkli baskı oranı',f"{metric['rnk_share']:.1f}%"),
          ('Farklı kitap çeşidi',metric['unique_books']),
          ('Tamamlanan iş günü',metric['working_days']),
          ('Kargo / ciro oranı',f"{metric['shipping_ratio']:.1f}%")]
    kpis=''.join(f'<div class="kpi"><small>{esc(k)}</small><strong>{esc(v)}</strong></div>' for k,v in rows)
    days=''.join('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in (
        d['date'], d['orders'], money(d['gross']), money(d['shipping']), money(d['gross']-d['shipping']),
        'ÖDENDİ' if d['date'] in paid_days else 'YENİDEN KONTROL' if d['date'] in review_days else 'ÖDENMEDİ' if d['orders'] else '—'
    ))+'</tr>' for d in data['daily'] if d['orders'])
    orders=''.join('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in (
        o.get('id',''), str(o.get('tamamlanma_tarihi',''))[:16].replace('T',' '),
        o.get('platform',''),money(accounting_revenue(o)),
        money(num(o.get('kargo_ucreti'))) if o.get('kargo_ucreti') is not None else '—',
        o.get('kargo_turu') or '—'
    ))+'</tr>' for o in data['orders'])
    platforms=''.join(f'<tr><td>{esc(d["name"])}</td><td>{d["orders"]}</td><td>{esc(money(d["gross"]))}</td></tr>' for d in data['platforms'])
    bookrows=''.join('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in (
        x['kod'],x['isim'],x['adet'],x['sb'],x['rnk'],x['pages'])) + '</tr>'
        for x in data.get('books_ranked', []))
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>ALFA ERP Muhasebe {esc(data['start'])}</title>
<style>body{{font:14px Arial,sans-serif;color:#1c2b3b;max-width:1100px;margin:25px auto;padding:0 18px}}h1{{margin-bottom:4px}}p{{color:#53657a}}.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px}}.kpi{{border:1px solid #bdcad8;border-radius:7px;padding:10px}}small{{display:block;color:#64748b}}strong{{display:block;font-size:17px;margin-top:4px}}table{{border-collapse:collapse;width:100%;margin:13px 0 25px}}th,td{{padding:7px;border-bottom:1px solid #d5dfea;text-align:left}}th{{background:#e8eff7}}h2{{margin-top:25px}}@media print{{body{{margin:8mm}}.kpi{{break-inside:avoid}}}}</style></head><body>
<h1>ALFA ERP · Muhasebe Raporu</h1><p>Gerçekleşen tamamlanma tarihi: {esc(data['start'])} — {esc(data['end'])} · Yalnızca tamamlanan siparişler</p>
<div class="tiles">{kpis}</div><h2>Günlük muhasebe</h2><table><thead><tr><th>Gün</th><th>Sipariş</th><th>Ciro</th><th>Kargo</th><th>Kargo sonrası</th><th>Ödeme</th></tr></thead><tbody>{days}</tbody></table>
<h2>Platformlar</h2><table><thead><tr><th>Platform</th><th>Sipariş</th><th>Ciro</th></tr></thead><tbody>{platforms}</tbody></table>
<h2>En çok tamamlanan kitaplar</h2><table><thead><tr><th>Kod</th><th>Kitap</th><th>Adet</th><th>SB</th><th>RNK</th><th>Sayfa</th></tr></thead><tbody>{bookrows}</tbody></table>
<h2>Tamamlanan sipariş listesi</h2><table><thead><tr><th>No</th><th>Tamamlanma</th><th>Platform</th><th>Ciro</th><th>Kargo</th><th>Kargo türü</th></tr></thead><tbody>{orders}</tbody></table>
<p>Not: Kargo sonrası tutar, yalnızca kayıtlı Telafi/Açık Adres kargo ücretleri düşülmüş cirodur; kâr hesabı değildir. Ücret kaydı eksik sipariş sayısı: {metric['shipping_missing']}.</p></body></html>'''
