"""FlexFlow — a single integrated, read-only in-page production dashboard.

Built once and updated only on visible, explicit or coalesced data changes.
No popup, fictional efficiency score, printer control or Firebase writes.
"""
from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QLinearGradient
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QAbstractItemView
)
from flexflow import estimate, BLACK_PPM, COLOR_PPM


def fmt(value, digits=0):
    return f"{float(value):,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def minutes(value):
    return "Belirsiz" if value is None else fmt(value, 1) + " dk"


def scheme():
    light = str(QApplication.instance().property("alfa_theme") or "koyu") == "acik"
    return {
        "panel": "#ffffff" if light else "#18293d",
        "ink": "#18334a" if light else "#ecf6ff",
        "muted": "#586d7e" if light else "#bed0df",
        "border": "#d4e1eb" if light else "#344e67",
        "track": "#e7eef5" if light else "#2c3e51",
    }


class MetricCard(QFrame):
    def __init__(self, label, color, parent=None):
        super().__init__(parent)
        self.color = color
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)
        self.caption = QLabel(label)
        self.caption.setWordWrap(True)
        self.value = QLabel("—")
        self.value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.value.setStyleSheet("font-weight:900;font-size:23px;color:" + color)
        self.detail = QLabel("")
        self.detail.setWordWrap(True)
        lay.addWidget(self.caption)
        lay.addWidget(self.value)
        lay.addWidget(self.detail)
        self.setMinimumHeight(116)

    def set_values(self, value, detail):
        p = scheme()
        self.setStyleSheet(
            "QFrame{background:" + p["panel"] + ";border:1px solid:" +
            p["border"] + ";border-radius:11px;}"
            "QLabel{border:0;background:transparent;color:" + p["ink"] + ";}"
        )
        self.value.setStyleSheet("font-weight:900;font-size:23px;color:" + self.color)
        self.caption.setStyleSheet("font-size:12px;font-weight:750;color:" + p["muted"])
        self.detail.setStyleSheet("font-size:11px;color:" + p["muted"])
        self.value.setText(str(value))
        self.detail.setText(str(detail))


class HorizontalBars(QWidget):
    """Four equipment/workload bars; no animation timer or third-party plot library."""
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.rows = []
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMouseTracking(True)

    def set_rows(self, rows):
        self.rows = list(rows)
        self.update()

    def paintEvent(self, event):
        p = scheme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(p["panel"]))
        painter.setPen(QPen(QColor(p["border"]), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 12, 12)
        painter.setPen(QColor(p["ink"]))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(18, 27, self.title)
        width = max(70.0, self.width() - 42.0)
        for i, (title, actual, capacity, color, suffix) in enumerate(self.rows[:4]):
            y = 55 + i * 40
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.setPen(QColor(p["ink"]))
            painter.drawText(18, y, title)
            ratio = actual / capacity if capacity > 0 else 0
            value = fmt(actual, 1) + " / " + fmt(capacity, 0) + " " + suffix
            painter.setPen(QColor(p["muted"]))
            painter.drawText(self.rect().adjusted(0, y - 17, -17, 0),
                             Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, value)
            track = QRectF(18, y + 7, width, 11)
            painter.setBrush(QColor(p["track"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(track, 5, 5)
            fill = QRectF(18, y + 7, max(0, width * min(1.0, ratio)), 11)
            if fill.width() > 0:
                gradient = QLinearGradient(fill.topLeft(), fill.topRight())
                gradient.setColorAt(0, QColor(color).darker(115))
                gradient.setColorAt(1, QColor(color))
                painter.setBrush(gradient)
                painter.drawRoundedRect(fill, 5, 5)
        painter.end()


class FlowTimeline(QWidget):
    """Stage-duration visualization; upper bounds are not a promised finish time."""
    def __init__(self):
        super().__init__()
        self.parts = []
        self.setMinimumHeight(230)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_parts(self, parts):
        self.parts = list(parts)
        self.update()

    def paintEvent(self, event):
        p = scheme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(p["border"]), 1))
        painter.setBrush(QColor(p["panel"]))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 12, 12)
        painter.setPen(QColor(p["ink"]))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(18, 27, "İş aşamaları · tahmini dakika")
        maximum = max((hi for _, lo, hi, _ in self.parts), default=0)
        maximum = max(1.0, maximum)
        bar_left = min(176, max(113, self.width() * 0.29))
        bar_width = max(40.0, self.width() - bar_left - 62.0)
        for i, (label, lo, hi, color) in enumerate(self.parts[:4]):
            y = 53 + i * 42
            painter.setPen(QColor(p["ink"]))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(15, y + 14, int(bar_left - 28), 18,
                             Qt.AlignmentFlag.AlignVCenter, label)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(p["track"]))
            track = QRectF(bar_left, y + 12, bar_width, 14)
            painter.drawRoundedRect(track, 6, 6)
            high = bar_width * min(1.0, hi / maximum)
            low = bar_width * min(1.0, lo / maximum)
            if high:
                painter.setBrush(QColor(color).darker(170))
                painter.drawRoundedRect(QRectF(bar_left, y + 12, high, 14), 5, 5)
            if low:
                painter.setBrush(QColor(color))
                painter.drawRoundedRect(QRectF(bar_left, y + 12, low, 14), 5, 5)
            painter.setPen(QColor(p["muted"]))
            painter.drawText(int(bar_left + 4), y + 2, minutes(lo) + " – " + minutes(hi))
        painter.end()


