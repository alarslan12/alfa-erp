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
    QLabel, QMessageBox, QPushButton, QScrollArea, QProgressBar,
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QAbstractItemView,
)
from flexflow_operasyon import daily_dashboard, activity_dates, operation_insight
from flexflow_rapor import csv_report, html_report
from takvim import TarihPopup
from temali_combo import AlfaTemaliCombo
from widgets import button


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
            "Açık siparişlerin kolileme ilerlemesi: %"+
            fmt(100*values[2]/total,1) if total else
            "Şu anda açık sipariş bulunmuyor."
        )


class FlexFlowView(QWidget):
    def __init__(self,db,parent=None):
        super().__init__(parent)
        self.db=db
        self.latest=None
        self._calendar_from=None
        self._calendar_to=None
        self._activity_days=[]
        self.popup=None
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
        self.filter_segment=QFrame()
        self.filter_segment.setObjectName("OrderFilterSegment")
        filter_row=QHBoxLayout(self.filter_segment)
        filter_row.setContentsMargins(4,3,4,3)
        filter_row.setSpacing(4)
        self.period=AlfaTemaliCombo()
        self.period.setObjectName("OrderFilter")
        self.period.setMaxVisibleItems(12)
        self.period.setFixedSize(158,36)
        self.period.setToolTip("Yalnızca kaydedilmiş üretim hareketi bulunan günler")
        self.period.addItem("Tüm hareketli günler",None)
        self.period.currentIndexChanged.connect(self._period_changed)
        filter_row.addWidget(self.period)
        self.calendar_btn=button("▦  Takvim","CalendarTrigger")
        self.calendar_btn.setFixedSize(94,36)
        self.calendar_btn.setToolTip("Bir gün seç; Shift+tık ile tarih aralığı belirle")
        self.calendar_btn.clicked.connect(self.open_calendar)
        filter_row.addWidget(self.calendar_btn)
        self.clear_btn=button("Temizle","OrderReset")
        self.clear_btn.setFixedSize(71,36)
        self.clear_btn.clicked.connect(self.clear_date_filter)
        filter_row.addWidget(self.clear_btn)
        toolbar.addWidget(self.filter_segment)
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

        # Daily operations interpretation is the first substantial panel,
        # ahead of KPI cards/charts, and is refreshed from recorded data.
        self.insight_panel=QFrame()
        self.insight_panel.setObjectName("FlexFlowInsight")
        insight_layout=QVBoxLayout(self.insight_panel)
        insight_layout.setContentsMargins(16,13,16,14)
        insight_layout.setSpacing(8)
        self.insight_title=QLabel("GÜNLÜK OPERASYON DEĞERLENDİRMESİ")
        self.insight_title.setObjectName("FlexFlowInsightTitle")
        insight_layout.addWidget(self.insight_title)
        self.insight_observation=QLabel()
        self.insight_progress=QLabel()
        self.insight_comparison=QLabel()
        self.insight_live=QLabel()
        self.insight_assessment=QLabel()
        self.insight_note=QLabel()
        for label in (self.insight_observation,self.insight_progress,
                      self.insight_comparison,self.insight_live,
                      self.insight_assessment,self.insight_note):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            insight_layout.addWidget(label)
        self.insight_assessment.setObjectName("FlexFlowInsightRisk")
        self.insight_note.setObjectName("FlexFlowInsightNote")
        root.addWidget(self.insight_panel)

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
            ("Seçili gün tamamlanan","#51d6a6"),
            ("Seçili gün hazırlanan","#6cbcff"),
            ("Seçili gün kolilenen","#f1c275"),
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
        self.completed_chart=LineChart("Günlük tamamlanan sipariş",[
            ("orders","Sipariş","#51d6a6")])
        self.pages_chart=LineChart("Tamamlanan işlerin sayfa hacmi",[
            ("pages","Sayfa","#b597ff")])
        self.progress_chart=LineChart("Kayıtlı günlerde hazırlanan / kolilenen",[
            ("ready","Hazırlandı","#60baff"),("boxed","Kolilendi","#f1c275")
        ])
        self.backlog=BacklogPanel()
        for chart in (self.completed_chart,self.pages_chart,self.progress_chart):
            chart.setFixedHeight(235)
        charts.addWidget(self.completed_chart,0,0)
        charts.addWidget(self.pages_chart,0,1)
        charts.addWidget(self.progress_chart,1,0)
        charts.addWidget(self.backlog,1,1)
        charts.setColumnStretch(0,1)
        charts.setColumnStretch(1,1)
        root.addLayout(charts)
        self.shift_note=QLabel()
        self.shift_note.setWordWrap(True)
        self.shift_note.setStyleSheet("font-size:12px;font-weight:800;padding:8px;")
        root.addWidget(self.shift_note)

        hourly_head=QHBoxLayout()
        hourly_title=QLabel("SAAT SAAT ÜRETİM HAREKETLERİ")
        hourly_title.setStyleSheet("font-weight:900;font-size:13px")
        hourly_head.addWidget(hourly_title)
        hourly_head.addStretch()
        self.hourly_date_note=QLabel("Saatlik veriler: seçili gün")
        self.hourly_date_note.setObjectName("FlexFlowHourlyDate")
        hourly_head.addWidget(self.hourly_date_note)
        root.addLayout(hourly_head)

        self.hourly_chart=LineChart("Seçilen gün · saatlik sipariş akışı",[
            ("started","Aktife alındı","#6cbcff"),
            ("orders","Tamamlandı","#51d6a6")
        ])
        self.hourly_progress=LineChart("Seçilen gün · saatlik kitap hareketleri",[
            ("ready","Hazırlandı","#60baff"),
            ("boxed","Kolilendi","#f1c275")
        ])
        hours_grid=QGridLayout()
        hours_grid.setSpacing(10)
        for col,chart in enumerate((self.hourly_chart,self.hourly_progress)):
            chart.setFixedHeight(230)
            hours_grid.addWidget(chart,0,col)
            hours_grid.setColumnStretch(col,1)
        root.addLayout(hours_grid)

        self.hourly_table=self._table(
            ["Saat","Aktife alınan","Tamamlanan",
             "Hazırlanan nüsha / sip.","Kolilenen nüsha / sip."],
            345,
        )
        root.addWidget(self.hourly_table)
        daily_title=QLabel("GÜNLÜK ÜRETİM RAPORU")
        daily_title.setStyleSheet("font-weight:900;font-size:13px")
        root.addWidget(daily_title)
        self.daily_table=self._table(
            ["Tarih","Aktife alınan","Tamamlanan","Kitap","Sayfa",
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
        self._calendar_from=self._calendar_to=None
        self.calendar_btn.setText("▦  Takvim")
        self.refresh()

    def open_calendar(self):
        dates=self._activity_days or activity_dates(
            self.db,getattr(self.db,"production_events",[]))
        self.popup=TarihPopup(dates,self,
            heading="FlexFlow · üretim tarihini seç",
            activity_label="Üretim hareketi kayıtlı gün")
        self.popup.selected.connect(self.set_range)
        self.popup.open()

    def set_range(self,start,end):
        self._calendar_from=start
        self._calendar_to=(end or start) if start else None
        self.period.blockSignals(True)
        self.period.setCurrentIndex(0)
        self.period.blockSignals(False)
        if start:
            if end:
                self.calendar_btn.setText(
                    f"▦ {start[8:10]}.{start[5:7]} – {end[8:10]}.{end[5:7]}")
            else:
                self.calendar_btn.setText(f"▦ {start[8:10]}.{start[5:7]}")
            self.calendar_btn.setToolTip(
                "Seçili üretim dönemi: "+start+
                (" – "+end if end else "")+" · Değiştirmek için tıkla")
        else:
            self.calendar_btn.setText("▦  Takvim")
        self.refresh()

    def clear_date_filter(self):
        self._calendar_from=self._calendar_to=None
        self.period.blockSignals(True)
        self.period.setCurrentIndex(0)
        self.period.blockSignals(False)
        self.calendar_btn.setText("▦  Takvim")
        self.refresh()

    def refresh(self,*_):
        try:
            events=getattr(self.db,"production_events",[])
            self._activity_days=activity_dates(self.db,events)
            # Keep the date selection while cloud events change; rebuild just
            # the dropdown entries (not the whole view or the cloud snapshot).
            chosen=self.period.currentData()
            self.period.blockSignals(True)
            self.period.clear()
            self.period.addItem("Tüm hareketli günler",None)
            for iso in self._activity_days:
                self.period.addItem(
                    date.fromisoformat(iso).strftime("%d.%m.%Y"),iso)
            idx=self.period.findData(chosen)
            self.period.setCurrentIndex(idx if idx>=0 else 0)
            self.period.blockSignals(False)
            selected=self.period.currentData()
            if self._calendar_from:
                report=daily_dashboard(
                    self.db,events,start_date=self._calendar_from,
                    end_date=self._calendar_to,selected_day=self._calendar_to)
            elif selected:
                report=daily_dashboard(
                    self.db,events,start_date=selected,end_date=selected,
                    selected_day=selected)
            else:
                # No last-7/14/30-day menu: global view shows the last 90
                # calendar days, with the dropdown listing actual activity days.
                report=daily_dashboard(self.db,events,days=90)
            self.latest=report
            insight=operation_insight(report)
        except Exception as exc:
            QMessageBox.warning(self,"FlexFlow",
                "Üretim panosu yenilenemedi: "+str(exc)[:240])
            return
        self.insight_title.setText(insight["title"])
        self.insight_observation.setText(insight["observation"])
        self.insight_progress.setText(insight["progress"])
        self.insight_comparison.setText(insight["comparison"])
        self.insight_live.setText(insight["live"])
        self.insight_assessment.setText(insight["assessment"])
        self.insight_note.setText(insight["note"])
        self.insight_panel.setProperty("insightLevel",insight["severity"])
        self.insight_panel.style().unpolish(self.insight_panel)
        self.insight_panel.style().polish(self.insight_panel)
        self.hourly_date_note.setText(
            "Saatlik veriler · "+date.fromisoformat(
                report["selected_day"]).strftime("%d.%m.%Y"))
        ranged=(report["start"]!=report["end"]
                and not report.get("overview_mode",False))
        counts=report["period"] if ranged else report["selected"]
        title="Seçili dönem" if ranged else "Seçili gün"
        self.cards[0].title.setText(title+" tamamlanan")
        self.cards[1].title.setText(title+" hazırlanan")
        self.cards[2].title.setText(title+" kolilenen")
        self.cards[4].title.setText("Son günün saatlik temposu" if ranged
                                    else "Seçili günün temposu")
        self.cards[5].title.setText("Son günün ortalama kıyası" if ranged
                                    else "Ortalama karşılaştırması")
        open_work=report["open_work"]
        self.cards[0].update_values(fmt(counts["orders"])+" sipariş",
                                    title+" tamamlanan sipariş")
        known_dates=set(report["logged_days"])
        has_log=any(p["date"] in known_dates for p in report["points"]) if ranged else (
            report["selected_activity_known"])
        ready=fmt(counts["ready"])+" nüsha" if has_log else "Kayıt yok"
        boxed=fmt(counts["boxed"])+" nüsha" if has_log else "Kayıt yok"
        if ranged:
            progress_note="Seçili dönemde kayıtlı hareketler"
            self.cards[1].update_values(ready,progress_note)
            self.cards[2].update_values(boxed,progress_note)
        else:
            self.cards[1].update_values(
                ready,title+" "+fmt(counts["ready_orders"])+
                " siparişte hazırlama hareketi" if has_log else
                "İşlem günlüğünde hazırlama hareketi yok")
            self.cards[2].update_values(
                boxed,title+" "+fmt(counts["boxed_orders"])+
                " siparişte kolileme hareketi" if has_log else
                "İşlem günlüğünde kolileme hareketi yok")
        self.cards[3].update_values(fmt(report["open_orders"])+" sipariş",
                                    fmt(report["active_orders"])+" aktif · "+
                                    fmt(report["open_orders"]-report["active_orders"])+" havuz")
        self.cards[4].update_values(fmt(report["selected_rate"],2)+" sipariş/sa",
                                     "Planlı vardiya saati başına tamamlanan")
        change=report["tempo_change"]
        label=("Veri yok" if change is None else
               ("+" if change>=0 else "")+fmt(change,1)+"%")
        self.cards[5].update_values(label,"Önceki üretim günlerinin saatlik ortalamasına göre")
        self.data_note.setText(
            ("Seçili dönem: " if ranged else "Görüntülenen dönem: ")+
            report["start"]+" → "+report["end"]+" · "+
            fmt(report["period"]["orders"])+
            " tamamlanan sipariş. Önceki kayıtlı üretim günlerinde ortalama "+
            fmt(report["average_orders"],1)+" sipariş/gün."
            + (" Hazırlama/kolileme işlemi zaman damgası bulunmayan günler için 'Kayıt yok' gösterilir."
               if not report["has_progress_history"] else "")
        )
        # Only dates with actual production movement enter the trend; never
        # manufacture activity points from empty days.
        activity=set(self._activity_days)
        plotted_days=[p for p in report["points"] if p["date"] in activity]
        self.completed_chart.set_data(plotted_days)
        self.pages_chart.set_data(plotted_days)
        logged=set(report["logged_days"])
        # Missing event history is not a measured zero. Plot only dates
        # with recorded movement; the daily table shows an explicit dash.
        plotted=[p for p in report["points"] if p["date"] in logged]
        self.progress_chart.set_data(plotted)
        self.backlog.refresh(open_work)
        self.shift_note.setText(
            "ŞU ANKİ AÇIK İŞ PLANI: "+report["workload"]+
            "  ·  Açık işte "+fmt(open_work["print_waiting"])+
            " nüsha baskı/hazırlık bekliyor, "+
            fmt(open_work["pack_ready"])+" nüsha kolilemeye hazır."
        )
        hourly=report["hourly"]
        hour_points=[
            {"label":f'{h["hour"]:02d}:00',"date":report["selected_day"],
             "started":h["started"],"orders":h["orders"],
             "ready":h["ready"],"boxed":h["boxed"]} for h in hourly[7:18]
        ]
        self.hourly_chart.set_data(hour_points)
        daily_registered=report["selected_day"] in logged
        self.hourly_progress.set_data(hour_points if daily_registered else [])
        shown_hours=[
            h for h in hourly if 7<=h["hour"]<=17 or
            h["started"] or h["orders"] or h["ready"] or h["boxed"]
        ]
        self._rows(self.hourly_table,[
            [f'{h["hour"]:02d}:00',h["started"],h["orders"],
             (fmt(h["ready"])+" / "+fmt(h["ready_orders"])) if daily_registered else "—",
             (fmt(h["boxed"])+" / "+fmt(h["boxed_orders"])) if daily_registered else "—"]
            for h in shown_hours
        ])
        shown_daily=(report["points"] if self._calendar_from or self.period.currentData()
                     else [p for p in report["points"] if p["date"] in activity])
        self._rows(self.daily_table,[
            [p["date"],fmt(p["started"]),fmt(p["orders"]),fmt(p["books"]),
             fmt(p["pages"]),fmt(p["ready"]) if p["date"] in logged else "—",
             fmt(p["boxed"]) if p["date"] in logged else "—"]
            for p in reversed(shown_daily)
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
