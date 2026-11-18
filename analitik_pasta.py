"""Interactive platform revenue donut for ALFA ERP normal analytics.

Income shares use the completed-period, return-adjusted platform gross totals.
Shipping costs remain in the separate final-net metric; they are not a slice.
Uses lightweight Qt painting, no web view or extra graphics dependency.
"""
from __future__ import annotations

from math import atan2, degrees, hypot, isfinite
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QSizePolicy,
    QToolTip, QVBoxLayout, QWidget,
)

COLORS = ("#51b8f8", "#67d5a5", "#f4ba68", "#b797f4",
          "#ff8899", "#7bd5df", "#a9c57b", "#eaa7cb")


def _money(value):
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".") + " TL"


def revenue_slices(platform_rows, max_slices=8):
    """Return positive return-adjusted platform revenue portions, not order counts.

    Group low-volume tail entries into a single 'Diğer platformlar' slice.
    Keep the exact input totals after rounding, including missing platform names.
    """
    sums = {}
    for row in platform_rows:
        name = str(row.get("name") or "Bilinmiyor").strip() or "Bilinmiyor"
        try:
            amount = float(row.get("gross") or 0)
        except (TypeError, ValueError, OverflowError):
            continue
        if not isfinite(amount) or amount <= 0:
            continue
        sums[name] = sums.get(name, 0.0) + amount
    items = sorted(sums.items(), key=lambda item: (-item[1], item[0].casefold()))
    count = max(2, int(max_slices))
    if len(items) > count:
        items = items[:count-1] + [
            ("Diğer platformlar", sum(amount for _, amount in items[count-1:]))
        ]
    total = sum(amount for _, amount in items)
    if total <= 0:
        return []
    return [
        {"name": name, "amount": amount, "percent": amount * 100.0 / total}
        for name, amount in items
    ]


def _light():
    return str(QApplication.instance().property("alfa_theme") or "koyu") == "acik"


class _DonutCanvas(QWidget):
    hovered = Signal(int)

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.rows = list(rows)
        self.current = -1
        self.setFixedSize(236, 236)
        self.setMouseTracking(True)

    def _region(self):
        # Consistent geometry in both painting and hit detection.
        return 118.0, 118.0, 102.0, 59.0

    def _index_at(self, point):
        if not self.rows:
            return -1
        cx, cy, outer, inner = self._region()
        dx, dy = point.x()-cx, point.y()-cy
        radius = hypot(dx, dy)
        if radius < inner or radius > outer+4:
            return -1
        # QPainter's positive angles are counter-clockwise, starting at 3 o'clock.
        # Slices begin at 12 o'clock and progress clockwise.
        ccw = (degrees(atan2(-dy, dx)) + 360.0) % 360.0
        clockwise = (90.0 - ccw) % 360.0
        acc = 0.0
        for idx, row in enumerate(self.rows):
            acc += 3.6*row["percent"]
            if clockwise <= acc + 1e-7:
                return idx
        return len(self.rows)-1

    def mouseMoveEvent(self, event):
        index = self._index_at(event.position())
        if index != self.current:
            self.current = index
            self.hovered.emit(index)
            if index >= 0:
                r = self.rows[index]
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    r["name"] + "\n" + _money(r["amount"]) +
                    "\n%" + f'{r["percent"]:.1f}'.replace(".", ","),
                    self,
                )
            else:
                QToolTip.hideText()
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.current != -1:
            self.current = -1
            self.hovered.emit(-1)
            QToolTip.hideText()
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        light = _light()
        panel = QColor("#ffffff" if light else "#172a3f")
        muted = QColor("#63788a" if light else "#c3d4e6")
        ink = QColor("#21394d" if light else "#f1f7ff")
        cx, cy, outer, inner = self._region()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.rows:
            p.setBrush(QColor("#d9e4ec" if light else "#364b60"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx-outer, cy-outer, outer*2, outer*2))
            p.setBrush(panel)
            p.drawEllipse(QRectF(cx-inner, cy-inner, inner*2, inner*2))
            p.setPen(ink)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Henüz satış yok")
            p.end()
            return

        accumulated = 0.0
        for i, row in enumerate(self.rows):
            r = outer+3.0 if i == self.current else outer
            rect = QRectF(cx-r, cy-r, r*2, r*2)
            span = 3.6*row["percent"]
            col = QColor(COLORS[i % len(COLORS)])
            if i == self.current:
                col = col.lighter(120)
            p.setBrush(col)
            p.setPen(QPen(panel, 2.0))
            p.drawPie(rect, round((90.0-accumulated)*16),
                      -round(span*16))
            accumulated += span
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(panel)
        p.drawEllipse(QRectF(cx-inner, cy-inner, inner*2, inner*2))
        p.setPen(ink)
        p.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        total = sum(r["amount"] for r in self.rows)
        short = _money(total)
        if len(short) > 16:
            short = f'{total:,.0f}'.replace(",", ".") + " TL"
        p.drawText(QRectF(cx-inner+5, cy-23, inner*2-10, 27),
                   Qt.AlignmentFlag.AlignCenter, short)
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(muted)
        p.drawText(QRectF(cx-inner+6, cy+6, inner*2-12, 30),
                   Qt.AlignmentFlag.AlignCenter, "İade sonrası ciro")
        p.end()


