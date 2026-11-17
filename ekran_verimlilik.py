"""Owner-only FlexFlow read-only capacity view for Analitik.

No cloud mutation, printer control, actual productivity measurement or payroll.
"""
from __future__ import annotations

from html import escape
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QTextBrowser, QWidget,
)
from flexflow import estimate, BLACK_PPM, COLOR_PPM, SHIFT_MINUTES, WORKERS


def _int(value):
    return f"{int(value):,}".replace(",", ".")


def _minute(value):
    if value is None:
        return "Bilinmiyor"
    return f"{float(value):,.1f}".replace(",", "_").replace(".", ",").replace("_", ".") + " dk"


def _pair(value):
    return _minute(value[0]) + " – " + _minute(value[1])


def _row(label, value):
    return ("<tr><td style='padding:7px 12px;border-bottom:1px solid #8291a04a'>"
            + escape(label) + "</td><td style='padding:7px 12px;border-bottom:1px solid #8291a04a'><b>"
            + escape(str(value)) + "</b></td></tr>")


def _html(values, historical=False):
    page_note = (
        "<p><b>Eksik sayfa bilgisi:</b> " + _int(values["missing_page_copies"]) +
        " nüsha. Kitap kodları: " + escape(", ".join(values["missing_page_codes"][:25])) +
        ". Aşağıdaki süreler sadece sayfası bilinen kitapların işini içerir; "
        "mesai sonucu güvenilir değildir.</p>"
        if not values["fully_known"] else ""
    )
    rows = [
        ("Sipariş", _int(values["orders"])),
        ("Basılacak SB nüsha", _int(values["copies_sb"])),
        ("Basılacak renkli nüsha", _int(values["copies_color"])),
        ("SB baskı sayfası", _int(values["pages_sb"])),
        ("Renkli baskı sayfası", _int(values["pages_color"])),
        ("Baskı toplamı", _int(values["print_pages"]) + " sayfa"),
        ("Baskı süresi · siyah", _minute(values["print_sb_min"])),
        ("Baskı süresi · renkli", _minute(values["print_color_min"])),
        ("Paralel cihazlarda baskı alt süresi", _minute(values["print_min"])),
        ("Delme makinesi", _pair(values["punch_min"])),
        ("Elle spiralleme", _pair(values["bind_min"])),
        ("Kolileme · " + _int(values["pack_orders"]) + " sipariş", _pair(values["pack_min"])),
        ("Standart manuel işçilik", _pair(values["labor_min"])),
        ("Standart işçilik saatleri", f'{values["labor_min"][0]/60:.2f} – {values["labor_min"][1]/60:.2f} kişi-saat'),
        ("Teorik darboğaz", values["bottleneck"]),
        ("İdeal koşullarda teorik alt sınır", _minute(values["optimistic_elapsed_min"])),
        ("Sıralı üst senaryo", _minute(values["sequential_elapsed_min"])),
    ]
    if not historical:
        rows += [
            ("Bugün kalan 07.00–17.00 mesaisi", _minute(values["shift_remaining_min"])),
            ("Mesai değerlendirmesi", values["shift_status"]),
            ("En az olası mesai aşımı", _minute(values["minimum_overtime_min"])),
            ("Sıralı senaryoda mesai aşımı", _minute(values["scenario_overtime_min"])),
        ]
    note = ("Tamamlanan işler üzerinden teorik standart iş yükü hesaplanır; bu rakamlar "
            "çalışanların gerçekten kaç saat çalıştığını göstermez."
            if historical else
            "Aktif siparişlerde hazırlanmış nüshalar yeniden basılacak sayılmaz. "
            "Bir siparişte kolilenmemiş nüsha varsa bir kez paketleme süresi ayrılır.")
    body = "".join(_row(a, b) for a, b in rows)
    return (
        "<h2>FlexFlow · sayısal üretim kapasitesi</h2>"
        "<p>" + escape(note) + "</p>" + page_note +
        "<table width='100%' cellspacing='0' cellpadding='0'>" + body + "</table>"
        "<p><b>Gerçek cihaz parkı:</b> 3 × 45 = " + _int(BLACK_PPM) +
        " SB sayfa/dk; 2 × 15 + 1 × 7,5 = " + str(COLOR_PPM).replace(".", ",") +
        " renkli sayfa/dk. " + _int(WORKERS) + " çalışan; 1 delme makinesi.</p>"
        "<p><b>10 saatlik ideal baskı tavanı:</b> " +
        _int(values["black_shift_page_capacity"]) + " SB sayfa ve " +
        _int(values["color_shift_page_capacity"]) + " renkli sayfa. "
        "Delme 300 sayfada 1–2 dk, elle spiralleme 5–45 sn/nüsha, "
        "kolileme 1–5 dk/sipariş varsayılır.</p>"
        "<p><i>Alt sınır, iki kişinin paralel çalışabildiği ideal senaryodur; "
        "üst senaryo işlerin sırayla işlendiği durumdur. Bunlar kesin teslim "
        "saatleri veya gerçek cihaz telemetrisi değildir. Duruş, mola, arıza, "
        "hazırlık, baskı tekrarları ve işlerin ayrıntılı sıralaması hesaba katılmaz. "
        "Mesai 07.00–17.00; ertesi gün ve hafta sonu çalışma planı varsayılmaz.</i></p>"
    )


class FlexFlowDialog(QDialog):
    def __init__(self, db, completed_orders=(), period_label="", parent=None):
        super().__init__(parent)
        self.db = db
        self.completed_orders = list(completed_orders)
        self.setWindowTitle("ALFA ERP Yönetici · Analitik · Verimlilik (FlexFlow)")
        self.resize(860, 730)
        self.setMinimumSize(640, 520)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        title = QLabel("<b>FlexFlow · Verimlilik</b> — gerçek kapasite varsayımları")
        top.addWidget(title)
        top.addStretch()
        refresh = QPushButton("↻ Güncelle")
        refresh.clicked.connect(self.refresh)
        top.addWidget(refresh)
        layout.addLayout(top)

        self.tabs = QTabWidget()
        self.active = QTextBrowser()
        self.pool = QTextBrowser()
        self.history = QTextBrowser()
        self.tabs.addTab(self.active, "Aktif üretim")
        self.tabs.addTab(self.pool, "Havuz yükü")
        self.tabs.addTab(self.history, "Tamamlanan dönem")
        for view in (self.active, self.pool, self.history):
            view.setOpenExternalLinks(False)
            view.setReadOnly(True)
        layout.addWidget(self.tabs, 1)
        if period_label:
            footer = QLabel("Tamamlanan dönem: " + period_label)
            layout.addWidget(footer)
        self.refresh()

    def refresh(self):
        active, pool = [], []
        for order in self.db.siparisler:
            if order.get("iade_tarihi"):
                continue
            state = self.db.siparis_durumu(order)
            if state == "aktif":
                active.append(order)
            elif state == "havuz":
                pool.append(order)
        pages = self.db._book_page_count
        self.active.setHtml(_html(estimate(active, pages)))
        self.pool.setHtml(_html(estimate(pool, pages)))
        self.history.setHtml(_html(estimate(self.completed_orders, pages, completed=True), historical=True))
