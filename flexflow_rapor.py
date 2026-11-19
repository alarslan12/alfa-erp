"""Readable CSV and printable HTML exports for FlexFlow operations.

No hidden machine coefficients appear on the report. Progress event gaps
are shown as 'Kayıt yok', not a fabricated zero.
"""
from __future__ import annotations

import csv
from html import escape
from io import StringIO
from flexflow_operasyon import operation_insight


def _f(value,places=0):
    return f"{float(value):,.{places}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _daily_rows(report):
    logged=set(report.get("logged_days") or [])
    for item in reversed(report["points"]):
        known=item["date"] in logged
        yield (
            item["date"], item["started"], item["orders"], item["books"], item["pages"],
            item["sb"], item["rnk"],
            item["ready"] if known else "Kayıt yok",
            item["boxed"] if known else "Kayıt yok",
        )


def csv_report(report):
    stream=StringIO()
    writer=csv.writer(stream,delimiter=";")
    writer.writerow(["ALFA ERP FlexFlow","Günlük üretim raporu"])
    writer.writerow(["Tarih aralığı",report["start"],report["end"]])
    writer.writerow(["Not","İlerleme saatleri yalnız kayıtlı olaylardan; gerçek işçilik saati ölçümü değildir."])
    writer.writerow(["Günlük ortalama tamamlanan",round(report["average_orders"],2),"sipariş/üretim günü"])
    writer.writerow(["Açık sipariş",report["open_orders"]])
    insight=operation_insight(report)
    writer.writerow([])
    writer.writerow([insight["title"]])
    for key in ("observation","progress","comparison","live","assessment","note"):
        writer.writerow([insight[key]])
    writer.writerow([])
    writer.writerow(["Tarih","Aktife alınan sipariş","Tamamlanan sipariş","Kitap nüshası","Sayfa",
                     "SB kitap","RNK kitap","Hazırlanan (net nüsha)","Kolilenen (net nüsha)"])
    for row in _daily_rows(report):
        writer.writerow(row)
    writer.writerow([])
    writer.writerow(["Seçilen gün",report["selected_day"]])
    writer.writerow(["Saat","Aktife alınan sipariş","Tamamlanan sipariş",
                     "Hazırlanan net nüsha","Kolilenen net nüsha"])
    logged=report["selected_day"] in set(report.get("logged_days") or [])
    for item in report["hourly"]:
        if not (7<=item["hour"]<=17 or any(item[k] for k in ("started","orders","ready","boxed"))):
            continue
        writer.writerow([f'{item["hour"]:02d}:00',item["started"],item["orders"],
                         item["ready"] if logged else "Kayıt yok",
                         item["boxed"] if logged else "Kayıt yok"])
    return stream.getvalue()


def html_report(report):
    logged=set(report.get("logged_days") or [])
    head="""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<title>ALFA ERP · FlexFlow Üretim Raporu</title>
<style>
body{font:14px 'Segoe UI',Arial,sans-serif;color:#1c354b;background:#f6f9fc;
max-width:1100px;margin:28px auto;padding:0 20px}
h1{margin-bottom:0}p{line-height:1.5}small{color:#60788c}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}
.card{padding:12px;border:1px solid #d8e4ef;border-radius:10px;background:white}
.card b{font-size:22px;display:block;margin-top:5px}
table{background:white;border-collapse:collapse;width:100%;margin-top:10px}
td,th{padding:9px 10px;text-align:left;border-bottom:1px solid #dbe4eb}
th{background:#e4eff8}.note{padding:12px;border-left:4px solid #e6b35e;background:#fff6e6}
@media print{body{background:white}.card{break-inside:avoid}}
</style></head><body>"""
    ranged=report["start"]!=report["end"]
    selected=report["period"] if ranged else report["selected"]
    cards=[
        ("Seçili dönemde tamamlanan",str(selected["orders"])+" sipariş"),
        ("Şu an açık sipariş",str(report["open_orders"])),
        ("Önceki üretim günleri ortalaması",_f(report["average_orders"],1)+" sipariş/gün"),
        ("Seçili son günün planlı vardiya temposu",_f(report["selected_rate"],2)+" sipariş/sa"),
        ("Şu an baskı/hazırlık bekleyen",str(report["open_work"]["print_waiting"])+" nüsha"),
        ("Şu an kolilemeye hazır",str(report["open_work"]["pack_ready"])+" nüsha"),
    ]
    summary="".join("<div class='card'><small>"+escape(k)+"</small><b>"+escape(v)+"</b></div>"
                    for k,v in cards)
    daily_headers=["Tarih","Aktife alınan","Tamamlanan","Kitap","Sayfa","SB","RNK","Hazırlanan","Kolilenen"]
    daily="<tr>"+"".join("<th>"+escape(x)+"</th>" for x in daily_headers)+"</tr>"
    for values in _daily_rows(report):
        daily+="<tr>"+"".join("<td>"+escape(str(x))+"</td>" for x in values)+"</tr>"
    hour_headers=["Saat","Aktife alınan","Tamamlanan","Hazırlanan","Kolilenen"]
    hour="<tr>"+"".join("<th>"+escape(x)+"</th>" for x in hour_headers)+"</tr>"
    for x in report["hourly"]:
        if not (7<=x["hour"]<=17 or any(x[k] for k in ("started","orders","ready","boxed"))):
            continue
        known=report["selected_day"] in logged
        values=(f'{x["hour"]:02d}:00',x["started"],x["orders"],
                x["ready"] if known else "Kayıt yok",
                x["boxed"] if known else "Kayıt yok")
        hour+="<tr>"+"".join("<td>"+escape(str(v))+"</td>" for v in values)+"</tr>"
    insight=operation_insight(report)
    interpretation=(
        "<h2>"+escape(insight["title"])+"</h2><div class='note'>"+
        "".join("<p>"+escape(insight[key])+"</p>" for key in
                ("observation","progress","comparison","live","assessment","note"))+
        "</div>")
    return (
        head+"<h1>FlexFlow · Üretim raporu</h1><small>"+escape(report["start"])+
        " – "+escape(report["end"])+"</small>"+interpretation+
        "<div class='grid'>"+summary+
        "</div><p class='note'>İşlem günlüğü olmayan hazır/kolileme hareketleri "
        "geriye dönük saatlere dağıtılmaz. Rapor, kayıtlı sipariş ve olaylara "
        "dayanır; gerçek personel çalışma süreleri veya makine telemetrisi "
        "değildir.</p><h2>Günlük üretim</h2><table>"+daily+
        "</table><h2>Saatlik üretim · "+escape(report["selected_day"])+
        "</h2><table>"+hour+"</table></body></html>"
    )