class PlatformRevenueDonut(QFrame):
    """Single static-size painter and a dynamic platform legend next to it."""

    def __init__(self, platforms, parent=None):
        super().__init__(parent)
        self.rows = revenue_slices(platforms)
        self.setObjectName("AnalyticsPlatformDonut")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(261)
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 9, 12, 9)
        h.setSpacing(16)
        self.canvas = _DonutCanvas(self.rows, self)
        h.addWidget(self.canvas, 0, Qt.AlignmentFlag.AlignVCenter)
        sidebar = QVBoxLayout()
        sidebar.setSpacing(7)
        caption = QLabel("SATIŞ PLATFORMU PAYLARI")
        caption.setObjectName("DonutLegendHeading")
        sidebar.addWidget(caption)
        self.legends = []
        for i, row in enumerate(self.rows):
            label = QLabel()
            label.setWordWrap(True)
            label.setMinimumHeight(24)
            label.setToolTip(
                row["name"] + " · " + _money(row["amount"]) +
                " · %" + f'{row["percent"]:.1f}'.replace(".", ",")
            )
            sidebar.addWidget(label)
            self.legends.append(label)
        if not self.rows:
            note = QLabel("Seçilen tarihlerde iade sonrası satış geliri bulunmuyor.")
            note.setWordWrap(True)
            sidebar.addWidget(note)
        sidebar.addStretch()
        h.addLayout(sidebar, 1)
        self.canvas.hovered.connect(self._highlight)
        self._highlight(-1)

    def _highlight(self, selected):
        light = _light()
        panel = "#ffffff" if light else "#172a3f"
        ink = "#20394b" if light else "#ecf7ff"
        secondary = "#536b7f" if light else "#c1d3e5"
        self.setStyleSheet(
            "QFrame#AnalyticsPlatformDonut{background:" + panel +
            ";border:1px solid " + ("#d6e1eb" if light else "#3e5773") +
            ";border-radius:12px;}"
            "QLabel#DonutLegendHeading{color:" + secondary +
            ";font-weight:900;font-size:12px;border:0;background:transparent;}"
        )
        for i, label in enumerate(self.legends):
            item = self.rows[i]
            accent = COLORS[i % len(COLORS)]
            ratio = f'{item["percent"]:.1f}'.replace(".", ",")
            label.setText(
                "●  " + item["name"] + "  ·  %" + ratio +
                "  ·  " + _money(item["amount"])
            )
            label.setStyleSheet(
                "color:" + (accent if i == selected else ink) +
                ";font-size:12px;font-weight:" +
                ("900" if i == selected else "650") +
                ";background:transparent;border:0;"
            )