class FlexFlowView(QWidget):
    """Single coherent screen for open (active and pool) production workload."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._last = None
        self.setObjectName("FlexFlowPage")
        root = QVBoxLayout(self)
        root.setContentsMargins(3, 3, 3, 3)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(self.scroll)
        content = QWidget()
        self.scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(9, 11, 12, 15)
        layout.setSpacing(12)
        top = QHBoxLayout()
        header = QLabel("FLEXFLOW  ·  ÜRETİM VERİMLİLİĞİ")
        header.setStyleSheet("font-size:18px;font-weight:900;")
        top.addWidget(header)
        top.addStretch()
        reload = QPushButton("↻  Güncelle")
        reload.clicked.connect(self.refresh)
        top.addWidget(reload)
        layout.addLayout(top)
        self.subtitle = QLabel("Aktif ve havuz siparişlerinden tek üretim yükü · 2 çalışan · 07:00–17:00")
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)
        self.cards = []
        grid = QGridLayout()
        grid.setHorizontalSpacing(11)
        grid.setVerticalSpacing(11)
        for i, (label, color) in enumerate((
            ("Kalan baskı", "#62baff"), ("Standart işçilik", "#57dfb0"),
            ("En erken teorik bitiş", "#f1c270"), ("Mesai marjı", "#d8b3fa")
        )):
            card = MetricCard(label, color)
            grid.addWidget(card, i // 2, i % 2)
            self.cards.append(card)
        layout.addLayout(grid)
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        layout.addWidget(self.warning)
        self.equipment = HorizontalBars("Makine kapasitesi · 10 saatlik teorik tavan")
        self.flow = FlowTimeline()
        layout.addWidget(self.equipment)
        layout.addWidget(self.flow)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        table_label = QLabel("SİPARİŞ BAZLI KALAN İŞ · İLK 30")
        table_label.setStyleSheet("font-weight:900;font-size:13px;")
        layout.addWidget(table_label)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Sipariş", "Durum", "Kalan SB", "Kalan RNK", "Kalan sayfa"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(250)
        self.table.setMaximumHeight(480)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        layout.addStretch()

    def refresh(self):
        pending = [
            row for row in self.db.siparisler
            if not row.get("iade_tarihi")
            and self.db.siparis_durumu(row) in ("aktif", "havuz")
        ]
        page = self.db._book_page_count
        result = estimate(pending, page, now=datetime.now().astimezone())
        self._last = result
        self.cards[0].set_values(fmt(result["print_pages"]) + " sayfa",
                                 fmt(result["print_copies"]) + " nüsha · SB " + fmt(result["pages_sb"]) +
                                 " / RNK " + fmt(result["pages_color"]))
        lo, hi = result["labor_min"]
        self.cards[1].set_values(fmt(lo / 60, 2) + " – " + fmt(hi / 60, 2) + " kişi-saat",
                                 "Delme + spiral + kolileme · standart aralık")
        self.cards[2].set_values(minutes(result["optimistic_elapsed_min"]),
                                 "İdeal iki personel / paralel makine alt sınırı")
        margin = result["shift_remaining_min"] - result["optimistic_elapsed_min"]
        self.cards[3].set_values(("+" if margin >= 0 else "−") + minutes(abs(margin))
                                 if result["fully_known"] else "Belirsiz",
                                 "Bugünkü 17.00 mesai bitişine göre ideal marj")
        self.warning.setText(
            ("⚠ Sayfa sayısı bilinmeyen " + fmt(result["missing_page_copies"]) +
             " nüsha var. Mesai tahmini eksiktir. Kitap kodları: " +
             ", ".join(result["missing_page_codes"][:20]))
            if not result["fully_known"] else
            result["shift_status"] + " · Teorik darboğaz: " + result["bottleneck"])
        self.equipment.set_rows([
            ("Siyah-beyaz baskı", result["pages_sb"], result["black_shift_page_capacity"], "#62baff", "sayfa"),
            ("Renkli baskı", result["pages_color"], result["color_shift_page_capacity"], "#ed9f71", "sayfa"),
            ("Delme · hızlı senaryo", result["punch_min"][0], 600.0, "#ba9bff", "dk"),
            ("Manuel iş yükü · 2 kişi", lo, 1200.0, "#57dfb0", "kişi-dk"),
        ])
        self.flow.set_parts([
            ("Paralel baskı", result["print_min"], result["print_min"], "#62baff"),
            ("Delme", *result["punch_min"], "#ba9bff"),
            ("Elle spiralleme", *result["bind_min"], "#57dfb0"),
            ("Kolileme", *result["pack_min"], "#f0bd71"),
        ])
        self.notice.setText(
            "3 SB × 45 sayfa/dk = " + fmt(BLACK_PPM) + "; 2 normal RNK × 15 ve "
            "1 yavaş RNK × 7,5 = " + fmt(COLOR_PPM, 1) +
            " sayfa/dk. Delme: 300 sayfa/1–2 dk; spiral: 5–45 sn/nüsha; "
            "kolileme: 1–5 dk/sipariş. Alt sınır kesin bitiş süresi değildir. "
            "Hazırlandı/Kolilendi işaretleri ölçülmüş makine veya personel süreleri sayılmaz.")
        rows = []
        for order in pending:
            subtotal = estimate([order], page)
            if subtotal["print_copies"] == 0 and subtotal["pack_orders"] == 0:
                continue
            rows.append((order, subtotal))
        rows.sort(key=lambda pair: pair[1]["print_pages"], reverse=True)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(min(30, len(rows)))
        for i, (order, subtotal) in enumerate(rows[:30]):
            entries = [
                "#" + str(order.get("id", "?")),
                "Aktif" if self.db.siparis_durumu(order) == "aktif" else "Havuz",
                fmt(subtotal["pages_sb"]), fmt(subtotal["pages_color"]),
                fmt(subtotal["print_pages"])
            ]
            for j, value in enumerate(entries):
                self.table.setItem(i, j, QTableWidgetItem(value))
        self.table.setUpdatesEnabled(True)
