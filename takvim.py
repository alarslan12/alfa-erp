"""ALFA ERP takvimi: sipariş günleri belirgin, bir gün veya Shift+klik aralığı."""
from datetime import date
import calendar
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QApplication, QPushButton
from widgets import button

MONTHS = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos',
          'Eylül', 'Ekim', 'Kasım', 'Aralık')
WEEK = ('Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz')


class TarihPopup(QDialog):
    selected = Signal(object, object)

    def __init__(self, dates, parent=None):
        super().__init__(parent)
        self.setObjectName('DatePickerDialog')
        self.setWindowTitle('Sipariş Takvimi')
        self.setModal(True)
        self.days = {str(d)[:10] for d in dates if len(str(d)) >= 10}
        self.anchor = self.start = self.end = None
        initial = QDate.fromString(max(self.days), 'yyyy-MM-dd') if self.days else QDate.currentDate()
        if not initial.isValid():
            initial = QDate.currentDate()
        self.year, self.month = initial.year(), initial.month()
        self.setFixedWidth(406)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 17, 18, 17)
        root.setSpacing(11)
        heading = QLabel('Sipariş tarihini seç')
        heading.setObjectName('CalendarTitle')
        root.addWidget(heading)
        guide = QLabel('Gün seç • Shift + tık ile tarih aralığı')
        guide.setObjectName('CalendarHelp')
        root.addWidget(guide)

        monthbar = QHBoxLayout()
        prev = button('‹', 'CalendarArrow')
        prev.setFixedSize(36, 34)
        prev.clicked.connect(lambda: self.change_month(-1))
        self.month_label = QLabel()
        self.month_label.setObjectName('CalendarMonth')
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        next_btn = button('›', 'CalendarArrow')
        next_btn.setFixedSize(36, 34)
        next_btn.clicked.connect(lambda: self.change_month(1))
        monthbar.addWidget(prev)
        monthbar.addWidget(self.month_label, 1)
        monthbar.addWidget(next_btn)
        root.addLayout(monthbar)

        self.days_grid = QGridLayout()
        self.days_grid.setContentsMargins(0, 0, 0, 0)
        self.days_grid.setHorizontalSpacing(5)
        self.days_grid.setVerticalSpacing(5)
        for i, name in enumerate(WEEK):
            label = QLabel(name)
            label.setObjectName('CalendarWeekday')
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.days_grid.addWidget(label, 0, i)
        self.day_buttons = []
        for row in range(1, 7):
            for col in range(7):
                b = QPushButton()
                b.setObjectName('CalendarDay')
                b.setFixedHeight(37)
                b.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                b.clicked.connect(lambda checked=False, w=b: self.choose_day(w.property('dateKey')))
                self.days_grid.addWidget(b, row, col)
                self.day_buttons.append(b)
        root.addLayout(self.days_grid)

        legend = QHBoxLayout()
        marker = QLabel('●')
        marker.setObjectName('CalendarMarker')
        legend.addWidget(marker)
        legend.addWidget(QLabel('Sipariş bulunan gün'))
        legend.addStretch()
        root.addLayout(legend)
        self.selection = QLabel('Henüz tarih seçilmedi')
        self.selection.setObjectName('CalendarSelection')
        root.addWidget(self.selection)

        buttons = QHBoxLayout()
        clear = button('Filtreyi kaldır', 'SmallAction')
        clear.clicked.connect(lambda: (self.selected.emit(None, None), self.accept()))
        apply = button('Tarihi uygula', 'Accent')
        apply.clicked.connect(self.apply)
        buttons.addWidget(clear)
        buttons.addStretch()
        buttons.addWidget(apply)
        root.addLayout(buttons)
        self.render()

    def showEvent(self, event):
        super().showEvent(event)
        owner = self.parentWidget()
        if owner:
            center = owner.window().frameGeometry().center()
            frame = self.frameGeometry()
            frame.moveCenter(center)
            self.move(frame.topLeft())

    def change_month(self, delta):
        month_index = self.year * 12 + self.month - 1 + delta
        self.year, m = divmod(month_index, 12)
        self.month = m + 1
        self.render()

    def choose_day(self, key):
        if not key:
            return
        picked = QDate.fromString(key, 'yyyy-MM-dd')
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier and self.anchor:
            self.start, self.end = sorted((self.anchor, picked))
        else:
            self.anchor = picked
            self.start, self.end = picked, None
        self.selection.setText(
            self.start.toString('dd.MM.yyyy') +
            ('  →  ' + self.end.toString('dd.MM.yyyy') if self.end else ' · Tek gün')
        )
        self.render()

    def render(self):
        self.month_label.setText(f'{MONTHS[self.month - 1]} {self.year}')
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(self.year, self.month)
        days = [d for week in weeks for d in week]
        while len(days) < 42:
            days.append(days[-1] + __import__('datetime').timedelta(days=1))
        lo = self.start.toString('yyyy-MM-dd') if self.start else None
        hi = (self.end or self.start).toString('yyyy-MM-dd') if self.start else None
        for idx, btn in enumerate(self.day_buttons):
            day = days[idx]
            key = day.isoformat()
            active = key in self.days
            chosen = lo is not None and lo <= key <= hi
            own = day.month == self.month
            btn.setText(str(day.day))
            btn.setProperty('dateKey', key)
            btn.setProperty('hasOrder', active)
            btn.setProperty('selectedDay', chosen)
            btn.setProperty('otherMonth', not own)
            btn.setToolTip(f'{day.strftime("%d.%m.%Y")} · ' + ('Sipariş var' if active else 'Sipariş yok'))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def apply(self):
        if not self.start:
            return
        self.selected.emit(self.start.toString('yyyy-MM-dd'),
                           self.end.toString('yyyy-MM-dd') if self.end else None)
        self.accept()
