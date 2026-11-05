"""ALFA ERP V4.29 · Konuya göre sınıflandırılmış performans ve takvim muhasebesi."""
import calendar
from datetime import date, timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QPointF, QDate, QTimer, QEvent
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSizePolicy, QApplication, QCheckBox
)
from PySide6.QtCore import QUrl
from widgets import button, text, scrollable
from muhasebe_veri import PaymentDays, accounting_days, completed_summary, html_report, completion_fingerprints
from takvim import MONTHS, WEEK

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
    """Hafif yerel grafik; yeni paket kurmaya gerek yok."""
    def __init__(self, title, series):
        super().__init__()
        self.title = title
        self.series = series    # (dataset_key, caption, color)
        self.data = []
        self.setObjectName('AnalyticsChart')
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_data(self, data):
        self.data = data
        self.update()

    def _colors(self):
        theme = str(QApplication.instance().property('alfa_theme') or 'koyu')
        if theme == 'acik':
            return {
                'bg': CREAM_BG, 'panel': CREAM_PANEL, 'border': CREAM_BORDER,
                'text': CREAM_TEXT, 'muted': CREAM_MUTED, 'grid': '#dacdbc'
            }
        return {
            'bg': NAVY, 'panel': NAVY, 'border': '#3b516c',
            'text': FG, 'muted': MUTED, 'grid': '#34475e'
        }

    def paintEvent(self, event):
        colors=self._colors()
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(colors['panel']))
        painter.setPen(QPen(QColor(colors['border']),1))
        painter.drawRoundedRect(self.rect().adjusted(1,1,-2,-2),12,12)
        painter.setFont(QFont('Segoe UI',11,QFont.Weight.Bold))
        painter.setPen(QColor(colors['text']))
        painter.drawText(17,25,self.title)
        right=self.width()-20
        xlegend=right
        painter.setFont(QFont('Segoe UI',8))
        for key,label,col in reversed(self.series):
            w=max(66,len(label)*6+22)
            xlegend-=w
            painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor(col))
            painter.drawEllipse(xlegend,16,7,7)
            painter.setPen(QColor(colors['muted']))
            painter.drawText(xlegend+11,23,label)
        l, t, r, b = 47,47,max(75,self.width()-17),self.height()-36
        if r-l<40 or b-t<45:
            painter.end();return
        vals=[float(item.get(key,0)) for item in self.data for key,_,_ in self.series]
        ymax=max(vals, default=0)
        ymax=max(1,ymax*1.12)
        painter.setFont(QFont('Segoe UI',8))
        for j in range(5):
            y=t+(b-t)*j/4
            painter.setPen(QPen(QColor(colors['grid']),1))
            painter.drawLine(int(l),int(y),int(r),int(y))
            v=ymax*(1-j/4)
            s=(f'{v/1000:.1f}k' if v>=1000 else f'{v:.0f}' if v>=10 else f'{v:.1f}')
            painter.setPen(QColor(colors['muted']))
            painter.drawText(7,int(y)+4,37,12,Qt.AlignmentFlag.AlignRight,s)
        n=len(self.data)
        if n:
            labels=[0,n//4,n//2,3*n//4,n-1]
            for idx in dict.fromkeys(labels):
                x=(l+r)/2 if n==1 else l+(r-l)*idx/max(1,n-1)
                painter.setPen(QColor(colors['muted']))
                painter.drawText(int(x)-21,b+8,42,17,Qt.AlignmentFlag.AlignHCenter,self.data[idx]['label'])
        if n==0:
            painter.setPen(QColor(colors['muted']))
            painter.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'Henüz veri yok')
        if n == 1:
            # A line chart with one date is just a dot: display proportional bars.
            plot_width = max(45, r-l)
            bar_w = min(58, max(28, int(plot_width/(len(self.series)*4))))
            spacing = min(22, max(8, bar_w//2))
            group_w = len(self.series)*bar_w + (len(self.series)-1)*spacing
            base_x = (l+r-group_w)/2
            for index,(key,label,color) in enumerate(self.series):
                value = float(self.data[0].get(key,0))
                height = (b-t)*value/ymax
                x = base_x + index*(bar_w+spacing)
                y = b-height
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(color))
                if height > 0:
                    painter.drawRoundedRect(int(x),int(y),bar_w,max(2,int(height)),4,4)
                else:
                    painter.drawRoundedRect(int(x),int(b)-2,bar_w,2,1,1)
                number = f'{value:,.0f}' if key in ('orders','pages','sb','rnk','books') else f'{value:,.2f}'
                painter.setPen(QColor(colors['text']))
                painter.setFont(QFont('Segoe UI',9,QFont.Weight.Bold))
                painter.drawText(int(x)-25,int(max(t+2,y-20)),bar_w+50,17,
                                 Qt.AlignmentFlag.AlignHCenter,number)
        else:
            for key,label,color in self.series:
                pen=QPen(QColor(color))
                pen.setWidthF(2.5)
                painter.setPen(pen)
                path=QPainterPath()
                for i,item in enumerate(self.data):
                    x=l+(r-l)*i/max(1,n-1)
                    y=b-(b-t)*float(item.get(key,0))/ymax
                    if i==0: path.moveTo(x,y)
                    else:path.lineTo(x,y)
                painter.drawPath(path)
        painter.end()


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
        val.setStyleSheet(f'color:{accent};')
        val.setToolTip(f'{title}: {value}')
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(val)


class AnalitikView(QWidget):
    """Selected completion day/range -> completed orders only, with payment tracking."""
    def __init__(self, db, on_open_order=None):
        super().__init__()
        self.setObjectName('AnalyticsPage')
        self.db=db
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
        header=QHBoxLayout()
        heading=text('◈  Muhasebe & Analitik', 'AnalyticsTitle')
        header.addWidget(heading)
        header.addStretch()
        self.range_text=text('','AccountingPeriod')
        header.addWidget(self.range_text)
        export=button('↗ HTML Raporu', 'AnalyticsExport')
        export.setToolTip('Seçili tamamlanma tarihlerindeki kayıtlarla HTML muhasebe raporu oluştur')
        export.clicked.connect(self.export_html)
        header.addWidget(export)
        reload=button('↻','SmallAction')
        reload.setToolTip('Siparişleri ve takvimi yenile')
        reload.clicked.connect(self.refresh)
        header.addWidget(reload)
        root.addLayout(header)

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
        root.addLayout(body,1)
        self.refresh()

    def eventFilter(self, watched, event):
        if watched is self.results_scroll.viewport() and event.type()==QEvent.Type.Resize:
            if hasattr(self,'_reflow_timer'):
                self._reflow_timer.start()
        return super().eventFilter(watched,event)

    def _metric_columns(self):
        width=self.results_scroll.viewport().width()
        return 2 if width<600 else 3 if width<880 else 4 if width<1170 else 5

    def _adapt_width(self):
        if self._last_metric_columns != self._metric_columns():
            self.show_report()

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
            btn.setProperty('dateKey',key)
            btn.setProperty('accountState',state)
            btn.setProperty('selectedDay',bool(start and start<=day<=end))
            btn.setProperty('outsideMonth',day.month!=self.month)
            btn.setText(str(day.day))
            status='ÖDENDİ' if is_paid else 'Değişiklik sonrası ödeme yeniden kontrol edilmeli' if is_review else 'ÖDENMEDİ' if done else 'Aktif sipariş var' if active else 'İşlem yok'
            btn.setToolTip(f'{day:%d.%m.%Y}\n{done} tamamlanan · {active} aktif sipariş (oluşturulma günü)\n{status}')
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
        paid_revenue=sum(float(o.get('ciro') or 0) for o in self.latest['orders']
                         if str(o.get('tamamlanma_tarihi',''))[:10] in self._paid_days)
        unpaid_revenue=m['gross']-paid_revenue
        paid_days_count=sum(1 for d in self.latest['daily'] if d['orders'] and d['date'] in self._paid_days)
        total_work_days=max(0,int(m.get('working_days',0)))
        payment_ratio=(100*paid_days_count/total_work_days) if total_work_days else 0.0
        # Birbiriyle ilişkili değerler aynı başlık altında, ardışık
        # küçük rozetlerde yer alır; ekran genişliğine göre sütun sayısı değişir.
        groups=[
            ('FİNANS · CİRO', 'finance', [
                ('Toplam ciro', money(m['gross']), MINT),
                ('Kargo sonrası', money(m['after_shipping']), MINT),
                ('Ort. sipariş', money(m['avg_order']), PURPLE),
                ('Sayfa başına ciro', money(m['per_page']), MINT),
                ('Ödenen ciro', money(paid_revenue), '#77bdfd'),
                ('Ödenmeyen ciro', money(unpaid_revenue), '#f0c177'),
            ]),
            ('KARGO GİDERLERİ', 'shipping', [
                ('Kargo gideri', money(m['shipping_total']), AMBER),
                ('Telafi kargo', money(m['shipping_telafi']), '#ff9d92'),
                ('Açık adres kargo', money(m['shipping_acik_adres']), AMBER),
                ('Kargo / ciro oranı', f"%{m.get('shipping_ratio',0):.1f}", '#f0ba84'),
            ]),
            ('SİPARİŞ · İŞ GÜNÜ', 'orders', [
                ('Tamamlanan', integer(m['orders']), BLUE),
                ('Günlük ort. sipariş', f"{m.get('avg_daily_completed',0):.2f}", '#8ed2ff'),
                ('Çalışılan gün', integer(total_work_days), '#abc9ff'),
                ('Ödenmiş gün', integer(paid_days_count), '#70c8ff'),
                ('Ödeme kapsama', f"%{payment_ratio:.1f}", '#76d3aa'),
            ]),
            ('KİTAP · SAYFA', 'books', [
                ('Toplam kitap', integer(m['books']), BLUE),
                ('Toplam sayfa', integer(m['pages']), MINT),
                ('Kitap / sipariş', f"{m['avg_books']:.1f}", PURPLE),
                ('Sayfa / sipariş', f"{m['avg_pages']:.1f}", AMBER),
                ('Kitap başı ort. sayfa', f"{m.get('avg_pages_book',0):.1f}", '#9fd9b8'),
                ('Kitap çeşidi', integer(m['unique_books']), '#a4c8ff'),
            ]),
            ('BASKI TÜRLERİ · SB / RNK', 'printing', [
                ('Siyah-beyaz kitap', integer(m['sb']), PURPLE),
                ('Renkli kitap', integer(m['rnk']), '#f3a06e'),
                ('SB sayfa', integer(m['pages_sb']), BLUE),
                ('RNK sayfa', integer(m['pages_rnk']), '#efbd6d'),
                ('Renkli baskı oranı', f"%{m['rnk_share']:.1f}", '#f5bd7f'),
            ]),
        ]
        columns=self._metric_columns()
        self._last_metric_columns=columns
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
            for c in range(columns):
                badges.setColumnStretch(c,1)
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

        distribution=QHBoxLayout();distribution.setSpacing(9)
        tops=[]
        for row in self.latest.get('books_ranked',[])[:8]:
            name=row['isim']
            tops.append([f"#{row['kod']}",name,row['adet'],row['sb'],row['rnk'],integer(row['pages'])])
        platform_rows=[[r['name'],r['orders'],integer(r['books']),money(r['gross'])]
                       for r in self.latest['platforms'][:8]]
        # Compact distribution tables give useful detail even for a single date.
        panels=[('EN ÇOK TAMAMLANAN KİTAPLAR',
                 ['Kod','Kitap','Adet','SB','RNK','Sayfa'],tops),
                ('PLATFORMA GÖRE',
                 ['Platform','Sipariş','Kitap','Ciro'],platform_rows)]
        if columns>=4:
            for caption,head,rows in panels:
                sub=QVBoxLayout();sub.setSpacing(5)
                sub.addWidget(text(caption,'AnalyticsSection'))
                sub.addWidget(self.table(head,rows,205))
                distribution.addLayout(sub,1)
            self.result_layout.addLayout(distribution)
        else:
            for caption,head,rows in panels:
                self.result_layout.addWidget(text(caption,'AnalyticsSection'))
                self.result_layout.addWidget(self.table(head,rows,205))

        self.result_layout.addWidget(text('GÜNLÜK MUHASEBE','AnalyticsSection'))
        rows=[]
        for item in reversed(daily):
            if not item['orders']:continue
            paid='ÖDENDİ' if item['date'] in self._paid_days else 'YENİDEN KONTROL' if item['date'] in self.payments.paid else 'ÖDENMEDİ'
            rows.append([item['date'],item['orders'],money(item['gross']),
                         money(item['shipping']),money(item['gross']-item['shipping']),paid])
        self.result_layout.addWidget(self.table(['Tarih','Tamamlanan','Ciro','Kargo','Kargo sonrası','Ödeme'],rows,165))
        self.result_layout.addWidget(text('SİPARİŞLER','AnalyticsSection'))
        orders=[]
        for o in self.latest['orders'][:80]:
            total=self.db.siparis_ozeti(o)
            orders.append([f"#{o.get('id','')}",str(o.get('tamamlanma_tarihi',''))[:16].replace('T',' '),
                str(o.get('platform') or 'Manuel'),total['adet'],total['sayfa'],
                money(float(o.get('ciro') or 0))])
        self.result_layout.addWidget(self.table(['No','Tamamlanma','Platform','Kitap','Sayfa','Ciro'],orders,205))
        if len(self.latest['orders'])>80:
            self.result_layout.addWidget(text('İlk 80 sipariş gösteriliyor; HTML raporu tüm siparişleri içerir.','AccountingHelp'))
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
        if not self.latest:return
        file,_=QFileDialog.getSaveFileName(self,'Muhasebe HTML raporu kaydet',
            f"ALFA_Muhasebe_{self.latest['start']}_{self.latest['end']}.html",'HTML dosyası (*.html)')
        if not file:return
        try:
            target=Path(file)
            if target.suffix.lower()!='.html':target=target.with_suffix('.html')
            target.write_text(html_report(self.latest,self._paid_days,
                                          self.payments.paid-self._paid_days),encoding='utf-8')
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.resolve())))
        except Exception as exc:
            QMessageBox.warning(self,'HTML raporu oluşturulamadı',str(exc))
