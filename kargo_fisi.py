"""ALFA ERP - seçili aktif siparişler için bağımsız, yazdırılabilir HTML.

Hiçbir Flet bağımlılığı veya çevrimiçi font/script gerektirmez.
Bu çıktı, kargo firmasınca düzenlenen resmi barkodlu taşıma etiketi değil,
siparişle koli eşleştirmek için dahili baskı şerididir.
"""
from datetime import datetime
from html import escape
from pathlib import Path
import os
import tempfile
import webbrowser


def olustur_html(siparisler, db):
    """A4'te yüksek yoğunluklu kesim şeritleri; dış veri HTML-escape edilir."""
    if not siparisler:
        raise ValueError('En az bir sipariş gerekli.')
    fisler = []
    for s in siparisler:
        ozet = db.siparis_ozeti(s)
        kitaplar = []
        for g in db.siparis_gruplari(s):
            kitaplar.append(
                f'<span class="book"><b>{escape(str(g["kod"]))}</b> '
                f'({g["adet"]} adet; SB {g["sb"]}, RNK {g["rnk"]})</span>'
            )
        kod = escape(str(s.get('kod', '') or 'KOD YOK'))
        platform = escape(str(s.get('platform', '—')))
        siparis_no = escape(str(s.get('id', '—')))
        tarih = escape(str(s.get('tarih', '—')).replace('T', ' ')[:16])
        ciro = float(s.get('ciro', 0) or 0)
        ciro_yazi = f'{ciro:,.2f} TL'
        fisler.append(
            '<section class="label">'
            f'<div class="code"><strong>{kod}</strong><small>KES / AYIR</small></div>'
            '<div class="detail">'
            f'<div class="heading"><b>#{siparis_no}</b><span>{platform}</span><time>{tarih}</time></div>'
            f'<div class="stats"><b>{ozet["adet"]} kitap</b><b>{ozet["sayfa"]:,} sayfa</b>'
            f'<b>SB {ozet["sb"]}</b><b>RNK {ozet["rnk"]}</b>'
            f'<b>{ciro_yazi}</b></div>'
            f'<div class="books">{" · ".join(kitaplar)}</div>'
            '</div></section>'
        )
    css = '''
    @page { size: A4 portrait; margin: 7mm; }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; background: #fff; color: #161616;
                 font-family: Arial, Helvetica, sans-serif; }
    .sheet { display: flex; flex-direction: column; gap: 2.5mm; }
    .label { display: flex; width: 100%; min-height: 30mm; border: 1.3px dashed #555;
             break-inside: avoid; page-break-inside: avoid; background:#fff; }
    .code { width: 36%; flex-shrink: 0; padding: 2.2mm 3.5mm;
            border-right: 1.5px dashed #555; display:flex; flex-direction:column;
            justify-content: center; align-items:center; gap:2mm; text-align:center; }
    .code strong { font-weight: 800; font-size: 17pt; line-height: 1.12;
                   overflow-wrap: anywhere; word-break:break-word; }
    .code small { color: #666; font-size: 6pt; letter-spacing: 2px; }
    .detail { flex:1; min-width:0; padding:2.5mm 3mm; display:flex;
              flex-direction:column; justify-content:space-between; gap:1.5mm; }
    .heading { display:flex; align-items:center; gap:3mm; flex-wrap:wrap; }
    .heading b { font-size: 12pt; }
    .heading span { border:1px solid #444; border-radius:2px; padding:1mm 2mm;
                    font-size:8pt; font-weight:600; }
    .heading time { margin-left:auto; font-size:8pt; color:#555; }
    .stats { display:flex; flex-wrap:wrap; gap:2mm 4mm; font-size:9.2pt; }
    .books { font-size:7.8pt; line-height:1.22; color:#333;
             overflow-wrap:anywhere; }
    .book { display:inline; }
    .toolbar { background:#23262e; color:#fff; display:flex; align-items:center;
               padding:10px 18px; gap:12px; margin-bottom:12px; }
    .toolbar button { padding:7px 14px; background:#f0ad64; border:0; border-radius:5px;
                      cursor:pointer; font-weight:700; }
    .toolbar p { margin:0; font-size:12px; }
    @media print {
      .toolbar { display:none !important; }
      .label { box-shadow:none; }
      body { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
    }
    '''
    toplam = len(siparisler)
    return (
        '<!doctype html><html lang="tr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>ALFA ERP | {toplam} Kargo Fişi</title><style>{css}</style></head>'
        '<body><div class="toolbar"><button onclick="window.print()">YAZDIR (Ctrl+P)</button>'
        f'<p>{toplam} sipariş · A4 / şerit baskı · Kesik çizgiler kesim sınırıdır.</p></div>'
        f'<main class="sheet">{"".join(fisler)}</main>'
        '<script>window.addEventListener("load", function(){window.setTimeout(function(){window.print();}, 250);});</script>'
        '</body></html>'
    )


def dosyaya_yaz(siparisler, db, hedef_klasor=None, zaman=None):
    """Kullanıcı verilerinden yerel geçici dosya üretir; dosyayı silmez."""
    folder = Path(hedef_klasor or (Path(tempfile.gettempdir()) / 'alfa_erp_baski'))
    folder.mkdir(parents=True, exist_ok=True)
    zaman = zaman or datetime.now()
    yol = folder / f'kargo_fisleri_{zaman:%Y%m%d_%H%M%S_%f}.html'
    yol.write_text(olustur_html(siparisler, db), encoding='utf-8')
    return yol


def tarayicida_ac(yol):
    """Yerel dosyayı varsayılan tarayıcıda açar; baskı JS tarafından tetiklenir."""
    yol = Path(yol).resolve()
    if not yol.is_file():
        raise FileNotFoundError(yol)
    if os.name == 'nt':
        os.startfile(str(yol))  # Windows dosya ilişkilendirmesi
        return True
    return webbrowser.open(yol.as_uri())
