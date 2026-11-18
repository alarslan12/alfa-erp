"""Owner-only FlexFlow operations dashboard.

Designed for operators: real counts, daily/hourly pace, current queue and a
plain-language shift forecast. Fixed engineering coefficients stay in
flexflow.py and never appear as confusing user-facing performance claims.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QFrame, QFileDialog, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QScrollArea, QComboBox, QProgressBar,
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QAbstractItemView,
)
from flexflow_operasyon import daily_dashboard
from flexflow_rapor import csv_report, html_report


def fmt(value, places=0):
    return f"{float(value):,.{places}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def palette():
    light=str(QApplication.instance().property("alfa_theme") or "koyu")=="acik"
    return {
        "panel":"#ffffff" if light else "#172a40",
        "text":"#1c354b" if light else "#eff7ff",
        "muted":"#617889" if light else "#b9d1e4",
        "border":"#d6e1ea" if light else "#3b5673",
        "track":"#e4edf5" if light else "#273d53",
    }


class MetricCard(QFrame):
    def __init__(self,title,color,parent=None):
        super().__init__(parent)
        self.color=color
        self.setObjectName("FlexFlowMetric")
        self.setMinimumHeight(106)
        root=QVBoxLayout(self)
        root.setContentsMargins(13,10,13,10)
        root.setSpacing(4)
        self.title=QLabel(title)
        self.value=QLabel("—")
        self.value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.description=QLabel("")
        self.description.setWordWrap(True)
        root.addWidget(self.title)
        root.addWidget(self.value)
        root.addWidget(self.description)

    def update_values(self,value,description):
        p=palette()
        self.setStyleSheet(
            "QFrame#FlexFlowMetric{background:"+p["panel"]+
            ";border:1px solid "+p["border"]+";border-radius:11px;}"
            "QLabel{background:transparent;border:0;color:"+p["text"]+";}"
        )
        self.title.setStyleSheet("color:"+p["muted"]+";font-weight:750;font-size:12px")
        self.value.setStyleSheet("color:"+self.color+";font-weight:900;font-size:22px")
        self.description.setStyleSheet("color:"+p["muted"]+";font-size:11px")
        self.value.setText(str(value))
        self.description.setText(str(description))


class BacklogPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("FlexFlowBacklog")
        root=QVBoxLayout(self)
        root.setContentsMargins(15,13,15,14)
        root.setSpacing(9)
        title=QLabel("AÇIK İŞLERİN DURUMU")
        title.setStyleSheet("font-weight:900;font-size:13px;")
        root.addWidget(title)
        self.labels=[]
        self.bars=[]
        for label,color in (
            ("Baskı / hazırlık bekliyor","#60baff"),
            ("Kolilemeye hazır","#f3bf70"),
            ("Kolilenmiş","#59d8aa"),
        ):
            row=QHBoxLayout()
            caption=QLabel(label)
            count=QLabel("—")
            count.setStyleSheet("font-weight:850;")
            row.addWidget(caption)
            row.addStretch()
            row.addWidget(count)
            root.addLayout(row)
            bar=QProgressBar()
            bar.setTextVisible(False)
            bar.setRange(0,1000)
            bar.setFixedHeight(13)
            bar.setStyleSheet(
                "QProgressBar{background:"+palette()["track"]+
                ";border:0;border-radius:6px;}"
                "QProgressBar::chunk{background:"+color+";border-radius:6px;}"
            )
            root.addWidget(bar)
            self.labels.append(count)
            self.bars.append(bar)
        self.subtitle=QLabel("")
        self.subtitle.setWordWrap(True)
        root.addWidget(self.subtitle)

    def refresh(self,work):
        total=int(work["books"])
        values=[int(work["print_waiting"]),int(work["pack_ready"]),int(work["boxed"])]
        for val,label,bar in zip(values,self.labels,self.bars):
            label.setText(fmt(val)+" nüsha")
            bar.setValue(round(1000*val/total) if total else 0)
        self.subtitle.setText(
            "Açık siparişlerde toplam "+fmt(total)+" kitap nüshasının durumu. "
            "Tamamlanmış siparişler bu stok hesabına tekrar eklenmez."
        )


class FlexFlowView(QWidget):
    def __init__(self,db,parent=None):
        super().__init__(parent)
        self.db=db
        self.latest=None
        self.setObjectName("FlexFlowPage")
        # Import on construction, not at module import: AnalitikView creates
        # this view while ekran_analitik is already being imported.
        from ekran_analitik import LineChart
        outer=QVBoxLayout(self)
        outer.setContentsMargins(3,3,3,3)
        area=QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(area)
        content=QWidget()
        area.setWidget(content)
        root=QVBoxLayout(content)
        root.setContentsMargins(9,11,12,16)
        root.setSpacing(12)

        toolbar=QHBoxLayout()
        heading=QLabel("FLEXFLOW  ·  ÜRETİM PANOSU")
        heading.setStyleSheet("font-size:18px;font-weight:900")
        toolbar.addWidget(heading)
        toolbar.addStretch()
        self.period=QComboBox()
        self.period.setMinimumWidth(112)
        for label,n in (("Son 7 gün",7),("Son 14 gün",14),("Son 30 gün",30)):
            self.period.addItem(label,n)
        self.period.setCurrentIndex(1)
        self.period.currentIndexChanged.connect(self._period_changed)
        toolbar.addWidget(self.period)
        self.export_csv=QPushButton("CSV")
        self.export_html=QPushButton("HTML Rapor")
        self.export_csv.clicked.connect(lambda:self.export("csv"))
        self.export_html.clicked.connect(lambda:self.export("html"))
        toolbar.addWidget(self.export_csv)
        toolbar.addWidget(self.export_html)
        reload=QPushButton("↻ Güncelle")
        reload.clicked.connect(self.refresh)
        toolbar.addWidget(reload)
        root.addLayout(toolbar)

        intro=QLabel(
            "Günlük üretim hareketleri, işlerin ilerlemesi ve tamamlanma temposu. "
            "Buradaki saatlik rakamlar kaydedilmiş işlemlere dayanır."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.cards=[]
        kpis=QGridLayout()
        kpis.setSpacing(10)
        for i,(name,color) in enumerate((
            ("Bugün tamamlanan","#51d6a6"),
            ("Bugün hazırlanan","#6cbcff"),
            ("Bugün kolilenen","#f1c275"),
            ("Açık sipariş","#b9a5f5"),
            ("Tamamlama temposu","#5ac9e8"),
            ("Ortalama karşılaştırması","#e3a3d8"),
        )):
            card=MetricCard(name,color)
            kpis.addWidget(card,i//3,i%3)
            self.cards.append(card)
        for col in range(3):kpis.setColumnStretch(col,1)
        root.addLayout(kpis)
        self.data_note=QLabel()
        self.data_note.setWordWrap(True)
        root.addWidget(self.data_note)

        charts=QGridLayout()
        charts.setSpacing(10)
        self.completed_chart=LineChart("Günlük tamamlanan sipariş",[("orders","Sipariş","#51d6a6")])
        self.progress_chart=LineChart("Günlük hazırlanan / kolilenen nüsha",[
            ("ready","Hazırlandı","#60baff"),("boxed","Kolilendi","#f1c275")
        ])
        for chart,col in ((self.completed_chart,0),(self.progress_chart,1)):
            chart.setFixedHeight(237)
            charts.addWidget(chart,0,col)
            charts.setColumnStretch(col,1)
        root.addLayout(charts)

        self.backlog=BacklogPanel()
        root.addWidget(self.backlog)
        self.shift_note=QLabel()
        self.shift_note.setWordWrap(True)
        self.shift_note.setStyleSheet("font-size:12px;font-weight:800;padding:8px;")
        root.addWidget(self.shift_note)

        hourly_head=QHBoxLayout()
        hourly_title=QLabel("SAAT SAAT ÜRETİM HAREKETLERİ")
        hourly_title.setStyleSheet("font-weight:900;font-size:13px")
        hourly_head.addWidget(hourly_title)
        hourly_head.addStretch()
        self.selected_day=QComboBox()
        self.selected_day.setMinimumWidth(135)
        self.selected_day.currentIndexChanged.connect(self.refresh)
        hourly_head.addWidget(self.selected_day)
        root.addLayout(hourly_head)

        self.hourly_chart=LineChart("Seçilen gün · saatlik sipariş akışı",[
            ("started","Aktife alındı","#6cbcff"),
            ("orders","Tamamlandı","#51d6a6")
        ])
        self.hourly_chart.setFixedHeight(230)
        root.addWidget(self.hourly_chart)

        self.hourly_table=self._table(
            ["Saat","Aktife alınan","Tamamlanan",
             "Hazırlanan nüsha","Kolilenen nüsha"],
            345,
        )
        root.addWidget(self.hourly_table)
        daily_title=QLabel("GÜNLÜK ÜRETİM RAPORU")
        daily_title.setStyleSheet("font-weight:900;font-size:13px")
        root.addWidget(daily_title)
        self.daily_table=self._table(
            ["Tarih","Tamamlanan","Kitap","Basılan sayfa",
             "Hazırlanan","Kolilenen"],315,
        )
        root.addWidget(self.daily_table)
        info=QLabel(
            "Hazırlandı ve kolilendi işlemleri, işlem günlüğünde zaman damgası "
            "bulunduğu günler için gösterilir. Günlüğü bulunmayan geçmiş "
            "işlemler saatlere dağıtılmaz. 'Nüsha' kitap adedini, "
            "'sipariş' ise ayrı sipariş kayıtlarını ifade eder."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size:11px;")
        root.addWidget(info)
        root.addStretch()

    @staticmethod
    def _table(headers,height):
        table=QTableWidget(0,len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(25)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setFixedHeight(height)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    @staticmethod
    def _rows(table,rows):
        table.setUpdatesEnabled(False)
        try:
            table.setRowCount(len(rows))
            for i,row in enumerate(rows):
                for j,value in enumerate(row):
                    item=table.item(i,j)
                    if item is None:
                        item=QTableWidgetItem()
                        table.setItem(i,j,item)
                    item.setText(str(value))
        finally:
            table.setUpdatesEnabled(True)

    def _period_changed(self,*_):
        self.selected_day.clear()
        self.refresh()

    def refresh(self,*_):
        try:
            days=int(self.period.currentData() or 14)
            current=self.selected_day.currentData()
            events=getattr(self.db,"production_events",[])
            report=daily_dashboard(self.db,events,days=days,selected_day=current)
            self.latest=report
        except Exception as exc:
            QMessageBox.warning(self,"FlexFlow","Üretim panosu yenilenemedi: "+str(exc)[:240])
            return
        options=[(p["date"],p["label"]) for p in report["points"]]
        self.selected_day.blockSignals(True)
        self.selected_day.clear()
        for key,label in reversed(options):
            self.selected_day.addItem(key,key)
        selected=current if current in {p[0] for p in options} else report["end"]
        self.selected_day.setCurrentIndex(
            next((idx for idx in range(self.selected_day.count())
                  if self.selected_day.itemData(idx)==selected),0))
        self.selected_day.blockSignals(False)
        if selected!=report["selected_day"]:
            report=daily_dashboard(self.db,events,days=days,selected_day=selected)
            self.latest=report
        today=report["today"]
        open_work=report["open_work"]
        self.cards[0].update_values(fmt(today["orders"])+" sipariş","Bugün tamamlanan sipariş")
        if report["today_activity_known"]:
            ready=fmt(today["ready"])+" nüsha"
            boxed=fmt(today["boxed"])+" nüsha"
        else:
            ready=boxed="Kayıt yok"
        self.cards[1].update_values(ready,"Bugün hazır işaretlenen (net)")
        self.cards[2].update_values(boxed,"Bugün kolilenen (net)")
        self.cards[3].update_values(fmt(report["open_orders"])+" sipariş",
                                    fmt(report["active_orders"])+" aktif · "+
                                    fmt(report["open_orders"]-report["active_orders"])+" havuz")
        self.cards[4].update_values(fmt(report["today_rate"],2)+" sipariş/sa",
                                     "Vardiya saati başına tamamlanan")
        change=report["tempo_change"]
        label=("Veri yok" if change is None else
               ("+" if change>=0 else "")+fmt(change,1)+"%")
        self.cards[5].update_values(label,"Önceki üretim günlerinin saatlik ortalamasına göre")
        self.data_note.setText(
            "Son "+fmt(report["days"])+" gün: "+
            fmt(sum(p["orders"] for p in report["points"]))+
            " tamamlanan sipariş. Önceki üretim günlerinde ortalama "+
            fmt(report["average_orders"],1)+" sipariş/gün."
            + (" Hazırlama/kolileme saat kayıtları bazı günler için eksiktir."
               if not report["has_progress_history"] else "")
        )
        self.completed_chart.set_data(report["points"])
        logged=set(report["logged_days"])
        plotted=[{**p,"ready":p["ready"] if p["date"] in logged else 0,
                  "boxed":p["boxed"] if p["date"] in logged else 0}
                 for p in report["points"]]
        self.progress_chart.set_data(plotted if logged else [])
        self.backlog.refresh(open_work)
        self.shift_note.setText(
            "BUGÜNÜN İŞ PLANI: "+report["workload"]+
            "  ·  Açık işte "+fmt(open_work["print_waiting"])+
            " nüsha baskı/hazırlık bekliyor, "+
            fmt(open_work["pack_ready"])+" nüsha kolilemeye hazır."
        )
        hourly=report["hourly"]
        self.hourly_chart.set_data([
            {"label":f'{h["hour"]:02d}:00',"date":report["selected_day"],
             "started":h["started"],"orders":h["orders"]} for h in hourly[7:18]
        ])
        daily_registered=report["selected_day"] in logged
        shown_hours=[
            h for h in hourly if 7<=h["hour"]<=17 or
            h["started"] or h["orders"] or h["ready"] or h["boxed"]
        ]
        self._rows(self.hourly_table,[
            [f'{h["hour"]:02d}:00',h["started"],h["orders"],
             fmt(h["ready"]) if daily_registered else "—",
             fmt(h["boxed"]) if daily_registered else "—"]
            for h in shown_hours
        ])
        self._rows(self.daily_table,[
            [p["date"],fmt(p["orders"]),fmt(p["books"]),fmt(p["pages"]),
             fmt(p["ready"]) if p["date"] in logged else "—",
             fmt(p["boxed"]) if p["date"] in logged else "—"]
            for p in reversed(report["points"])
        ])

    def export(self,kind):
        if self.latest is None:
            self.refresh()
            if self.latest is None:return
        extension="csv" if kind=="csv" else "html"
        file,_=QFileDialog.getSaveFileName(
            self,"FlexFlow üretim raporu",
            "ALFA_FlexFlow_"+self.latest["start"]+"_"+self.latest["end"]+"."+extension,
            "CSV (*.csv)" if kind=="csv" else "HTML (*.html)")
        if not file:return
        try:
            target=Path(file)
            if target.suffix.lower()!="."+extension:
                target=target.with_suffix("."+extension)
            text=csv_report(self.latest) if kind=="csv" else html_report(self.latest)
            target.write_text(text,encoding="utf-8-sig" if kind=="csv" else "utf-8")
            if kind=="html":
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.resolve())))
        except (OSError,ValueError) as exc:
            QMessageBox.warning(self,"Rapor kaydedilemedi",str(exc))
