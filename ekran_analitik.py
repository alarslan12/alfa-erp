"""ALFA ERP V4.29 · Konuya göre sınıflandırılmış performans ve takvim muhasebesi."""
import calendar
from datetime import date, timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QPointF, QDate, QTimer, QEvent, QStandardPaths
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSizePolicy, QApplication, QCheckBox, QTabWidget
)
from PySide6.QtCore import QUrl
from widgets import button, text, scrollable
from muhasebe_veri import PaymentDays, accounting_days, completed_summary, html_report, completion_fingerprints, accounting_revenue, after_shipping_revenue
from takvim import MONTHS, WEEK
from ayar_yonetimi import accessible_ui_color
from analitik_pasta import PlatformRevenueDonut

NAVY='#10243a'
FG='#f5f9ff'
MUTED='#c0d4e8'
BLUE='#409fff'
MINT='#35dda9'
AMBER='#ffc05a'
PURPLE='#b693ff'
CREAM_BG='#fbf7ef'
CREAM_PANEL='#f3ebdf'
CREAM_BORDER='#d6c7b0'
CREAM_TEXT='#2f455c'
CREAM_MUTED='#6f7f90'


def money(n):
    return f'{n:,.2f} ₺'.replace(',', ' ')


def integer(n):
    return f'{int(n):,}'.replace(',', '.')


class LineChart(QWidget):
    """Lightweight interactive time-series chart: hover value, peak, clear axes."""
    def __init__(self, title, series):
        super().__init__()
        self.title=title
        self.series=series
        self.data=[]
        self.hovered=None
        self._chart_bounds=None
        self.setObjectName('AnalyticsChart')
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        self.setMouseTracking(True)

    def set_data(self,data):
        self.data=list(data)
        self.hovered=None
        self.update()

    def _colors(self):
        theme=str(QApplication.instance().property('alfa_theme') or 'koyu')
        if theme=='acik':
            return {'panel':CREAM_PANEL,'border':CREAM_BORDER,'text':CREAM_TEXT,
                    'muted':CREAM_MUTED,'grid':'#d7c8b7'}
        return {'panel':NAVY,'border':'#3b516c','text':FG,
                'muted':MUTED,'grid':'#34475e'}

    @staticmethod
    def _formatted(value):
        value=float(value)
        if abs(value)>=10:
            return f'{value:,.0f}'.replace(',', '.')
        return f'{value:,.1f}'.replace('.', ',')

    def _location(self,idx,value):
        if self._chart_bounds is None:return 0.0,0.0
        l,t,r,b,ymin,ymax=self._chart_bounds
        x=(l+r)/2 if len(self.data)==1 else l+(r-l)*idx/max(1,len(self.data)-1)
        y=b-(b-t)*(float(value)-ymin)/(ymax-ymin)
        return x,y

    def mouseMoveEvent(self,event):
        if self._chart_bounds is None or not self.data:
            return super().mouseMoveEvent(event)
        l,t,r,b,_,_=self._chart_bounds
        x,y=event.position().x(),event.position().y()
        hovered=None
        if l-11<=x<=r+11 and t-14<=y<=b+14:
            n=len(self.data)
            idx=0 if n==1 else min(n-1,max(0,round((x-l)*max(1,n-1)/max(1,r-l))))
            choices=[]
            for key,label,_ in self.series:
                point=self._location(idx,self.data[idx].get(key,0))
                d=((point[0]-x)**2+(point[1]-y)**2)**0.5
                choices.append((d,idx,key,label,float(self.data[idx].get(key,0))))
            if choices:
                best=min(choices)
                if best[0]<=25:
                    hovered=(best[1],best[2],best[3],best[4])
        if hovered!=self.hovered:
            self.hovered=hovered
            if hovered:
                from PySide6.QtWidgets import QToolTip
                idx,key,label,value=hovered
                date_label=self.data[idx].get('date') or self.data[idx].get('label','')
                QToolTip.showText(event.globalPosition().toPoint(),
                                  str(date_label)+' · '+label+': '+f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.'),self)
            else:
                from PySide6.QtWidgets import QToolTip
                QToolTip.hideText()
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self,event):
        if self.hovered is not None:
            self.hovered=None
            from PySide6.QtWidgets import QToolTip
            QToolTip.hideText()
            self.update()
        super().leaveEvent(event)

    def paintEvent(self,event):
        colors=self._colors()
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(colors['panel']))
        p.setPen(QPen(QColor(colors['border']),1))
        p.drawRoundedRect(self.rect().adjusted(1,1,-2,-2),12,12)
        p.setPen(QColor(colors['text']))
        p.setFont(QFont('Segoe UI',10,QFont.Weight.Bold))
        p.drawText(14,23,self.title)
        legend_right=self.width()-17
        p.setFont(QFont('Segoe UI',8))
        for key,label,col in reversed(self.series):
            block=max(57,len(label)*6+20)
            legend_right-=block
            p.setBrush(QColor(accessible_ui_color(col)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(legend_right),16,7,7)
            p.setPen(QColor(colors['muted']))
            p.drawText(int(legend_right+12),23,label)
        # A readable scale stays visible on the left. Precise point values
        # appear only in the hover tooltip, never as permanent overlays.
        left,top,right,bottom=77.0,46.0,float(self.width()-19),float(self.height()-35)
        if right-left<65 or bottom-top<40:
            self._chart_bounds=None
            p.end()
            return
        values=[float(row.get(key,0) or 0) for row in self.data for key,_,_ in self.series]
        ymin=min(0,min(values,default=0))
        ymax=max(1,max(values,default=0))
        if ymin>=0:ymax*=1.10
        else:
            extent=max(1.0,ymax-ymin)
            ymin-=extent*.05
            ymax+=extent*.08
        self._chart_bounds=(left,top,right,bottom,ymin,ymax)
        p.setFont(QFont('Segoe UI',8))
        for j in range(5):
            y=top+(bottom-top)*j/4
            p.setPen(QPen(QColor(colors['grid']),1))
            p.drawLine(int(left),int(y),int(right),int(y))
            value=ymax-(ymax-ymin)*j/4
            p.setPen(QColor(colors['muted']))
            p.drawText(5,int(y)-8,int(left-14),17,
                       Qt.AlignmentFlag.AlignRight,self._formatted(value))
        n=len(self.data)
        if n:
            for idx in dict.fromkeys([0,n//4,n//2,3*n//4,n-1]):
                x,_=self._location(idx,0)
                label=str(self.data[idx].get('label',''))
                p.setPen(QColor(colors['muted']))
                p.drawText(int(x-23),int(bottom+8),46,17,Qt.AlignmentFlag.AlignHCenter,label)
        else:
            p.setPen(QColor(colors['muted']))
            p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'Henüz veri yok')
        for key,label,color in self.series:
            col=QColor(accessible_ui_color(color))
            pen=QPen(col)
            pen.setWidthF(2.4)
            p.setPen(pen)
            # QPainter.drawPath fills even open paths with the active brush,
            # closing them implicitly: this caused the solid triangular
            # polygons seen in the user's screenshot.
            p.setBrush(Qt.BrushStyle.NoBrush)
            path=QPainterPath()
            for i,row in enumerate(self.data):
                x,y=self._location(i,row.get(key,0))
                if i==0:path.moveTo(x,y)
                else:path.lineTo(x,y)
            if self.data:
                p.drawPath(path)
                # Small circular markers make the interactive positions
                # discoverable without cluttering long date ranges.
                if len(self.data)<=40:
                    p.setPen(QPen(col,2.0))
                    p.setBrush(QColor(colors['panel']))
                    for row_idx, row in enumerate(self.data):
                        x,y=self._location(row_idx,row.get(key,0))
                        p.drawEllipse(QPointF(x,y),3.2,3.2)
        if self.hovered:
            idx,key,label,value=self.hovered
            hx,hy=self._location(idx,value)
            p.setPen(QPen(QColor(colors['muted']),1,Qt.PenStyle.DashLine))
            p.drawLine(int(hx),int(top),int(hx),int(bottom))
            tint=next((color for colkey,_,color in self.series if colkey==key),BLUE)
            color=QColor(accessible_ui_color(tint))
            p.setPen(Qt.PenStyle.NoPen)
            glow=QColor(color);glow.setAlpha(75)
            p.setBrush(glow)
            p.drawEllipse(QPointF(hx,hy),12,12)
            p.setBrush(color)
            p.drawEllipse(QPointF(hx,hy),6,6)
        p.end()


class StatPill(QFrame):
    """Real-height KPI widget; never compress into a thin horizontal line."""
    def __init__(self, title, value, accent):
        super().__init__()
        self.setObjectName('AccountingPill')
        # QScrollArea can give QFrame layouts a zero-height size hint on initial
        # display in some Qt/Windows scaling combinations. Guarantee both lines.
        self.setFixedHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(11,7,11,7)
        layout.setSpacing(2)
        lbl=QLabel(title)
        lbl.setObjectName('AccountingPillTitle')
        lbl.setFixedHeight(16)
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl)
        val=QLabel(str(value))
        val.setObjectName('AccountingPillValue')
        val.setFixedHeight(27)
        val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        val.setStyleSheet(f'color:{accessible_ui_color(accent)};')
        val.setToolTip(f'{title}: {value}')
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(val)


class RevenuePill(QFrame):
    """Prominent, accessible revenue/receivables metric with context."""
    def __init__(self, title, value, accent, meaning):
        super().__init__()
        self.setObjectName("AnalyticsRevenuePill")
        self.setFixedHeight(108)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(14,12,12,9)
        layout.setSpacing(4)
        heading=QLabel(title)
        heading.setObjectName("AnalyticsRevenuePillTitle")
        layout.addWidget(heading)
        total=QLabel(str(value))
        total.setObjectName("AnalyticsRevenuePillAmount")
        total.setStyleSheet(f"color:{accessible_ui_color(accent)};")
        total.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        total.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(total,1)
        note=QLabel(meaning)
        note.setObjectName("AnalyticsRevenuePillHint")
        note.setWordWrap(True)
        note.setToolTip(meaning)
        layout.addWidget(note)


class AnalitikView(QWidget):
    """Selected completion day/range -> completed orders only, with payment tracking."""
    def __init__(self, db, on_open_order=None, owner_edition=False):
        super().__init__()
        self.setObjectName('AnalyticsPage')
        self.db=db
        self.owner_edition=bool(owner_edition)
        self.cloud_admin_request=None  # Yönetici oturumu açılırsa atanır.
        self.on_open_order=on_open_order
        self.payments=PaymentDays(Path(db.sepet_dosyasi).parent)
        self.completed_days={}
        self.active_days={}
        self._paid_days=set()
        self._fingerprints={}
        self.start=None
        self.end=None
        self.anchor=None
        self.latest=None
        self.day_buttons=[]
        root=QVBoxLayout(self)
        root.setContentsMargins(2,3,2,5)
        root.setSpacing(9)
        self.sections=None
        self.flexflow=None
        self._normal_dirty=True
        if self.owner_edition:
            from ekran_verimlilik import FlexFlowView
            self.sections=QTabWidget(self)
            self.sections.setObjectName("AnalyticsSectionTabs")
            normal_page=QWidget()
            normal_layout=QVBoxLayout(normal_page)
            normal_layout.setContentsMargins(1,3,1,3)
            normal_layout.setSpacing(9)
            self.sections.addTab(normal_page,"Normal Analitik")
            self.flexflow=FlexFlowView(self.db,self)
            self.sections.addTab(self.flexflow,"FlexFlow")
            root.addWidget(self.sections,1)
            self.sections.currentChanged.connect(self._section_changed)
            work_layout=normal_layout
        else:
            work_layout=root
        header=QHBoxLayout()
        heading=text('◈  Muhasebe & Analitik', 'AnalyticsTitle')
        header.addWidget(heading)
        header.addStretch()
        self.range_text=text('','AccountingPeriod')
        header.addWidget(self.range_text)
        export=button('↗ HTML Raporu / Yazdır', 'AnalyticsExport')
        export.setToolTip('HTML raporunu Masaüstüne kaydet ve yazdırma ekranını aç')
        export.clicked.connect(self.export_html)
        header.addWidget(export)
        reload=button('↻','SmallAction')
        reload.setToolTip('Siparişleri ve takvimi yenile')
        reload.clicked.connect(self.refresh)
        header.addWidget(reload)
        work_layout.addLayout(header)

        body=QHBoxLayout()
        body.setSpacing(12)
        self.calendar_panel=QFrame()
        self.calendar_panel.setObjectName('AccountingCalendarPanel')
        self.calendar_panel.setFixedWidth(352)
        calendar_layout=QVBoxLayout(self.calendar_panel)
        calendar_layout.setContentsMargins(13,13,13,12)
        calendar_layout.setSpacing(10)
        monthline=QHBoxLayout()
        left=button('‹', 'AccountingMonthArrow')
        right=button('›', 'AccountingMonthArrow')
        left.setFixedSize(36,34)
        right.setFixedSize(36,34)
        left.clicked.connect(lambda:self.change_month(-1))
        right.clicked.connect(lambda:self.change_month(1))
        self.month_title=QLabel()
        self.month_title.setObjectName('AccountingMonthTitle')
        self.month_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        monthline.addWidget(left)
        monthline.addWidget(self.month_title,1)
        monthline.addWidget(right)
        calendar_layout.addLayout(monthline)
        grid=QGridLayout();grid.setSpacing(4)
        for col,label in enumerate(WEEK):
            lbl=QLabel(label)
            lbl.setObjectName('AccountingWeekday')
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl,0,col)
        for row in range(1,7):
            for col in range(7):
                day_btn=QPushButton()
                day_btn.setObjectName('AccountingDay')
                day_btn.setFixedHeight(39)
                day_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                day_btn.clicked.connect(lambda checked=False, b=day_btn:self.choose_date(b.property('dateKey')))
                grid.addWidget(day_btn,row,col)
                self.day_buttons.append(day_btn)
        calendar_layout.addLayout(grid)
        guidance=text('Gün seç · Shift+tık veya “Aralık seç” ile dönem belirle','AccountingHelp',wrap=True)
        calendar_layout.addWidget(guidance)
        self.range_mode=QCheckBox('Aralık seç')
        self.range_mode.setToolTip('İlk gün ve son gün için iki kez tıkla')
        self.range_mode.toggled.connect(self._toggle_range)
        calendar_layout.addWidget(self.range_mode)
        quick=QHBoxLayout();quick.setSpacing(6)
        quick.addStretch()
        quick_btn=button('◫  Bu ayı seç','AccountingQuick')
        quick_btn.setToolTip('Takvimde görüntülenen ayın tamamını seç')
        quick_btn.clicked.connect(lambda checked=False:self.quick_period('month'))
        quick.addWidget(quick_btn)
        calendar_layout.addLayout(quick)
        legend=QGridLayout();legend.setHorizontalSpacing(8);legend.setVerticalSpacing(6)
        for index,(marker,role) in enumerate((('● Tamamlanan','done'),('● Ödendi','paid'),('● Yalnız aktif','active'))):
            lbl=QLabel(marker)
            lbl.setObjectName('AccountingLegend')
            lbl.setProperty('legendRole',role)
            legend.addWidget(lbl,index//2,index%2)
        calendar_layout.addLayout(legend)
        self.selection_label=QLabel()
        self.selection_label.setObjectName('AccountingSelection')
        self.selection_label.setWordWrap(True)
        calendar_layout.addWidget(self.selection_label)
        self.paid_btn=button('✓  ÖDENDİ', 'AccountingPaidAction')
        self.unpaid_btn=button('↶  ÖDENMEDİ', 'AccountingUnpaidAction')
        self.paid_btn.clicked.connect(lambda:self.set_payment(True))
        self.unpaid_btn.clicked.connect(lambda:self.set_payment(False))
        payment_row=QHBoxLayout();payment_row.setSpacing(7)
        payment_row.addWidget(self.paid_btn,1)
        payment_row.addWidget(self.unpaid_btn,1)
        calendar_layout.addLayout(payment_row)
        self.payment_note=QLabel('Ödeme işareti seçili tamamlanma günlerine uygulanır.')
        self.payment_note.setObjectName('AccountingHelp')
        self.payment_note.setWordWrap(True)
        calendar_layout.addWidget(self.payment_note)
        calendar_layout.addStretch()
        body.addWidget(self.calendar_panel,0,Qt.AlignmentFlag.AlignTop)

        self.result_content=QWidget()
        self.result_layout=QVBoxLayout(self.result_content)
        self.result_layout.setContentsMargins(0,0,5,10)
        self.result_layout.setSpacing(10)
        self.result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.result_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.results_scroll=scrollable(self.result_content)
        self.results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results_scroll.viewport().installEventFilter(self)
        self._last_metric_columns=None
        self._reflow_timer=QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.setInterval(90)
        self._reflow_timer.timeout.connect(self._adapt_width)
        body.addWidget(self.results_scroll,1)
        work_layout.addLayout(body,1)
        # Render lazily on tab navigation to avoid startup/UI freezes.
        self._normal_refresh_timer=QTimer(self)
        self._normal_refresh_timer.setSingleShot(True)
        self._normal_refresh_timer.setInterval(125)
        self._normal_refresh_timer.timeout.connect(self._refresh_normal_now)
        self._report_timer=QTimer(self)
        self._report_timer.setSingleShot(True)
        self._report_timer.setInterval(90)
        self._report_timer.timeout.connect(self._render_report)
        self._flex_timer=QTimer(self)
        self._flex_timer.setSingleShot(True)
        self._flex_timer.setInterval(160)
        self._flex_timer.timeout.connect(self._refresh_flex_now)

    def _section_changed(self,index):
        if index==1 and self.flexflow is not None:
            self._normal_refresh_timer.stop()
            self._report_timer.stop()
            self._flex_timer.start()
        else:
            self._flex_timer.stop()
            self.refresh()

    def _refresh_flex_now(self):
        if self.flexflow is not None and self.sections is not None and self.sections.currentIndex()==1:
            self.flexflow.refresh()

    def eventFilter(self, watched, event):
        # Qt can deliver a final event while the scroll area is being
        # destroyed. Never dereference a deleted C++ widget at shutdown.
        try:
            viewport=self.results_scroll.viewport()
            if watched is viewport and event.type()==QEvent.Type.Resize:
                if hasattr(self,'_reflow_timer'):
                    self._reflow_timer.start()
        except RuntimeError:
            return False
        return super().eventFilter(watched,event)

    def _metric_columns(self):
        width=self.results_scroll.viewport().width()
        return 2 if width<600 else 3 if width<880 else 4 if width<1170 else 5

    def _revenue_columns(self):
        width=self.results_scroll.viewport().width()
        return 1 if width<520 else 2 if width<970 else 4

    def _adapt_width(self):
        # A viewport resize can arrive during navigation/teardown while
        # pending Qt layout deletions are still being processed.
        if not self.isVisible() or getattr(self,'_report_building',False):
            return
        # Do not reconstruct 6 charts/large tables on layout resize.
        # Qt grids stretch until the next data-driven refresh.
        return

    def _toggle_range(self,enabled):
        if enabled:
            self.anchor=None
            self.payment_note.setText('Önce ilk güne, ardından son güne tıklayın.')

    def quick_period(self, period):
        if period == 'month':
            self.start=date(self.year,self.month,1)
            self.end=date(self.year,self.month,calendar.monthrange(self.year,self.month)[1])
        else:
            finish=self.anchor or self.start or date.today()
            self.start=finish-timedelta(days=int(period)-1)
            self.end=finish
        self.anchor=self.end
        self.range_mode.blockSignals(True)
        self.range_mode.setChecked(False)
        self.range_mode.blockSignals(False)
        self.year,self.month=self.end.year,self.end.month
        self.paint_calendar()
        self.show_report()
        self.results_scroll.verticalScrollBar().setValue(0)

    def change_month(self,offset):
        m=self.year*12+self.month-1+offset
        self.year,zero=divmod(m,12)
        self.month=zero+1
        self.paint_calendar()

    def choose_date(self,key):
        if not key:return
        selected=date.fromisoformat(str(key))
        shift=bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)
        if (shift or self.range_mode.isChecked()) and self.anchor is not None:
            self.start,self.end=sorted((self.anchor,selected))
            self.range_mode.setChecked(False)
        else:
            self.anchor=selected
            self.start,self.end=selected,None
        self.year,self.month=selected.year,selected.month
        self.paint_calendar()
        self.show_report()
        self.results_scroll.verticalScrollBar().setValue(0)

    def refresh(self,*_):
        if self.sections is not None and self.sections.currentIndex()==1:
            self._normal_dirty=True
            if self.flexflow is not None:
                self._flex_timer.start()
            return
        self._normal_refresh_timer.start()

    def _refresh_normal_now(self):
        if self.sections is not None and self.sections.currentIndex()==1:
            self._normal_dirty=True
            return
        if self.db.cloud_accounting_loaded:
            self.payments.apply_cloud(self.db.cloud_accounting_rows)
        self.completed_days,self.active_days=accounting_days(self.db)
        self._fingerprints=completion_fingerprints(self.db)
        self._paid_days=self.payments.effective_paid(self._fingerprints)
        if self.start is None:
            last=max(self.completed_days,default=date.today().isoformat())
            self.start=date.fromisoformat(last)
            self.anchor=self.start
            self.end=None
            self.year,self.month=self.start.year,self.start.month
        self.paint_calendar()
        self._normal_dirty=False
        self.show_report()

    def paint_calendar(self):
        self.month_title.setText(f'{MONTHS[self.month-1]} {self.year}')
        days=calendar.Calendar(firstweekday=0).monthdatescalendar(self.year,self.month)
        flat=[d for week in days for d in week]
        while len(flat)<42:
            flat.append(flat[-1]+timedelta(days=1))
        start=self.start
        end=self.end or self.start
        for i,btn in enumerate(self.day_buttons):
            day=flat[i]
            key=day.isoformat()
            is_paid=key in self._paid_days
            is_review=key in self.payments.paid and not is_paid
            done=self.completed_days.get(key,0)
            active=self.active_days.get(key,0)
            state='paid' if is_paid else 'review' if is_review else 'done' if done else 'active' if active else 'none'
            selected=bool(start and start<=day<=end)
            outside=day.month!=self.month
            changed=(btn.property('accountState')!=state or
                     btn.property('selectedDay')!=selected or
                     btn.property('outsideMonth')!=outside)
            btn.setProperty('dateKey',key)
            btn.setProperty('accountState',state)
            btn.setProperty('selectedDay',selected)
            btn.setProperty('outsideMonth',outside)
            btn.setText(str(day.day))
            status='ÖDENDİ' if is_paid else 'Değişiklik sonrası ödeme yeniden kontrol edilmeli' if is_review else 'ÖDENMEDİ' if done else 'Aktif sipariş var' if active else 'İşlem yok'
            btn.setToolTip(f'{day:%d.%m.%Y}\n{done} tamamlanan · {active} aktif sipariş (oluşturulma günü)\n{status}')
            if changed:
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        if start:
            if self.end:
                label=f'{self.start:%d.%m.%Y} → {self.end:%d.%m.%Y}'
            else:
                label=f'{self.start:%d.%m.%Y}'
            self.selection_label.setText('Seçili dönem: '+label)
        self.range_text.setText(self.selection_label.text())
        available=self._selected_completed_keys()
        self.paid_btn.setEnabled(bool(available))
        self.unpaid_btn.setEnabled(bool(available or self._selected_marked_keys()))
        if available:
            paid=sum(d in self._paid_days for d in available)
            self.payment_note.setText(f'{len(available)} tamamlanma günü · {paid} ödenmiş, {len(available)-paid} ödenmemiş')
        else:
            self.payment_note.setText('Tamamlanma yok. Varsa önceki ödeme işaretini ÖDENMEDİ ile kaldırabilirsiniz.')

    def _selected_marked_keys(self):
        if self.start is None:return []
        end=self.end or self.start
        return sorted(key for key in self.payments.paid if self.start<=date.fromisoformat(key)<=end)

    def _selected_completed_keys(self):
        if self.start is None:return []
        end=self.end or self.start
        return sorted(key for key in self.completed_days if self.start<=date.fromisoformat(key)<=end)

    def set_payment(self,paid):
        if self.db.cloud_required and not self.cloud_admin_request:
            QMessageBox.information(self,'Muhasebe',
                'Bulut muhasebesi yalnızca Yönetim Panelinden değiştirilebilir.')
            return
        days=self._selected_completed_keys() if paid else sorted(set(self._selected_completed_keys()) | set(self._selected_marked_keys()))
        if not days:
            QMessageBox.information(self,'Muhasebe','Seçili dönemde tamamlanan sipariş bulunmuyor.')
            return
        label='ÖDENDİ' if paid else 'ÖDENMEDİ'
        if len(days)>1 and QMessageBox.question(self,'Muhasebe',
            f'{len(days)} farklı tamamlanma gününü {label} olarak işaretlemek istiyor musunuz?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            if self.db.cloud_required:
                result=self.cloud_admin_request('admin_payment', days=days,paid=bool(paid),
                    fingerprints={key:self._fingerprints.get(key,'') for key in days})
                self.payments.apply_cloud(result.get('accounting_days',[]))
                self.db.cloud_accounting_rows=result.get('accounting_days',[])
                self.db.cloud_accounting_loaded=True
                changed=True
            else:
                changed=self.payments.set_paid(days,paid,self._fingerprints)
            self._paid_days=self.payments.effective_paid(self._fingerprints)
            if changed:
                self.db.audit.record_action('muhasebe',f'Muhasebe günü {label} olarak işaretlendi',
                    f'{days[0]} → {days[-1]} · {len(days)} gün',metadata={'gunler':days,'odendi':paid})
        except Exception as exc:
            QMessageBox.warning(self,'Muhasebe kaydedilemedi',str(exc))
            return
        self.paint_calendar()
        self.show_report()

    def show_report(self):
        if self.start is None:
            return
        if self.sections is not None and self.sections.currentIndex()==1:
            self._normal_dirty=True
            return
        self._report_timer.start()

    def _render_report(self):
        if self.start is None or getattr(self,'_report_building',False):
            return
        if self.sections is not None and self.sections.currentIndex()==1:
            self._normal_dirty=True
            return
        self._report_building=True
        self.setUpdatesEnabled(False)
        try:
            self._build_report()
        finally:
            self._report_building=False
            self.setUpdatesEnabled(True)

    def _build_report(self):
        start=self.start.isoformat()
        end=(self.end or self.start).isoformat()
        self.latest=completed_summary(self.db,start,end)
        m=self.latest['metrics']
        while self.result_layout.count():
            item=self.result_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
            if item.layout():
                from widgets import clear_layout
                clear_layout(item.layout())
        title=text('TAMAMLANAN SİPARİŞLER · MUHASEBE ÖZETİ','AnalyticsSection')
        self.result_layout.addWidget(title)
        paid_revenue=sum(after_shipping_revenue(o) for o in self.latest['orders']
                         if str(o.get('tamamlanma_tarihi',''))[:10] in self._paid_days)
        # Both cards are always reconciled to the same return/shipping-net amount.
        unpaid_revenue=m['after_shipping']-paid_revenue
        paid_days_count=sum(1 for d in self.latest['daily'] if d['orders'] and d['date'] in self._paid_days)
        total_work_days=max(0,int(m.get('working_days',0)))
        # The four amounts people look for first have their OWN visual group.
        # Paid/unpaid describe completed-day accounting flags, NOT an
        # individual customer's payment transaction.
        finance=QFrame()
        finance.setObjectName("AnalyticsRevenueGroup")
        hero=QVBoxLayout(finance)
        hero.setContentsMargins(14,13,14,14)
        hero.setSpacing(9)
        heading=QLabel("CİRO VE TAHSİLAT DURUMU")
        heading.setObjectName("AnalyticsRevenueGroupTitle")
        hero.addWidget(heading)
        explanation=QLabel(
            "Tamamlanan siparişlerin satış tutarları ve seçili dönemin ödeme durumu"
        )
        explanation.setObjectName("AnalyticsRevenueGroupSubtitle")
        explanation.setWordWrap(True)
        hero.addWidget(explanation)
        revenue=[
            ("İade sonrası ciro",money(m["gross"]),MINT,
             "Tamamlanan siparişlerin iade düşülmüş satış tutarı"),
            ("İade ve kargo sonrası ciro",money(m["after_shipping"]),"#65d4fc",
             "İade sonrası cirodan kayıtlı kargo giderleri çıkarılmış"),
            ("Ödenen ciro",money(paid_revenue),"#bba1ff",
             "Ödendi işaretli günlerin iade ve kargo sonrası tutarı"),
            ("Ödenmeyen ciro",money(unpaid_revenue),"#f7c77c",
             "İade ve kargo düşüldükten sonra ödenmedi işaretli tutar"),
        ]
        revenue_columns=self._revenue_columns()
        cards=QGridLayout()
        cards.setHorizontalSpacing(10)
        cards.setVerticalSpacing(10)
        for i,(label,value,accent,meaning) in enumerate(revenue):
            cards.addWidget(RevenuePill(label,value,accent,meaning),
                            i//revenue_columns,i%revenue_columns)
        for column in range(revenue_columns):
            cards.setColumnStretch(column,1)
        hero.addLayout(cards)
        note=QLabel(
            "İade ve kargo sonrası ciro = İade sonrası ciro − kayıtlı kargo "
            "giderleri. Bu tutar net kâr değildir; baskı, işçilik ve "
            "komisyon giderleri ayrıca düşülmemiştir."
        )
        note.setObjectName("AnalyticsRevenueFormula")
        note.setWordWrap(True)
        hero.addWidget(note)
        self.result_layout.addWidget(finance)

        # Secondary figures intentionally use the existing, quieter StatPill
        # design. Similar averages live together, away from key money figures.
        groups=[
            ('İADE İSTATİSTİKLERİ · TAMAMLANMA DÖNEMİ','returns',[
                ('İade öncesi ciro',money(m['gross_before_returns']),BLUE),
                ('İade edilen satış',money(m['returned_revenue']),'#dcb0ff'),
                ('İade edilen sipariş',integer(m['returned_orders']),'#dcb0ff'),
                ('İade / sipariş oranı',f"%{m['return_order_ratio']:.1f}",'#dcb0ff'),
                ('İade / ciro oranı',f"%{m['return_revenue_ratio']:.1f}",'#dcb0ff'),
            ]),
            ('KARGO GİDERLERİ', 'shipping', [
                ('Toplam kargo gideri', money(m['shipping_total']), AMBER),
                ('Telafi siparişi kargosu', money(m['shipping_telafi']), '#ff9d92'),
                ('Açık adres kargosu', money(m['shipping_acik_adres']), AMBER),
                ('Kargo / ciro oranı', f"%{m.get('shipping_ratio',0):.1f}", '#f0ba84'),
            ]),
            ('ORTALAMALAR · BİRİM VERİMLİLİK', 'averages', [
                ('Ort. sipariş tutarı', money(m['avg_order']), PURPLE),
                ('Kitap başına ciro', money(m['per_book']), MINT),
                ('Sayfa başına ciro', money(m['per_page']), MINT),
                ('Kitap / sipariş', f"{m['avg_books']:.1f}", PURPLE),
                ('Sayfa / sipariş', f"{m['avg_pages']:.1f}", AMBER),
                ('Kitap başı ort. sayfa', f"{m.get('avg_pages_book',0):.1f}", '#9fd9b8'),
            ]),
            ('SİPARİŞ · İŞ GÜNÜ', 'orders', [
                ('Tamamlanan', integer(m['orders']), BLUE),
                ('Günlük ort. sipariş', f"{m.get('avg_daily_completed',0):.2f}", '#8ed2ff'),
                ('Çalışılan gün', integer(total_work_days), '#abc9ff'),
                ('Ödenmiş gün', integer(paid_days_count), '#70c8ff'),
            ]),
            ('KİTAP · SAYFA · BASKI TÜRLERİ · SB / RNK', 'printing', [
                ('Toplam kitap', integer(m['books']), BLUE),
                ('Toplam sayfa', integer(m['pages']), MINT),
                ('Kitap çeşidi', integer(m['unique_books']), '#a4c8ff'),
                ('Siyah-beyaz kitap', integer(m['sb']), PURPLE),
                ('Renkli kitap', integer(m['rnk']), '#f3a06e'),
                ('SB sayfa', integer(m['pages_sb']), BLUE),
                ('RNK sayfa', integer(m['pages_rnk']), '#efbd6d'),
                ('Renkli baskı oranı', f"%{m['rnk_share']:.1f}", '#f5bd7f'),
            ]),
        ]
        columns=self._metric_columns()
        self._last_metric_columns=(columns,revenue_columns)
        for group_title, group_kind, entries in groups:
            section=QFrame()
            section.setObjectName('AnalyticsMetricGroup')
            section.setProperty('groupKind',group_kind)
            v=QVBoxLayout(section)
            v.setContentsMargins(10,8,10,10)
            v.setSpacing(7)
            heading=QLabel(group_title)
            heading.setObjectName('AnalyticsGroupTitle')
            heading.setProperty('groupKind',group_kind)
            heading.setFixedHeight(19)
            v.addWidget(heading)
            badges=QGridLayout()
            badges.setHorizontalSpacing(8)
            badges.setVerticalSpacing(8)
            for i,(label,value,color) in enumerate(entries):
                badges.addWidget(StatPill(label,value,color),i//columns,i%columns)
            for column in range(columns):
                badges.setColumnStretch(column,1)
            v.addLayout(badges)
            self.result_layout.addWidget(section)
        daily=self.latest['daily']
        # Aggregate only for the plot when selecting very long periods.
        if len(daily)>125:
            plotted=[]
            for start_i in range(0,len(daily),7):
                subset=daily[start_i:start_i+7]
                row={'label':subset[0]['label'], 'date':subset[0]['date'],
                     **{key:sum(x.get(key,0) for x in subset)
                        for key in ('orders','gross','shipping','pages','sb','rnk','books')}}
                row['after_shipping']=row['gross']-row['shipping']
                row['avg_pages']=row['pages']/row['orders'] if row['orders'] else 0
                plotted.append(row)
            suffix=' / 7 günlük'
        else:
            plotted=[]
            for item in daily:
                row=dict(item)
                row['after_shipping']=row.get('gross',0)-row.get('shipping',0)
                row['avg_pages']=row.get('pages',0)/row.get('orders',0) if row.get('orders') else 0
                plotted.append(row)
            suffix=' / günlük'
        charts=[
            LineChart('Tamamlanan sipariş'+suffix,[('orders','Sipariş',BLUE)]),
            LineChart('Ciro ve kargo'+suffix,[('gross','Ciro',MINT),('shipping','Kargo',AMBER)]),
            LineChart('Net ciro'+suffix,[('after_shipping','Net',MINT)]),
            LineChart('Basılan sayfa'+suffix,[('pages','Sayfa',PURPLE)]),
            LineChart('Kitap adedi'+suffix,[('books','Kitap',BLUE)]),
            LineChart('SB / RNK kitap'+suffix,[('sb','SB',BLUE),('rnk','RNK','#f6ac71')]),
        ]
        chartgrid=QGridLayout();chartgrid.setSpacing(9)
        chartcols=1 if columns<=2 else 2
        for i,chart in enumerate(charts):
            chart.setFixedHeight(220)
            chart.set_data(plotted)
            chartgrid.addWidget(chart,i//chartcols,i%chartcols)
        for i in range(chartcols):chartgrid.setColumnStretch(i,1)
        self.result_layout.addLayout(chartgrid)

        # Keep the platform donut at chart-card width, not a whole empty row.
        # Its companion uses *real* already-computed metrics: there are no
        # invented growth percentages or additional Firebase reads.
        platform_panel=PlatformRevenueDonut(self.latest['platforms'])
        summary_panel=QFrame()
        summary_panel.setObjectName('AnalyticsMetricGroup')
        summary_panel.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        summary_panel.setMinimumHeight(294)
        summary_layout=QVBoxLayout(summary_panel)
        summary_layout.setContentsMargins(12,12,12,12)
        summary_layout.setSpacing(10)
        period=f'{self.start:%d.%m} – {(self.end or self.start):%d.%m}'
        summary_heading=QLabel('ÖZET GÖSTERGELER · '+period)
        summary_heading.setObjectName('AnalyticsGroupTitle')
        summary_layout.addWidget(summary_heading)
        summary_grid=QGridLayout()
        summary_grid.setHorizontalSpacing(9)
        summary_grid.setVerticalSpacing(9)
        snapshot=[
            ('Net ciro',money(m['after_shipping']),MINT,'İade ve kargo sonrası'),
            ('Basılan sayfa',integer(m['pages']),PURPLE,'Seçili tamamlanma dönemi'),
            ('Kitap adedi',integer(m['books']),BLUE,'Seçili tamamlanma dönemi'),
            ('SB / RNK kitap',integer(m['sb'])+' / '+integer(m['rnk']),
             '#f3a06e','Siyah-beyaz / renkli'),
        ]
        for i,(label,value,accent,note) in enumerate(snapshot):
            summary_grid.addWidget(RevenuePill(label,value,accent,note),i//2,i%2)
        summary_grid.setColumnStretch(0,1)
        summary_grid.setColumnStretch(1,1)
        summary_layout.addLayout(summary_grid)
        dashboard_row=QGridLayout()
        dashboard_row.setSpacing(9)
        dashboard_row.addWidget(platform_panel,0,0)
        if chartcols==1:
            dashboard_row.addWidget(summary_panel,1,0)
            dashboard_row.setColumnStretch(0,1)
        else:
            dashboard_row.addWidget(summary_panel,0,1)
            dashboard_row.setColumnStretch(0,1)
            dashboard_row.setColumnStretch(1,1)
        self.result_layout.addLayout(dashboard_row)

        tops=[]
        for row in self.latest.get('books_ranked',[])[:8]:
            name=row['isim']
            tops.append([f"#{row['kod']}",name,row['adet'],row['sb'],row['rnk'],integer(row['pages'])])
        self.result_layout.addWidget(text('EN ÇOK TAMAMLANAN KİTAPLAR','AnalyticsSection'))
        self.result_layout.addWidget(
            self.table(['Kod','Kitap','Adet','SB','RNK','Sayfa'],tops,205))

        self.result_layout.addWidget(text('GÜNLÜK MUHASEBE','AnalyticsSection'))
        rows=[]
        for item in reversed(daily):
            if not item['orders']:continue
            paid='ÖDENDİ' if item['date'] in self._paid_days else 'YENİDEN KONTROL' if item['date'] in self.payments.paid else 'ÖDENMEDİ'
            rows.append([item['date'],item['orders'],money(item['gross']),
                         money(item['shipping']),money(item['gross']-item['shipping']),paid])
        self.result_layout.addWidget(self.table(['Tarih','Tamamlanan','Ciro','Kargo','Kargo sonrası','Ödeme'],rows,165))
        if m['shipping_missing']:
            self.result_layout.addWidget(text(f"Kargo bedeli girilmemiş {m['shipping_missing']} telafi/açık adres siparişi var.",'AccountingHelp'))
        self.result_layout.addStretch()

    def table(self, headers, rows, height):
        tbl=QTableWidget(len(rows),len(headers))
        tbl.setObjectName('AnalyticsDataTable')
        tbl.setHorizontalHeaderLabels(headers)
        tbl.verticalHeader().hide()
        tbl.verticalHeader().setDefaultSectionSize(25)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        tbl.setFixedHeight(height)
        for i,row in enumerate(rows):
            for j,value in enumerate(row):
                cell=QTableWidgetItem(str(value))
                cell.setToolTip(str(value))
                tbl.setItem(i,j,cell)
        hdr=tbl.horizontalHeader()
        for i in range(len(headers)):
            hdr.setSectionResizeMode(i,QHeaderView.ResizeMode.Stretch)
        return tbl

    def export_html(self):
        if not self.latest:
            return
        try:
            desktop=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
            if not desktop.is_dir():
                raise OSError('Windows Masaüstü klasörü bulunamadı.')

            stem=f"ALFA_Muhasebe_{self.latest['start']}_{self.latest['end']}"
            target=desktop/f'{stem}.html'
            number=2
            while target.exists():
                target=desktop/f'{stem}_{number}.html'
                number+=1

            report=html_report(self.latest,self._paid_days,
                               self.payments.paid-self._paid_days)
            # Tarayıcı yazdırma iletişim kutusunu açar, otomatik baskı yapmaz.
            print_script=(
                '<script>window.addEventListener("load",'
                'function(){window.print();},{once:true});</script>'
            )
            report=report.replace('</body></html>',print_script+'</body></html>',1)
            target.write_text(report,encoding='utf-8')
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.resolve()))):
                QMessageBox.warning(
                    self,'Yazdırma ekranı açılamadı',
                    f'HTML raporu Masaüstüne kaydedildi ancak tarayıcı açılamadı:\n{target}'
                )
        except Exception as exc:
            QMessageBox.warning(self,'HTML raporu oluşturulamadı',str(exc))
