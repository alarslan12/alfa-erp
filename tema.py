"""ALFA ERP'nin tek dosyalık grafik sistemi. Gelecek sürümlerde yalnızca bu QSS düzenlenebilir."""
BG='#10151f'; SURFACE='#1a2230'; SURFACE2='#202b3a'; BORDER='#344154'; TEXT='#e9eef7'; MUTED='#97a5b8'; AMBER='#f1b46f'; GREEN='#6acbaa'; PURPLE='#c3a6ff'; ORANGE='#f6ad7e'
QSS = '''
* { font-family: 'Segoe UI', 'Arial'; font-size: 13px; color:#e9eef7; }
QWidget#AppRoot, QMainWindow, QDialog { background:#10151f; }
QWidget#AppBody { background:#10151f; }
QWidget#Panel, QFrame#Panel, QFrame#Card, QFrame#OrderRow, QFrame#BasketRow { background:#1a2230; border:1px solid #344154; border-radius:11px; }
QFrame#Card:hover, QFrame#OrderRow:hover { border:1px solid #f1b46f; }
QFrame#Header { background:#151c28; border-bottom:1px solid #344154; }
QFrame#Toolbar { background:#1a2230; border:1px solid #344154; border-radius:11px; }
QLabel#Brand { color:#f1b46f; font-size:22px; font-weight:850; letter-spacing:.3px; }
QLabel#PageTitle { font-size:17px; font-weight:750; }
QLabel#Title { font-size:13px; font-weight:750; }
QLabel#Muted { color:#97a5b8; font-size:11px; }
QLabel#Tiny { color:#97a5b8; font-size:10px; }
QLabel#BadgeSB { color:#d5c0ff; background:#372b52; padding:2px 6px; border-radius:5px; font-weight:800; }
QLabel#BadgeRNK { color:#ffc79e; background:#4d3327; padding:2px 6px; border-radius:5px; font-weight:800; }
QLabel#Kpi { color:#f1b46f; font-size:17px; font-weight:800; }
QPushButton { background:#253246; border:1px solid #354357; border-radius:8px; padding:7px 12px; font-weight:600; }
QPushButton:hover { background:#314158; border-color:#6e86a4; }
QPushButton:focus { border:2px solid #8ac9ed; }
QPushButton:pressed { background:#182233; }
QPushButton:disabled { color:#69798d; background:#1c2634; border-color:#283547; }
QPushButton#Accent { background:#f1b46f; color:#171d27; border:1px solid #f1b46f; font-weight:800; }
QPushButton#Accent:hover { background:#ffca8d; }
QPushButton#Success { background:#285347; color:#b0f6d9; border:1px solid #3b876f; }
QPushButton#Danger { background:#4c2931; color:#ffd1d2; border:1px solid #7b424d; }
QPushButton#Nav { background:transparent; border:none; border-bottom:3px solid transparent; border-radius:0; padding:12px 18px; color:#a7b6ca; font-size:12px; }
QPushButton#Nav:checked { color:#f1b46f; background:#202936; border-bottom:3px solid #f1b46f; }
QPushButton#Segment { background:#1e2938; border:1px solid #344154; border-radius:8px; }
QPushButton#Segment:checked { color:#f1b46f; border-color:#f1b46f; background:#362d2a; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit { background:#131c29; border:1px solid #364358; border-radius:7px; padding:7px 8px; selection-background-color:#a66e39; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus { border-color:#f1b46f; }
QComboBox::drop-down { width:21px; border:none; }
QComboBox QAbstractItemView { background:#202b3a; color:#e9eef7; selection-background-color:#424457; border:1px solid #4b5a6d; }
QCheckBox { color:#c5d0dd; spacing:5px; }
QCheckBox::indicator { width:16px; height:16px; }
QCheckBox::indicator:unchecked { background:#142030; border:1px solid #53637b; border-radius:3px; }
QCheckBox::indicator:checked { background:#f1b46f; border:1px solid #f1b46f; border-radius:3px; image:none; }
QScrollArea, QScrollArea>QWidget>QWidget { border:none; background:transparent; }
QScrollBar:vertical { width:9px; background:#141d2a; }
QScrollBar::handle:vertical { background:#3b4a5e; border-radius:4px; min-height:20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar:horizontal { height:9px; background:#141d2a; }
QScrollBar::handle:horizontal { background:#3b4a5e; border-radius:4px; min-width:20px; }
QProgressBar { border:none; background:#2a3648; height:6px; border-radius:3px; text-align:center; }
QProgressBar::chunk { border-radius:3px; background:#6acbaa; }
QCalendarWidget QWidget { background:#1a2230; color:#e9eef7; }
QCalendarWidget QToolButton { background:#1e2938; border:none; }
QCalendarWidget QSpinBox { background:#1a2230; }
QCalendarWidget QAbstractItemView { background:#172131; color:#e9eef7; selection-background-color:#f1b46f; selection-color:#172131; }
QMenu { background:#253246; border:1px solid #4a5870; padding:4px; }
QMenu::item { padding:7px 16px; color:#e9eef7; }
QMenu::item:selected { background:#40536d; color:#f1b46f; }
QTabWidget::pane { border:1px solid #344154; border-radius:9px; background:#141d2b; }
QTabBar::tab { background:#223044; color:#aebbd0; padding:10px 20px; border:1px solid #344154; border-bottom:0; }
QTabBar::tab:selected { background:#34313a; color:#f1b46f; border-color:#f1b46f; }
QToolTip { background:#253246; color:#e9eef7; border:1px solid #536581; padding:5px; }
QMessageBox { background:#1a2230; }

/* Katalog V4.1 - eski Flet yerlesiminden uyarlanmis kompakt panel */
QFrame#BasketPanel { background:#191b28; border:1px solid #343043; border-radius:12px; }
QFrame#CatalogToolbar { background:#171b2b; border:1px solid #2b3550; border-radius:9px; }
QFrame#BookHead { background:#222029; border:1px solid #37303b; border-radius:6px; }
QLabel#BookName { font-size:10px; font-weight:800; color:#f0ebf0; }
QLabel#BookPages { font-size:9px; font-weight:700; color:#edb26e; }
QCheckBox#BookSelect { font-size:10px; color:#a5a1b5; }
QFrame#Card { background:#1b253c; border:1px solid #30436a; border-radius:9px; }
QFrame#Card:hover { border:1px solid #efae68; }
QFrame#BasketGroup { background:#24222d; border:2px solid #514955; border-radius:9px; }
QLabel#BasketGroupTitle { color:#ffba77; font-size:11px; font-weight:800; }
QFrame#BasketRow { background:#211f2a; border:1px solid #39323d; border-radius:6px; }
QFrame#BasketTotals { background:transparent; border-top:1px solid #3a3444; }
QPushButton#DangerText { color:#ff8597; background:transparent; border:0; padding:4px; }
QPushButton#QuickSB { background:#4d4478; border-color:#635c8f; color:#e7dbff; }
QPushButton#QuickRNK { background:#a96649; border-color:#c17a55; color:#fff0e4; }
QPushButton#OrderType { background:#302c3b; color:#b9b2c0; padding:7px; }
QPushButton#OrderType:checked { background:#4d4276; color:white; border-color:#66538c; }
QPushButton#Success { background:#75d7ad; color:#132a21; border-color:#75d7ad; font-weight:850; }
'''


QSS += """
/* V4.3 - flat header and centered navigation underline */
QFrame#Header { background:#141923; border:0; border-top:2px solid #e4aa68; border-bottom:1px solid #2a3545; border-radius:0; }
QPushButton#Nav { background:transparent; border:0; border-bottom:2px solid transparent; border-radius:0; padding:13px 17px; }
QPushButton#Nav:hover { background:#1b2532; color:#f1b46f; }
QPushButton#Nav:checked { background:transparent; border-bottom:2px solid #f1b46f; }
QMenu#OrdersHoverMenu { background:#1a2230; border:1px solid #3c4759; border-top:2px solid #f1b46f; padding:2px 0; }
QMenu#OrdersHoverMenu::item { padding:11px 17px; }
QMenu#OrdersHoverMenu::item:selected { background:#30394a; }
/* Portrait cards: only the cover image occupies the visual center */
QFrame#PortraitBookCard { background:#1b2536; border:1px solid #29384c; border-radius:8px; }
QFrame#PortraitBookCard:hover { border-color:#c68e5e; }
QLabel#PortraitBookName { font-size:11px; font-weight:750; color:#f2edf3; background:transparent; }
QLabel#PortraitBookPages { font-size:10px; color:#e6ae73; background:transparent; }
QLabel#PortraitCover { border:0; background:transparent; }
QFrame#QuantityPill { background:#121b2a; border:1px solid #344258; border-radius:13px; }
QLabel#PillSB { color:#c5b0f2; font-weight:800; font-size:10px; background:transparent; }
QLabel#PillRNK { color:#f6b18b; font-weight:800; font-size:10px; background:transparent; }
QPushButton#PillStep { background:#303e55; border:0; border-radius:12px; padding:0; font-size:15px; font-weight:700; }
QPushButton#PillStep:hover { background:#4b5b76; }
QSpinBox#PillQuantity { background:transparent; border:0; padding:0; font-weight:800; font-size:11px; }
/* Reduced basket chrome */
QFrame#BasketPanel { background:#191e2a; border:0; border-left:1px solid #344154; border-radius:0; }
QFrame#BasketGroup { background:transparent; border:0; border-bottom:1px solid #344154; border-radius:0; }
QFrame#BasketRow { background:transparent; border:0; border-radius:0; }
QFrame#CatalogToolbar { background:transparent; border:0; border-radius:0; }
QWidget#FloatingPrice { background:transparent; border:0; }
QLineEdit#FloatingPriceInput { background:rgba(20,26,38,0.32); border:1px solid #514656; border-radius:8px; padding:18px 12px 3px; font-size:13px; color:#f2e8ee; }
QLineEdit#FloatingPriceInput:focus { background:rgba(24,30,43,0.46); border-color:#f1b46f; }
QLabel#FloatingPriceLabel { background:transparent; border:0; }
"""

QSS += """
/* V4.4: dar kartlar, çerçevesiz kapak, yatay mini sayaçlar */
QFrame#CompactBookCard { background:#1b2536; border:1px solid #2c3a50; border-radius:7px; }
QFrame#CompactBookCard:hover { border-color:#e2a764; }
QLabel#CompactBookName { color:#f4f5fa; font-size:10px; font-weight:750; background:transparent; }
QLabel#CompactBookPages { color:#e7ac6e; font-size:9px; background:transparent; }
QLabel#CompactBookCover { background:transparent; border:0; padding:0; }
QFrame#MiniQuantity { background:#121a29; border:1px solid #35445c; border-radius:11px; }
QLabel#MiniSB { color:#cbb9fc; font-size:9px; font-weight:800; background:transparent; }
QLabel#MiniRNK { color:#ffb58a; font-size:9px; font-weight:800; background:transparent; }
QPushButton#MiniStep { background:#303f56; border:0; border-radius:8px; padding:0; font-size:12px; font-weight:800; }
QPushButton#MiniStep:hover { background:#50647d; }
QSpinBox#MiniValue { background:transparent; border:0; padding:0; font-size:10px; font-weight:700; }
QWidget#CatalogToolbar { background:transparent; border:0; }
QWidget#CatalogToolbar QLineEdit { min-height:24px; }
QWidget#CatalogToolbar QPushButton { padding:7px 8px; }
"""

QSS += """
/* V4.5: standalone kitap kapakları ve okunabilir sayaçlar */
QWidget#StandaloneBook { background: transparent; border: none; }
QLabel#StandaloneName { color: #f4f5fa; font-size: 10px; font-weight: 750; background: transparent; border: none; }
QLabel#StandalonePages { color: #e7ac6e; font-size: 9px; background: transparent; border: none; }
QLabel#StandaloneCover { background: transparent; border: none; border-radius: 0; padding: 0; }
QWidget#StandaloneMedia { background: transparent; border: none; }
QWidget#StandaloneQuantities { background: transparent; border: none; }
QWidget#StandaloneCounter { background: #172131; border: none; border-radius: 0px; }
QLabel#StandaloneSB { color: #cbb9fc; font-size: 9px; font-weight: 800; background: transparent; }
QLabel#StandaloneRNK { color: #ffb58a; font-size: 9px; font-weight: 800; background: transparent; }
QLabel#StandaloneCount { color: #ffffff; font-size: 11px; font-weight: 800; background: transparent; padding: 0; }
QPushButton#StandaloneStep { background: #30415b; color: white; border: none; border-radius: 0px; padding: 0; font-size: 13px; font-weight: 800; }
QPushButton#StandaloneStep:hover { background: #536681; }
QPushButton#StandaloneStep:disabled { color: #5b6574; background: #222a36; }
"""

QSS += """
/* V4.7: başlık/kapak/sayaç tek dikey bütün, keskin köşeler. */
QWidget#StandaloneHeader { background:#1c2738; border:0; border-radius:0; }
QWidget#StandaloneCounterSB { background:#453a69; border:0; border-radius:0; }
QWidget#StandaloneCounterRNK { background:#98583e; border:0; border-radius:0; }
QWidget#StandaloneCounterSB QLabel#StandaloneSB { color:#f1e9ff; }
QWidget#StandaloneCounterRNK QLabel#StandaloneRNK { color:#fff1e7; }
QWidget#StandaloneCounterSB QPushButton#StandaloneStep { background:#625388; color:white; border-radius:0; }
QWidget#StandaloneCounterRNK QPushButton#StandaloneStep { background:#b87452; color:white; border-radius:0; }
QWidget#StandaloneCounterSB QPushButton#StandaloneStep:hover { background:#806da9; }
QWidget#StandaloneCounterRNK QPushButton#StandaloneStep:hover { background:#d28c65; }
QWidget#StandaloneCounterSB QPushButton#StandaloneStep:disabled,
QWidget#StandaloneCounterRNK QPushButton#StandaloneStep:disabled { background:#30333d; color:#777d8a; }
"""

QSS += """
/* V4.8 - daha büyük kapak, daha ince bantlar, sayaçlar arasında nefes alanı */
QWidget#StandaloneHeader { background:#1c2738; border:0; border-radius:0; }
QLabel#StandaloneName { font-size:10px; font-weight:750; padding:0; margin:0; }
QLabel#StandalonePages { font-size:9px; padding:0; margin:0; }
QWidget#StandaloneCounterSB { background:#453a69; border:0; }
QWidget#StandaloneCounterRNK { background:#98583e; border:0; }
QLabel#StandaloneCount { font-size:11px; font-weight:800; padding:0; }
QPushButton#StandaloneStep { padding:0; margin:0; font-size:12px; }
"""

QSS += """
/* V4.9: V4.8 boyutlarına dokunmadan, mat altın çerçeve ve bölüm ayraçları. */
QWidget#StandaloneHeader {
    background: #1c2738;
    border: 1px solid #b98d51;
    border-radius: 0;
}
QWidget#StandaloneQuantities {
    background: transparent;
    border-left: 1px solid #b98d51;
    border-right: 1px solid #b98d51;
    border-bottom: 1px solid #b98d51;
    border-top: 0;
    border-radius: 0;
}
"""

QSS += """
/* V4.10: altın yerine koyu mavi-gri çizgiler, ince birleşik sayaçlar. */
QWidget#StandaloneHeader { border: 1px solid #45546a; background:#1c2738; }
QWidget#StandaloneQuantities { border: 1px solid #45546a; border-top:0; background:transparent; }
QWidget#StandaloneCounterSB { border:0; border-right:1px solid #45546a; background:#453a69; }
QWidget#StandaloneCounterRNK { border:0; background:#98583e; }
QWidget#StandaloneCounterSB QPushButton#StandaloneStep,
QWidget#StandaloneCounterRNK QPushButton#StandaloneStep { min-height:0; max-height:23px; padding:0; }
"""

QSS += """
/* V4.11: 19px sayaç bandı, SB/RNK arasında görünür tek çizgi. */
QWidget#StandaloneQuantities { border: 1px solid #45546a; border-top:0; background:transparent; }
QWidget#StandaloneCounterSB { background:#453a69; border:0; border-right:2px solid #8291aa; border-radius:0; }
QWidget#StandaloneCounterRNK { background:#98583e; border:0; border-radius:0; }
QWidget#StandaloneCounterSB QPushButton#StandaloneStep,
QWidget#StandaloneCounterRNK QPushButton#StandaloneStep { min-height:0; max-height:19px; padding:0; font-size:11px; }
QLabel#StandaloneCount { font-size:10px; padding:0; }
QLabel#StandaloneSB, QLabel#StandaloneRNK { font-size:9px; padding:0; }
"""

QSS += """
QFrame#StandaloneCounterDivider { background:#9daec3; border:0; }
QWidget#StandaloneCounterSB { border:0; background:#453a69; }
QWidget#StandaloneCounterRNK { border:0; background:#98583e; }
QWidget#BasketPillSB { background:#453a69; border:1px solid #6b5b95; border-radius:8px; }
QWidget#BasketPillRNK { background:#98583e; border:1px solid #c7825e; border-radius:8px; }
QLabel#BasketPillText, QLabel#BasketPillCount { color:white; font-size:10px; font-weight:700; }
QPushButton#BasketPillStep { background:rgba(255,255,255,0.12); color:white; border:0; border-radius:4px; padding:0; font-weight:700; }
QPushButton#BasketPillStep:hover { background:rgba(255,255,255,0.28); }
"""

QSS += """
/* V4.13 — Siparişler: ince filtre şeridi, modern durum satırları ve kartlı takip */
QFrame#OrderToolbar {
    background: #171f2b;
    border: 1px solid #354359;
    border-radius: 9px;
}
QFrame#OrderToolbar QLineEdit, QFrame#OrderToolbar QComboBox {
    background: #111a28;
    border: 1px solid #354359;
    border-radius: 6px;
    padding: 7px 9px;
    min-height: 25px;
}
QFrame#OrderToolbar QLineEdit:focus, QFrame#OrderToolbar QComboBox:focus {
    border: 1px solid #8496b4;
}
QLabel#OrderSection { color:#f1b46f; font-weight:800; letter-spacing:.4px; font-size:11px; }
QLabel#OrderMetrics { color:#b1bfd0; font-weight:650; font-size:11px; }
QPushButton#CalendarTrigger { background:#253349; color:#e4eaf5; }
QPushButton#OrderReset { background:transparent; border:1px solid #45556c; min-width:28px; }
QFrame#OrderBulk { background:#171f2b; border:1px solid #354359; border-radius:6px; }
QFrame#OrderRow {
    background:#222632;
    border:1px solid #454656;
    border-radius:10px;
}
QFrame#OrderRow:hover { border:1px solid #7d8fa8; }
QLabel#OrderID { font-size:17px; font-weight:900; color:#ffffff; }
QLabel#OrderPlatform {
    color:#f5ecff; background:#67508a;
    font-size:10px; font-weight:800; padding:4px 7px;
    border-radius:5px;
}
QLabel#OrderMeta { color:#e4e9ef; font-size:11px; font-weight:650; }
QLabel#OrderMoney { color:#6edab5; font-size:12px; font-weight:800; }
QLabel#OrderQuantity { color:#f2b86d; font-size:11px; font-weight:800; }
QPushButton#CopyCode {
    background:#171923; text-align:left; border:1px solid #424554;
    border-radius:6px; font-size:12px; font-weight:750;
    padding:8px 9px; color:#f0f2f6;
}
QPushButton#CopyCode:hover { border-color:#8c9fb8; }
QWidget#OrderCovers { background:transparent; border:0; }
QScrollArea#OrderCoverScroll { background:transparent; border:0; }
QScrollArea#OrderCoverScroll QWidget#qt_scrollarea_viewport { background:transparent; }
QProgressBar#ReadyProgress, QProgressBar#BoxProgress {
    border:0; border-radius:2px; background:#131923;
}
QProgressBar#ReadyProgress::chunk { background:#589ee5; border-radius:2px; }
QProgressBar#BoxProgress::chunk { background:#61c9a0; border-radius:2px; }
QPushButton#SmallAction {
    background:#293449; border:1px solid #56647b;
    color:#f6d6a7; padding:6px 8px;
}
QPushButton#PdfAction {
    background:#283a50; border:1px solid #5279a0;
    border-radius:6px; color:#c1e2ff;
    font-size:11px; font-weight:800; padding:6px 10px;
}
QPushButton#PdfAction:hover { background:#35516e; border-color:#86bbf0; }
QDialog#DatePickerDialog {
    background:#161f2b; border:1px solid #526378;
}
QCalendarWidget#OrderCalendar { background:#1b2636; color:#e7edf5; }
QCalendarWidget#OrderCalendar QWidget#qt_calendar_navigationbar { background:#28364b; }
QCalendarWidget#OrderCalendar QAbstractItemView:enabled {
    selection-background-color:#476a92; selection-color:white;
    background:#182233; color:#ecf2fa;
    border:0; outline:0;
}
QLabel#DateLegend { color:#f1b46f; font-size:10px; }
QWidget#TrackGridBody { background:transparent; }
QFrame#TrackBookCard {
    background:#1d2838; border:1px solid #40516a;
    border-radius:8px;
}
QFrame#TrackBookCard:hover { border-color:#7897b8; }
QLabel#TrackCode { color:#e8b678; font-weight:800; font-size:11px; }
QLabel#TrackBookName { color:#f7f8fb; font-weight:800; font-size:11px; }
QLabel#TrackBookInfo { color:#9eacc0; font-size:10px; }
QFrame#VariantSB { background:#24233c; border:1px solid #4f476c; border-radius:5px; }
QFrame#VariantRNK { background:#3b2c2a; border:1px solid #6b493f; border-radius:5px; }
QLabel#VariantCaption { color:#c5cedb; font-size:9px; font-weight:650; }
QScrollArea#CopiesScroll { background:transparent; border:0; }
QScrollArea#CopiesScroll QWidget#qt_scrollarea_viewport { background:transparent; }
QCheckBox#CopyCheck { spacing:0px; }
QCheckBox#CopyCheck::indicator { width:13px; height:13px; }
"""

QSS += """
/* V4.14-prep: sipariş kartlarında büyük kapak ve sade aksiyonlar */
QLabel#OrderPlatformDone {
    color:#d8fff0; background:#355b53;
    font-size:10px; font-weight:800; padding:4px 7px;
    border-radius:5px;
}
QPushButton#DetailAction {
    background:#293449; border:1px solid #56647b;
    color:#edf3fb; padding:7px 10px; font-weight:750;
}
QPushButton#DetailAction:hover { border-color:#8ea1ba; background:#33455e; }
QToolButton#MoreActions {
    background:#243145; border:1px solid #52637b; border-radius:8px;
    padding:7px 10px; color:#e8eef7; font-weight:900; min-width:34px;
}
QToolButton#MoreActions:hover { background:#31445d; border-color:#8ea1ba; }
QLabel#OrderMoreBooks {
    color:#dbe6f3; background:#192233; border:1px dashed #50627c;
    border-radius:8px; font-size:16px; font-weight:800;
}
QFrame#TrackBookCard {
    background:#1d2838; border:1px solid #40516a; border-radius:8px;
}
QFrame#TrackBookCard:hover { border-color:#7897b8; }
QLabel#TrackBookName { color:#f7f8fb; font-weight:800; font-size:13px; }
QLabel#TrackBookInfo { color:#9eacc0; font-size:10px; }
QFrame#VariantSB, QFrame#VariantRNK { border-radius:7px; }
QFrame#VariantSB { background:#24233c; border:1px solid #4f476c; }
QFrame#VariantRNK { background:#3b2c2a; border:1px solid #6b493f; }
QLabel#VariantCaption { color:#d0d8e4; font-size:10px; font-weight:700; }
"""

QSS += """
/* V4.15 — Premium, ince sipariş filtre şeridi */
QFrame#OrderToolbar {
    background:#182130; border:1px solid #314157; border-radius:9px;
}
QFrame#OrderToolbar QLineEdit#OrderSearch {
    background:#101a29; border:1px solid #40516a; border-radius:7px;
    padding:8px 12px; min-height:25px; font-size:12px;
}
QFrame#OrderToolbar QLineEdit#OrderSearch:focus {
    border-color:#8ba5c7; background:#152236;
}
QFrame#OrderToolbar QComboBox#OrderFilter {
    background:#202d41; border:1px solid #40516a; border-radius:7px;
    min-height:25px; padding:7px 10px; color:#dce6f3;
}
QFrame#OrderToolbar QComboBox#OrderFilter:hover { border-color:#7891ae; }
QLabel#OrderSection { color:#ebf2fa; font-size:12px; font-weight:850; letter-spacing:.3px; }
QLabel#OrderMetrics {
    color:#b4c5da; font-size:11px; font-weight:650;
    background:transparent;
}
QPushButton#CalendarTrigger {
    background:#2c3a50; border:1px solid #526682; color:#deebf8;
    padding:7px 12px; border-radius:7px;
}
QPushButton#CalendarTrigger:hover { border-color:#8aabd0; background:#384c67; }
QPushButton#OrderReset { background:#232f42; border:1px solid #465a74; border-radius:7px; }
QFrame#OrderBulk {
    background:transparent; border:0; border-bottom:1px solid #34465c; border-radius:0;
}
/* Kompakt sipariş kartı: büyük kapak, tek satır aksiyon */
QFrame#OrderRow {
    background:#1a2636; border:1px solid #3b4c64; border-radius:9px;
}
QFrame#OrderRow:hover { border-color:#7b94b4; }
QFrame#OrderRow[orderStatus="tamamlandi"] {
    background:#1a2a2d; border:1px solid #39645c;
}
QFrame#OrderRow[orderStatus="havuz"] { border-left:3px solid #9c7e57; }
QFrame#OrderRow[orderStatus="aktif"] { border-left:3px solid #577da5; }
QFrame#OrderRow[orderStatus="tamamlandi"] { border-left:3px solid #68c7a2; }
QLabel#OrderDoneTag {
    color:#bdf5e1; background:#245046; border:1px solid #478c77;
    padding:8px 5px; border-radius:7px; font-size:11px; font-weight:800;
}
QLabel#OrderDoneDate { color:#71cda9; font-size:10px; font-weight:750; }
QPushButton#DetailAction { color:#e7effa; padding:8px 8px; }
QToolButton#MoreActions { min-width:28px; padding:8px 5px; }
QMenu#OrderActionsMenu { background:#1d2a3c; border:1px solid #536783; padding:5px; }
QMenu#OrderActionsMenu::item { padding:9px 20px; }
QMenu#OrderActionsMenu::item:selected { background:#38516b; color:#ffffff; }
QMenu#OrderActionsMenu::separator { height:1px; background:#526077; margin:4px 6px; }
/* Kompakt ve ayrı sipariş düzenleme penceresi */
QDialog#OrderEditWindow, QDialog#OrderTrackWindow { background:#101720; }
QFrame#OrderEditPanel { background:#1b283a; border:1px solid #3b526e; border-radius:9px; }
QLabel#OrderEditSection { color:#e1eaf6; font-size:11px; font-weight:850; letter-spacing:.4px; }
QLabel#OrderEditPlatform {
    background:#22364a; border:1px solid #405f7e; border-radius:7px;
    color:#aed9f6; font-size:12px; font-weight:800; padding:8px 12px;
}
QFrame#OrderEditBookRow { background:#1c2939; border:1px solid #374b63; border-radius:8px; }
QFrame#OrderEditBookRow:hover { border-color:#65819e; }
QLabel#OrderEditBookName { color:#f2f6fb; font-size:12px; font-weight:750; }
QComboBox#OrderBookSearch { background:#132133; border:1px solid #485e78; }
QFrame#TrackBookCard { background:#1b2a3b; border:1px solid #3b536b; border-radius:8px; }
QFrame#TrackBookCard:hover { border-color:#7698b7; }
"""

QSS += """
/* V4.17: sipariş detay penceresi daha küçük popup, 3 kolon kart ve sağda büyük kapak. */
QFrame#TrackBookCard {
    background: #172334;
    border: 1px solid #32465d;
    border-radius: 8px;
}
QFrame#TrackBookCard:hover { border-color: #5f7d9b; }
QWidget#TrackSelectZone, QWidget#TrackControlZone, QWidget#TrackCoverZone {
    background: transparent; border: 0; padding: 0;
}
QFrame#TrackZoneDivider { background:#34475f; border:0; }
QLabel#TrackCode {
    font-size:12px; font-weight:900; color:#f0b86a;
    background:#223348; border:1px solid #40546d; border-radius:5px; padding:4px 8px;
}
QLabel#TrackBookName { font-size:12px; font-weight:850; color:#f4f7fd; }
QLabel#TrackBookInfo { font-size:9px; color:#a9b8ca; }
QFrame#TrackVariantSB {
    background: #27233d; border:1px solid #594d83; border-radius:6px;
}
QFrame#TrackVariantRNK {
    background: #3f2d2a; border:1px solid #86513f; border-radius:6px;
}
QLabel#TrackVariantTitleSB { color:#d8c9ff; font-size:10px; font-weight:900; }
QLabel#TrackVariantTitleRNK { color:#ffbf98; font-size:10px; font-weight:900; }
QLabel#TrackVariantAmount { color:#c4cede; font-size:9px; }
QLabel#TrackStepLabel { color:#ced8e8; font-size:9px; font-weight:800; }
QLabel#TrackStepCount {
    color:#f4f7fc; font-size:10px; font-weight:900;
    background:#1d2633; border:1px solid #35475e; border-radius:4px; padding:2px 4px;
}
QPushButton#TrackStep {
    background:#384a60; color:#f6f8ff; border:1px solid #59718f;
    border-radius:4px; padding:0; margin:0;
    min-width:0; min-height:0; font-size:12px; font-weight:900;
}
QPushButton#TrackStep:hover { background:#5f7693; border-color:#abc0d9; }
QPushButton#TrackStep:pressed { background:#28384b; }
QPushButton#TrackStep:disabled {
    background:#283341; color:#657486; border-color:#334254;
}
QPushButton#TrackPdfButton {
    background:#213b55; color:#d5ebff; border:1px solid #4d7497;
    border-radius:5px; padding:6px 5px; min-height:0;
    font-size:10px; font-weight:850;
}
QPushButton#TrackPdfButton:hover { background:#305270; border-color:#88b8e4; }
"""


QSS += """
/* V4.18 — sipariş listesi: kompakt filtre segmenti ve 3 parçalı yatay kart */
QFrame#OrderToolbar {
    background:#141d2a; border:1px solid #2c3b4f; border-radius:8px;
}
QFrame#OrderFilterSegment {
    background:#1c2939; border:1px solid #3b4c63; border-radius:8px;
}
QToolButton#OrderSortReverse {
    background:#253549; border:1px solid #50647f; border-radius:6px;
    color:#e7eef8; min-width:28px; min-height:28px; font-weight:900;
}
QToolButton#OrderSortReverse:hover { background:#334963; border-color:#89a6ca; }
QPushButton#OrderReset {
    background:#253549; border:1px solid #50647f; border-radius:6px;
    color:#d7e3f2; padding:6px 10px;
}
QFrame#OrderRow {
    background:#182434; border:1px solid #36485f; border-radius:8px;
}
QFrame#OrderRow:hover { border-color:#6e8dac; }
QWidget#OrderCovers { background:transparent; border:0; }
QWidget#OrderMiniCoverCard { background:transparent; border:0; }
QLabel#OrderQtyBadge {
    background:rgba(17,25,37,0.92); border:1px solid #6b89ad; border-radius:8px;
    color:#eff5fc; font-size:10px; font-weight:900; padding:2px 6px; min-width:12px;
}
QLabel#MiniBadgeSB {
    color:#ece7ff; background:rgba(76,61,122,0.95); border:1px solid #7562b0;
    border-radius:5px; font-size:8px; font-weight:800; padding:1px 5px;
}
QLabel#MiniBadgeRNK {
    color:#ffe3d0; background:rgba(111,68,50,0.95); border:1px solid #b06e52;
    border-radius:5px; font-size:8px; font-weight:800; padding:1px 5px;
}
QLabel#OrderMoreBooks {
    color:#dce8f7; background:#1a2534; border:1px dashed #50627c; border-radius:8px;
    font-size:12px; font-weight:800; min-width:86px; min-height:126px;
}
QPushButton#DetailAction {
    background:#253549; border:1px solid #556983; border-radius:7px;
    color:#edf3fb; padding:8px 10px; font-weight:800;
}
QPushButton#DetailAction:hover { background:#31465f; border-color:#8ca7c6; }
QToolButton#MoreActions {
    background:#243145; border:1px solid #52637b; border-radius:7px;
    padding:8px 8px; color:#e8eef7; font-weight:900; min-width:32px;
}
QToolButton#MoreActions:hover { background:#31445d; border-color:#8ea1ba; }
"""

QSS += """
/* V4.19 — Üst navigasyon: logo yok, merkezî büyük sekmeler ve ikinci yatay bar. */
QFrame#Header {
    background:#131c28; border:0; border-top:2px solid #b77f51;
    border-bottom:1px solid #34475d; border-radius:0;
}
QPushButton#Nav {
    background:transparent; border:0; border-bottom:3px solid transparent;
    border-radius:0; padding:12px 25px; font-size:15px;
    font-weight:800; color:#c1d1e4;
}
QPushButton#Nav:hover { background:#1c2a3b; color:#fff0dd; }
QPushButton#Nav:checked {
    border-bottom:3px solid #f1b46f; color:#f8c48b;
    background:transparent;
}
QFrame#OrdersSubbar {
    background:#192637; border:0; border-bottom:1px solid #364b62;
    border-radius:0;
}
QPushButton#OrdersSubnav {
    background:transparent; border:0; border-bottom:2px solid transparent;
    border-radius:0; padding:9px 19px; min-height:30px;
    font-size:12px; font-weight:800; color:#aebed1;
}
QPushButton#OrdersSubnav:hover { color:#eff4fc; background:#26364a; }
QPushButton#OrdersSubnav:checked {
    border-bottom:2px solid #f1b46f; color:#f5bc83;
    background:#253449;
}

/* Tek yüksekliği olan filtre kontrolleri ve alt satırda kompakt özet. */
QFrame#OrderToolbar {
    background:#152132; border:1px solid #304258;
    border-radius:8px;
}
QFrame#OrderToolbar QLineEdit#OrderSearch {
    background:#101c2a; border:1px solid #3b516c; border-radius:6px;
    padding:6px 11px; min-height:0; max-height:36px; font-size:12px;
}
QFrame#OrderToolbar QLineEdit#OrderSearch:focus { border-color:#8daacf; }
QFrame#OrderFilterSegment {
    background:#1b2b3d; border:1px solid #3b526e;
    border-radius:7px;
}
QFrame#OrderToolbar QComboBox#OrderFilter {
    background:#25364c; border:1px solid #4a617b;
    border-radius:5px; padding:4px 7px; min-height:0; max-height:36px;
    font-size:11px; font-weight:700;
}
QPushButton#CalendarTrigger, QPushButton#OrderReset {
    background:#26384d; color:#eef4fb; border:1px solid #516b89;
    border-radius:5px; padding:4px 7px; min-height:0; max-height:36px;
    font-size:11px; font-weight:750;
}
QToolButton#OrderSortReverse {
    background:#26384d; color:#eef4fb; border:1px solid #516b89;
    border-radius:5px; padding:0; font-size:17px; font-weight:900;
}
QToolButton#OrderSortReverse:hover, QPushButton#CalendarTrigger:hover,
QPushButton#OrderReset:hover { background:#36506d; border-color:#88a7ca; }
QLabel#OrderMetrics { color:#bacbde; font-size:11px; font-weight:750; }
QLabel#OrderSelectedCount {
    background:#2d4058; color:#edf5ff; border:1px solid #55708c;
    border-radius:6px; padding:4px 9px; font-size:11px; font-weight:800;
}
QFrame#OrderRow { background:#1b2a3d; border:1px solid #41536b; border-radius:8px; }
QFrame#OrderRow:hover { border:1px solid #87a1bf; }
QFrame#OrderRow[orderSelected="true"] {
    border:2px solid #79aafa; background:#1d344e;
}
QFrame#OrderRow[orderFocused="true"] {
    border:2px solid #e5b878; background:#263348;
}
QLabel#OrderSelectedTag {
    color:#d4e8ff; background:#315783; border:1px solid #71a4da;
    border-radius:5px; padding:2px 5px; font-size:9px; font-weight:900;
}
QScrollArea#OrderCoverScroll, QWidget#OrderCovers {
    background:transparent; border:0;
}
QScrollArea#OrderCoverScroll QWidget#qt_scrollarea_viewport {
    background:transparent; border:0;
}
QScrollBar:horizontal { height:7px; background:#152132; }
QScrollBar::handle:horizontal { background:#56718e; border-radius:3px; }

/* Sipariş takip detayının iki çift ana işlemi. */
QFrame#TrackActionReady {
    background:#232940; border:1px solid #57577c; border-radius:7px;
}
QFrame#TrackActionBoxed {
    background:#1f3941; border:1px solid #47797a; border-radius:7px;
}
QLabel#TrackActionLabel { color:#becddf; font-size:9px; font-weight:900; }
QPushButton#TrackBulkPositive, QPushButton#TrackBulkNegative {
    padding:5px 8px; border-radius:5px; min-height:0;
    font-size:11px; font-weight:850;
}
QPushButton#TrackBulkPositive {
    background:#427f70; border:1px solid #66ac93; color:#f1fff9;
}
QPushButton#TrackBulkPositive:hover { background:#509b84; }
QPushButton#TrackBulkNegative {
    background:#354357; border:1px solid #5c708a; color:#edf3fa;
}
QPushButton#TrackBulkNegative:hover { background:#49627f; }
QPushButton#TrackBulkPositive:disabled, QPushButton#TrackBulkNegative:disabled {
    background:#27313d; color:#8392a5; border-color:#3b4a59;
}

/* Yeni kitap bazlı baskı havuzu: büyük okunabilir adetler, tıklanabilir siparişler. */
QFrame#BookPoolToolbar {
    background:#172538; border:1px solid #354d67; border-radius:8px;
}
QLabel#BookPoolTitle { color:#e6edf8; font-size:14px; font-weight:900; }
QFrame#PoolBookRow {
    background:#1b2a3c; border:1px solid #354b65; border-radius:9px;
}
QFrame#PoolBookRow:hover { border-color:#7398c1; }
QLabel#PoolBookName { color:#f1f5fa; font-size:12px; font-weight:850; }
QFrame#PoolStat {
    background:#233348; border:1px solid #405670; border-radius:6px;
    min-width:77px;
}
QPushButton#PoolOrderLink {
    background:#304864; border:1px solid #527caa; border-radius:6px;
    color:#e3f0ff; font-size:10px; font-weight:850;
    padding:4px 7px; min-height:0;
}
QPushButton#PoolOrderLink:hover { background:#46698e; border-color:#87b5e8; }
QScrollArea#PoolLinksScroll, QScrollArea#PoolLinksScroll QWidget#qt_scrollarea_viewport {
    background:transparent; border:0;
}
"""

QSS += """
/* V4.20 — kompakt sipariş arayüzü ve takvim düzeltmeleri */
QFrame#Header { min-height:52px; max-height:52px; }
QPushButton#Nav {
    font-size:18px; font-weight:800; padding:8px 16px;
    min-height:34px;
}
QFrame#OrdersSubbar {
    min-height:34px; max-height:34px;
    background:#141c28; border-top:1px solid #243246; border-bottom:1px solid #243246;
}
QPushButton#OrdersSubnav {
    min-height:26px; padding:4px 10px; font-size:12px; font-weight:750;
}
QFrame#OrderToolbar { border-radius:8px; }
QFrame#OrderFilterSegment {
    background:#1d2938; border:1px solid #3b4c63; border-radius:9px;
}
QComboBox#OrderFilter, QToolButton#OrderSortReverse, QPushButton#CalendarTrigger, QPushButton#OrderReset {
    min-height:32px; max-height:32px;
}
QToolButton#OrderSortReverse {
    background:#253349; color:#e4eef8; border:1px solid #44576f; border-radius:6px;
    font-size:14px; font-weight:800;
}
QToolButton#OrderSortReverse:hover { background:#314662; }
QComboBox#OrderFilter QAbstractItemView,
QFrame#OrderToolbar QComboBox QAbstractItemView {
    background:#1a2330; color:#f2f6fb; border:1px solid #465970; outline:0;
    selection-background-color:#9c6937; selection-color:#ffffff; padding:4px;
}
QFrame#OrderToolbar QComboBox::drop-down { width:24px; border:0; }
QFrame#OrderToolbar QComboBox::down-arrow { width:10px; height:10px; }
QDialog#DatePickerDialog {
    background:#141c28; border:1px solid #44576f; border-radius:12px;
}
QCalendarWidget#OrderCalendar {
    background:#172232; border:1px solid #31445b; border-radius:10px;
}
QCalendarWidget#OrderCalendar QWidget#qt_calendar_navigationbar {
    background:#253549; min-height:32px;
}
QCalendarWidget#OrderCalendar QToolButton {
    color:#f4f8fd; font-size:18px; font-weight:800; background:transparent; border:0;
}
QCalendarWidget#OrderCalendar QMenu { background:#172232; color:#f4f8fd; }
QCalendarWidget#OrderCalendar QSpinBox {
    background:transparent; color:#f4f8fd; border:0; font-size:15px; font-weight:800;
}
QCalendarWidget#OrderCalendar QAbstractItemView:enabled {
    background:#172232; color:#eef4fb; selection-background-color:#4d7199; selection-color:#ffffff;
    border:0; outline:0; font-size:14px;
}
QFrame#OrderRow { border-radius:8px; }
QFrame#OrderRow[orderSelected="true"] {
    border:1px solid #91aee0; background:#243246;
}
QLabel#OrderSelectedTag { color:#dff5ff; font-size:10px; font-weight:800; }
QWidget#OrderCovers { background:transparent; border:0; }
QLabel#OrderPreviewCover { background:transparent; border:0; }
QPushButton#DetailAction { min-height:30px; font-weight:800; }
QPushButton#Success { min-height:30px; font-weight:800; }
QToolButton#MoreActions { min-width:34px; min-height:30px; }
QDialog#OrderTrackWindow, QDialog#OrderTrackTabsWindow {
    background:#111a26;
}
QFrame#TrackBookCard {
    background:#182335; border:1px solid #39506b; border-radius:8px;
}
QWidget#TrackControlZone { background:transparent; border:0; }
QWidget#TrackCoverZone { background:transparent; border:0; }
QLabel#TrackBookName { font-size:12px; font-weight:850; }
QLabel#TrackBookInfo { font-size:10px; }
QFrame#TrackVariantSB, QFrame#TrackVariantRNK { border-radius:6px; }
QPushButton#TrackPdfButton {
    background:#29425e; border:1px solid #5d84ad; border-radius:6px; color:#edf6ff;
    min-height:28px; font-weight:800;
}
QPushButton#TrackPdfButton:hover { background:#36557a; }
QTabWidget::pane { border:0; }
QTabBar::tab {
    background:#1b2738; color:#dce6f3; border:1px solid #3a4b63; border-bottom:0;
    padding:7px 12px; margin-right:2px; border-top-left-radius:8px; border-top-right-radius:8px;
}
QTabBar::tab:selected { background:#24364d; color:#ffffff; }
QFrame#PoolBookRow { background:#1a2434; border:1px solid #33465c; border-radius:8px; }
QPushButton#PoolOrderLink { min-height:24px; padding:4px 8px; }
"""


QSS += """
/* V4.20 – Etkileşimli özel takvim, filtre listeleri, kompakt arşiv ve havuz */
QFrame#Header { background:#131c28; border:0; border-bottom:1px solid #2c3b50; }
QPushButton#Nav { font-size:17px; font-weight:800; padding:6px 18px; min-height:0; }
QFrame#OrdersSubbar { background:#182536; border:0; border-bottom:1px solid #33465c; }
QPushButton#OrdersSubnav { min-height:0; padding:4px 13px; font-size:11px; }
QFrame#OrderToolbar { background:#152132; border:1px solid #304258; }
QFrame#OrderToolbar QComboBox#OrderFilter { min-height:0; max-height:34px; }
QListView#OrderDropdownList {
    background:#19283a; color:#eef5fc; border:1px solid #4b6481;
    outline:0; padding:0; font-size:12px; show-decoration-selected:0;
    selection-background-color:#385a82; selection-color:white;
}
QListView#OrderDropdownList::item {
    color:#eef5fc; background:#19283a; min-height:27px; padding:3px 9px;
    border:0; border-bottom:1px solid #30465f;
}
QListView#OrderDropdownList::item:selected {
    background:#496a91; color:#fff;
}
QListView#OrderDropdownList::item:hover { background:#304a68; }
QComboBox#OrderFilter QAbstractItemView::item { min-height:27px; }
QDialog#DatePickerDialog { background:#111d2b; border:1px solid #405976; border-radius:12px; }
QLabel#CalendarTitle { color:#f3f7ff; font-size:16px; font-weight:900; }
QLabel#CalendarHelp { color:#aabdd4; font-size:11px; }
QLabel#CalendarMonth { color:#f5f8ff; font-size:15px; font-weight:850; }
QLabel#CalendarWeekday { color:#9aacc3; font-size:11px; font-weight:750; padding:6px 0; }
QPushButton#CalendarArrow {
    background:#23364c; border:1px solid #415976; border-radius:7px;
    color:#e4f0ff; font-size:22px; font-weight:900; padding:0;
}
QPushButton#CalendarArrow:hover { background:#365675; }
QPushButton#CalendarDay {
    background:transparent; border:1px solid transparent; border-radius:7px;
    color:#d7e5f4; font-size:12px; font-weight:750; padding:0;
}
QPushButton#CalendarDay:hover { background:#344b66; border-color:#668cb5; }
QPushButton#CalendarDay[otherMonth="true"] { color:#657c97; }
QPushButton#CalendarDay[hasOrder="true"] {
    background:#254b64; border:1px solid #408da7;
    color:#a5f3fa; font-weight:900;
}
QPushButton#CalendarDay[selectedDay="true"] {
    background:#5373a0; border:1px solid #a1c7ed;
    color:#ffffff; font-weight:900;
}
QLabel#CalendarMarker { color:#65d7e1; font-size:15px; font-weight:900; }
QLabel#CalendarSelection { color:#d0e3fb; font-size:11px; font-weight:750; padding:4px 0; }
QFrame#OrderArchiveHeader {
    background:#1c3540; border:1px solid #466b6e; border-radius:8px;
}
QFrame#OrderArchiveCard {
    background:#1c293b; border:1px solid #3c516b; border-radius:9px;
}
QFrame#OrderArchiveCard:hover { border-color:#7196ba; }
QFrame#TrackBookCard { background:#1b2939; border-radius:8px; }
QFrame#PoolBookRow { background:#1b293a; border:1px solid #3d526b; border-radius:9px; }
QFrame#PoolBookRow:hover { border-color:#668fb7; }
QFrame#PoolVariantSB { background:#292640; border:1px solid #5a5283; border-radius:6px; }
QFrame#PoolVariantRNK { background:#402e2d; border:1px solid #805443; border-radius:6px; }
QPushButton#PoolPdfAction {
    background:#29445e; border:1px solid #5882aa; border-radius:6px;
    color:#ecf6ff; padding:5px 8px; font-weight:800;
}
QPushButton#PoolPdfAction:hover { background:#385a79; }
QPushButton#PoolMiniStep {
    background:#304560; border:1px solid #5e7e9f; border-radius:5px;
    font-weight:900; padding:0; font-size:14px;
}
QPushButton#PoolMiniStep:hover { background:#47678a; }
"""


QSS += """
/* V4.21 — Kontrast, erişilebilir etkileşim durumları ve üç bölgeli bilgi kartları. */
QPushButton#OrderPoolCTA {
    background:#514099; border:1px solid #a592e8; border-radius:18px;
    color:#faf7ff; font-size:12px; font-weight:900; padding:8px 17px;
}
QPushButton#OrderPoolCTA:hover { background:#6c58b8; border-color:#d3c7ff; }
QPushButton#OrderPoolCTA:pressed { background:#39306f; }
QFrame#OrderRow:hover { background:#213449; border-color:#78c5f1; }
QFrame#OrderRow[orderSelected="true"] { border:2px solid #b79bff; background:#272942; }
QFrame#OrderRow[orderRecent="true"] { border:2px solid #61b4fd; background:#1c354b; }
QFrame#OrderRow[orderFocused="true"] { border:2px solid #ffc97a; }
QFrame#OrderRow[orderSelected="true"][orderRecent="true"] { border:2px solid #d6b8ff; background:#2b3150; }
QLabel#OrderPoolQty, QLabel#OrderPoolPages,
QLabel#OrderActiveQty, QLabel#OrderActivePages {
    border-radius:7px; padding:5px 8px; font-weight:900;
}
QLabel#OrderPoolQty {
    color:#fff1bd; background:#655023; border:1px solid #d8a54f;
    font-size:13px;
}
QLabel#OrderPoolPages {
    color:#ddedff; background:#294b6c; border:1px solid #5b9bdb;
    font-size:12px;
}
QLabel#OrderActiveQty {
    color:#e4f5ff; background:#235173; border:1px solid #449ccc;
    font-size:11px;
}
QLabel#OrderActivePages {
    color:#dfe6ff; background:#353f6b; border:1px solid #757ed0;
    font-size:11px;
}
QLabel#OrderMoney { color:#7ee8bd; font-weight:850; }
QToolButton#MoreActions { min-width:0; padding:0; }
QPushButton#DetailAction { min-width:0; padding:6px 8px; }

/* Sipariş takip sekmeleri: seçili sekme belirgin, her sekme metni durum rengi. */
QTabWidget#OrderTrackTabs::pane {
    background:#111c2b; border:1px solid #415774; border-radius:9px;
}
QTabWidget#OrderTrackTabs QTabBar::tab {
    background:#1d2b3b; border:1px solid #445a74;
    border-bottom:2px solid #3c536c; border-top-left-radius:7px; border-top-right-radius:7px;
    padding:9px 16px; font-size:12px; font-weight:900; min-width:120px;
}
QTabWidget#OrderTrackTabs QTabBar::tab:selected {
    background:#2c4158; border-color:#82bde9; border-bottom:3px solid #f2b46f;
}
QTabWidget#OrderTrackTabs QTabBar::tab:hover { background:#354f6b; }
QLabel#OrderStatusBadgeActive {
    color:#e5f4ff; background:#236493; border:1px solid #74c7ff;
    border-radius:10px; padding:5px 10px; font-weight:900;
}
QLabel#OrderStatusBadgeDone {
    color:#c7ffe9; background:#20674f; border:1px solid #66e1b2;
    border-radius:10px; padding:5px 10px; font-weight:900;
}
QLabel#OrderStatusBadgePool {
    color:#ffe5bd; background:#6b4a29; border:1px solid #efb76b;
    border-radius:10px; padding:5px 10px; font-weight:900;
}
QFrame#TrackBookCard:hover { border:2px solid #7cb7e5; background:#22364a; }
QFrame#TrackBookCard[trackSelected="true"] { border:2px solid #c9a9ff; background:#2b2945; }
QFrame#TrackBookCard[trackRecent="true"] { border:2px solid #7ad1f7; background:#213b4f; }
QFrame#TrackBookCard[trackSelected="true"][trackRecent="true"] {
    border:2px solid #e0bdff; background:#313653;
}
QWidget#TrackCoverZone { background:transparent; border:0; padding:0; }
QLabel#TrackBookName { color:#f4f8ff; font-size:12px; font-weight:850; }
QLabel#TrackBookInfo { color:#b9c9db; font-size:10px; }

/* Kitap bazlı genel bakış: dar ama dolu kartlar. */
QDialog#BookPoolDialog { background:#111a28; }
QFrame#PoolBookRow { background:#1b293a; border:1px solid #455f7b; border-radius:10px; }
QFrame#PoolBookRow:hover { background:#243b50; border:2px solid #77b8e7; }
QFrame#PoolBookRow[poolRecent="true"] { background:#223c50; border:2px solid #86d8fb; }
QWidget#PoolCoverInfo { background:transparent; border:0; }
QLabel#PoolBookName { color:#f5f9ff; font-size:11px; font-weight:900; }
QLabel#PoolBookInfo { color:#c4d1e2; font-size:9px; }
QLabel#PoolQuantityPill {
    color:#fef5d4; background:#62522d; border:1px solid #b6a05d;
    border-radius:7px; padding:5px 7px; font-size:11px; font-weight:850;
}
QFrame#PoolVariantSB { background:#262a45; border:1px solid #746caf; border-radius:8px; }
QFrame#PoolVariantRNK { background:#432c2b; border:1px solid #b37756; border-radius:8px; }
QLabel#PoolVariantTitle { color:#faf7ff; font-weight:900; font-size:11px; }
QLabel#PoolVariantCount { color:#ecf3fa; font-weight:850; font-size:11px; }
QLabel#PoolMiniLabel { color:#d8e4f1; font-weight:750; font-size:10px; }
QLabel#PoolMiniValue { color:#ffffff; font-weight:900; font-size:11px; }
QFrame#PoolOrderLinks { background:#132237; border:1px solid #405a77; border-radius:7px; }
QLabel#PoolLinksTitle { color:#a9d8f8; font-size:10px; font-weight:850; }
QPushButton#PoolOrderLink {
    background:#254765; color:#f5fbff; border:1px solid #5e91b9;
    border-radius:5px; padding:4px 7px; font-weight:850;
}
QPushButton#PoolOrderLink:hover { background:#39739a; border-color:#9bd4f7; }

/* Takvimde sipariş günleri: gerçek vurgu; seçili günler daha sıcak kontrast. */
QPushButton#CalendarDay[hasOrder="true"] {
    background:#146a6c; border:2px solid #49e4d4; color:#ffffff; font-weight:900;
}
QPushButton#CalendarDay[selectedDay="true"] {
    background:#b66c27; border:2px solid #ffde8b; color:#ffffff; font-weight:900;
}
QPushButton#CalendarDay[hasOrder="true"][selectedDay="true"] {
    background:#b96727; border:2px solid #fff0a6;
}
QLabel#CalendarMarker { color:#49e4d4; }
"""


QSS += """
/* V4.22 – responsive layout and readable status without reflowing controls. */
QLabel#OrderRevenuePill {
    background:#174738; border:1px solid #3eae86; border-radius:7px;
    color:#a5ffda; padding:4px 8px; font-weight:850; font-size:11px;
}
QTabWidget#OrderTrackTabs { background:#111b2a; border:0; }
QTabWidget#OrderTrackTabs::pane { border:0; margin:0; padding:0; background:#101b29; }
QTabWidget#OrderTrackTabs QTabBar { background:#111b2a; border:0; }
QTabWidget#OrderTrackTabs QTabBar::tab {
    min-width:100px; background:#1b2a3c; color:#c9d9e9;
    border:1px solid #455d79; border-bottom:0;
    padding:8px 13px; margin-right:3px;
    border-top-left-radius:7px; border-top-right-radius:7px;
}
QTabWidget#OrderTrackTabs QTabBar::tab:selected {
    background:#2b435c; border:1px solid #7ba9d4;
    border-bottom:0; color:#ffffff;
}
QTabWidget#OrderTrackTabs QTabBar::tab:hover { background:#344d69; }
QLabel#PoolMiniValue {
    color:#fff; background:#162437; border:1px solid #4c6683;
    border-radius:4px; padding:2px; font-weight:900; font-size:11px;
}
QLabel#PoolQuantityPill { min-height:22px; }
QFrame#PoolBookRow { min-width:0; }
QFrame#PoolBookRow:hover { border:1px solid #8acbf2; }
"""

QSS += """
QFrame#PoolBookRow[poolRecent="true"] {
    background:#223c50; border:1px solid #86d8fb;
}
"""


QSS += """
/* V4.24: readable left-order badges and Windows-safe revenue editing. */
QLabel#OrderRevenuePill {
    background:#174738; border:1px solid #3eae86;
    border-radius:6px; color:#bbffe2; padding:4px 5px;
    font-size:10px; font-weight:850;
}
QFrame#OrderEditRevenueBox {
    background:#101b2b; border:1px solid #537391; border-radius:7px;
}
QLineEdit#OrderEditRevenueInput {
    background:transparent; color:#ffffff; border:0; border-radius:0;
    font-size:15px; font-weight:800; padding:5px 6px;
    selection-background-color:#426b95; selection-color:white;
}
QLineEdit#OrderEditRevenueInput:focus {
    background:transparent; border:0; color:#ffffff;
}
QLabel#OrderEditCurrencyLabel {
    background:transparent; color:#9fd6c2; font-size:12px; font-weight:850;
}
"""

QSS += """
/* ALFA ERP V4.25 · Analitik, ayarlar ve modern üst menü */
QPushButton#Nav {
    color:#d5e4f4; background:transparent; border:0;
    border-bottom:2px solid transparent; border-radius:0;
    padding:10px 21px 9px; font-family:'Segoe UI';
    font-size:15px; font-weight:800; min-width:118px;
}
QPushButton#Nav:hover {color:#ffffff; background:#22354b; border-bottom:2px solid #7ed6ff;}
QPushButton#Nav:checked {color:#f5faff; background:#192b40; border-bottom:3px solid #6fc5ff;}
QPushButton#SettingsGear {
    color:#dce9f9; background:#26384d; border:1px solid #526b85;
    border-radius:9px; padding:5px; font-family:'Segoe UI Symbol';
    font-size:22px; font-weight:800; min-height:34px; min-width:39px;
}
QPushButton#SettingsGear:hover, QPushButton#SettingsGear:checked {
    background:#315b73; border:1px solid #7cdcf1; color:#ffffff;
}
QLabel#OrderShippingCost {
    color:#fbd29a; background:#4b362b; border:1px solid #906445;
    border-radius:5px; padding:3px 7px; font-weight:750; font-size:10px;
}
QWidget#AnalyticsPage, QWidget#SettingsPage {background:transparent;}
QFrame#AnalyticsToolbar, QFrame#SettingsCard {
    background:#1a2739; border:1px solid #3d5068; border-radius:10px;
}
QLabel#AnalyticsTitle, QLabel#SettingsTitle {
    color:#f1f7ff; font-size:16px; font-weight:900;
    font-family:'Segoe UI';
}
QLabel#AnalyticsSection, QLabel#SettingsHeading {
    color:#bce7ff; font-size:13px; font-weight:900;
    font-family:'Segoe UI';
}
QLabel#AnalyticsHint, QLabel#AnalyticsFootnote, QLabel#SettingsHint {
    color:#a9bdd2; font-size:10px; line-height:1.3;
}
QLabel#SettingsPath {
    color:#e9f3ff; background:#122137; border:1px solid #324b67;
    border-radius:6px; padding:9px; font-size:11px;
}
QComboBox#AnalyticsFilter {
    color:#eaf3ff; background:#24354a; border:1px solid #4d6885;
    border-radius:7px; padding:7px 8px; min-height:26px;
}
QComboBox#AnalyticsFilter:hover {border-color:#92c8ed;}
QPushButton#AnalyticsExport {
    color:#d8fff3; background:#225446; border:1px solid #4eac90;
    border-radius:7px; font-weight:850; padding:9px 11px;
}
QPushButton#AnalyticsExport:hover {background:#2b705d;}
QFrame#AnalyticsMetric, QFrame#AnalyticsTable {
    background:#19283a; border:1px solid #3b536c; border-radius:10px;
}
QFrame#AnalyticsMetric:hover {background:#203750; border:1px solid #7badd8;}
QLabel#AnalyticsCaption {color:#b3c5d7; font-size:11px; font-weight:700;}
QLabel#AnalyticsValue {font-family:'Segoe UI'; font-size:19px; font-weight:900;}
QLabel#AnalyticsTableTitle {color:#f2f8ff; font-size:12px; font-weight:850;}
QTableWidget#AnalyticsDataTable {
    background:#142335; alternate-background-color:#1c2d40;
    color:#e4eefb; border:0; selection-background-color:#385d79;
    gridline-color:transparent; font-size:10px;
}
QTableWidget#AnalyticsDataTable::item {padding:4px 7px; border:0;}
QHeaderView::section {
    background:#2c4057; color:#d4e9fb; border:0; border-bottom:1px solid #57718c;
    padding:6px; font-size:10px; font-weight:850;
}
QPushButton#SettingsNav {
    background:#26374a; border:1px solid #4b627b; color:#dce8f5;
    padding:7px 17px; border-radius:7px; font-size:12px; font-weight:850;
}
QPushButton#SettingsNav:hover {background:#2f506c; border-color:#7ab7dc;}
QPushButton#SettingsNav:checked {
    color:#ffffff; background:#2b5878; border-color:#91d8ef;
}
QPushButton#SettingsThemeOption {
    background:#26374a; border:1px solid #506c88; border-radius:7px;
    color:#e4f1fd; padding:12px 10px; font-weight:850;
}
QPushButton#SettingsThemeOption:hover {border-color:#98d4fd;}
QPushButton#SettingsThemeOption:checked {
    border:2px solid #67dfc0; background:#22584e; color:#ffffff;
}
QFrame#AuditEvent {
    background:#19283a; border:1px solid #3c5470; border-radius:9px;
}
QFrame#AuditEvent:hover {background:#1e344c; border-color:#78b5e3;}
QLabel#AuditHeading {color:#f1f7ff; font-size:12px; font-weight:850;}
QLabel#AuditDescription {color:#c3d2e3; font-size:11px;}
QLabel#AuditTime {color:#b1c5dc; font-size:10px; font-weight:700;}
QLabel#AuditMeta {color:#8ea7c1; font-size:10px;}
QLabel#AuditIcon {font-size:19px; font-weight:900;}
QLabel#AuditChildTitle {color:#d5eafa; font-size:10px; font-weight:700;}
QFrame#AuditChildren {
    background:rgba(92,136,172,0.10); border:1px solid #344f68;
    border-radius:7px;
}
QToolButton#AuditExpand {
    color:#acdff8; background:transparent; border:0;
    padding:4px 5px; text-align:left; font-size:10px; font-weight:850;
}
QToolButton#AuditExpand:hover {color:#ffffff;}
"""


QSS += """
/* V4.26 – order statuses have distinct stage colors. */
QPushButton#OrdersSubnav[orderStage="havuz"] {color:#caaa80;}
QPushButton#OrdersSubnav[orderStage="aktif"] {color:#9ccee9;}
QPushButton#OrdersSubnav[orderStage="tamamlandi"] {color:#a0dbc1;}
QPushButton#OrdersSubnav[orderStage="havuz"]:checked {
    color:#ffe0ac; background:#513b28; border-bottom:3px solid #f4b75d;
}
QPushButton#OrdersSubnav[orderStage="havuz"]:hover {color:#ffe1b0;background:#3f352e;}
QPushButton#OrdersSubnav[orderStage="aktif"]:checked {
    color:#c5eaff; background:#21415b; border-bottom:3px solid #69c4ff;
}
QPushButton#OrdersSubnav[orderStage="aktif"]:hover {color:#c5eaff;background:#233b50;}
QPushButton#OrdersSubnav[orderStage="tamamlandi"]:checked {
    color:#c4ffe1; background:#204b3d; border-bottom:3px solid #5cdf9c;
}
QPushButton#OrdersSubnav[orderStage="tamamlandi"]:hover {color:#c7ffe8;background:#204034;}
QPushButton#PoolDeleteAction {
    background:#612b37; color:#ffe1e2; border:1px solid #bd6671;
    border-radius:7px; font-size:12px; font-weight:850; padding:6px 10px;
}
QPushButton#PoolDeleteAction:hover {background:#853848;border-color:#f69aa7;}
QPushButton#PoolDeleteAction:pressed {background:#a94854;}
QPushButton#DetailAction[orderStage="havuz"] {min-height:38px;}
QFrame#PoolOverviewGroup {background:#16283b; border:1px solid #405c7a; border-radius:9px;}
QFrame#PoolOverviewBook {background:#20324a; border:1px solid #3b597a; border-radius:7px;}
QFrame#PoolOverviewBook:hover {border:1px solid #85c6f4; background:#2a405b;}
QLabel#PoolOverviewHeading {color:#ffd198; font-size:13px; font-weight:900;}
QLabel#PoolOverviewCounts {color:#cabdff; font-size:12px; font-weight:800;}
/* Analitik: embeddable accounting calendar + dense stat pills. */
QFrame#AccountingCalendarPanel {background:#192839; border:1px solid #415775; border-radius:12px;}
QLabel#AccountingMonthTitle {font-size:17px;font-weight:900;color:#f3f8ff;}
QPushButton#AccountingMonthArrow {background:#2a4158;color:#f2f8ff;border:1px solid #557698;border-radius:7px;font-size:22px;padding:0;}
QPushButton#AccountingMonthArrow:hover {background:#40607e;}
QLabel#AccountingWeekday {font-size:10px;color:#a9bdd1;font-weight:850;}
QPushButton#AccountingDay {
    background:#233349;color:#d6e4f4;border:1px solid #34465c;
    border-radius:7px;font-size:12px;font-weight:750;padding:0;
}
QPushButton#AccountingDay:hover {border:2px solid #f4f7ff; background:#385474;}
QPushButton#AccountingDay[outsideMonth="true"] {color:#7b90a8;}
QPushButton#AccountingDay[accountState="done"] {background:#88621e;color:#fff3c3;border:1px solid #e9b542;font-weight:900;}
QPushButton#AccountingDay[accountState="review"] {background:#8b5922;color:#ffe9bf;border:2px dashed #ffd178;font-weight:900;}
QPushButton#AccountingDay[accountState="paid"] {background:#185fa7;color:#fff;border:1px solid #65b9ff;font-weight:900;}
QPushButton#AccountingDay[accountState="active"] {background:#254360;color:#afdcff;border:1px solid #497fa7;font-weight:850;}
QPushButton#AccountingDay[selectedDay="true"] {border:3px solid #f6f9ff;font-weight:950;}
QPushButton#AccountingDay[selectedDay="true"]:hover {border:3px solid #ffffff;}
QLabel#AccountingHelp {color:#aabfd4;font-size:10px;}
QLabel#AccountingSelection {color:#f5e4bd;background:#263a50;border:1px solid #5a7695;border-radius:6px;padding:8px;font-weight:850;font-size:11px;}
QLabel#AccountingPeriod {color:#a9dcf7;font-size:12px;font-weight:800;}
QLabel#AccountingLegend {font-size:11px;font-weight:850;}
QLabel#AccountingLegend[legendRole="done"] {color:#f5c55b;}
QLabel#AccountingLegend[legendRole="paid"] {color:#77bdfd;}
QLabel#AccountingLegend[legendRole="active"] {color:#8db5d3;}
QPushButton#AccountingPaidAction {background:#205b94;color:#fff;border:1px solid #72b8eb;border-radius:7px;padding:8px 6px;font-size:12px;font-weight:900;}
QPushButton#AccountingPaidAction:hover {background:#297ac0;}
QPushButton#AccountingUnpaidAction {background:#5c4826;color:#ffe3a8;border:1px solid #b88b48;border-radius:7px;padding:8px 6px;font-size:12px;font-weight:900;}
QPushButton#AccountingUnpaidAction:hover {background:#786039;}
QPushButton#AccountingPaidAction:disabled, QPushButton#AccountingUnpaidAction:disabled {background:#293442;color:#8999ab;border-color:#455366;}
QFrame#AccountingPill {background:#1c2f43;border:1px solid #49617c;border-radius:8px;min-height:0;}
QFrame#AccountingPill:hover {background:#29425c;border:1px solid #76acda;}
QLabel#AccountingPillTitle {color:#acbfd4;font-size:10px;font-weight:750;}
QLabel#AccountingPillValue {font-family:'Segoe UI';font-size:16px;font-weight:900;}
"""

QSS += """
/* V4.27 — Muhasebe rozetlerinin Windows / HiDPI başlangıçta ezilmesini önle. */
QFrame#AccountingPill {
    min-height:70px;
    max-height:70px;
    background:#20354b;
    border:1px solid #536c89;
    border-radius:8px;
}
QFrame#AccountingPill:hover {background:#294764;border-color:#7fc8f8;}
QLabel#AccountingPillTitle {
    color:#bed2e8; font-size:10px; font-weight:800;
    min-height:16px; max-height:16px; padding:0;
    background:transparent; border:0;
}
QLabel#AccountingPillValue {
    font-family:'Segoe UI'; font-size:17px; font-weight:900;
    min-height:27px; max-height:27px; padding:0;
    background:transparent; border:0;
}
QPushButton#AccountingQuick {
    background:#29425a; color:#e3f2ff; border:1px solid #557da2;
    border-radius:6px; padding:5px 7px; font-weight:850;
    min-height:20px;
}
QPushButton#AccountingQuick:hover {background:#356587; border-color:#8fd0fa;}
"""

QSS += """
/* V4.29 — Konuya göre gruplu muhasebe ve isteğe bağlı arşiv. */
QFrame#AnalyticsMetricGroup { background:#162336; border:1px solid #39516c; border-radius:10px; }
QLabel#AnalyticsGroupTitle { color:#b8d4f4; background:transparent; border:0; font-size:12px; font-weight:900; letter-spacing:.4px; }
QLabel#AnalyticsGroupTitle[groupKind="finance"] {color:#78dfbf;}
QLabel#AnalyticsGroupTitle[groupKind="shipping"] {color:#f2bf84;}
QLabel#AnalyticsGroupTitle[groupKind="orders"] {color:#8bc4ff;}
QLabel#AnalyticsGroupTitle[groupKind="books"] {color:#c8b1ff;}
QLabel#AnalyticsGroupTitle[groupKind="printing"] {color:#ffa88a;}
QFrame#CompletedArchiveBar {background:#1b2c40; border:1px solid #42607e; border-radius:8px;}
QLabel#ArchiveStatus {color:#d5e4f5; font-size:11px; font-weight:800;}
QPushButton#ArchiveToggle {background:#57472e; color:#ffe5b1; border:1px solid #ae884c; border-radius:7px; padding:6px 14px; font-size:11px; font-weight:850;}
QPushButton#ArchiveToggle:hover {background:#745a35; border-color:#ecc077;}
QPushButton#ArchiveLoadMore {background:#284564; color:#e3f2ff; border:1px solid #6795be; border-radius:8px; padding:8px 18px; font-weight:800;}
QPushButton#ArchiveLoadMore:hover {background:#335b7e; border-color:#9cd1ff;}
"""


QSS += """
/* V4.30 — Unified order controls / lightweight UI polish. */
QPushButton#OrderPoolCTA, QPushButton#OrderPrintCTA {
    border-radius:9px; padding:6px 13px; font-size:12px; font-weight:900;
    min-height:0; max-height:38px;
}
QPushButton#OrderPoolCTA {
    color:#f7f2ff; background:#5745a4; border:1px solid #a997ea;
}
QPushButton#OrderPoolCTA:hover {background:#6f5cbe; border-color:#d0c5fc;}
QPushButton#OrderPoolCTA:pressed {background:#403386; border-color:#9a85d9;}
QPushButton#OrderPrintCTA {
    color:#1e2631; background:#f2b76f; border:1px solid #f2bb7a;
}
QPushButton#OrderPrintCTA:hover {background:#ffcb8e; border-color:#ffe1b8;}
QPushButton#OrderPrintCTA:pressed {background:#db9b4f; border-color:#eab276;}
QPushButton#OrderPrintCTA:disabled {
    color:#a2aabb; background:#303e4e; border:1px solid #4b5b71;
}
QPushButton#OrderPoolCTA:focus, QPushButton#OrderPrintCTA:focus {
    border:2px solid #d3e9ff;
}
QFrame#OrderToolbar {background:#162233; border:1px solid #3b526d; border-radius:10px;}
QFrame#OrderFilterSegment {
    background:#203047; border:1px solid #425874; border-radius:9px;
}
QLineEdit#OrderSearch, QComboBox#OrderFilter, QPushButton#CalendarTrigger,
QPushButton#OrderReset, QToolButton#OrderSortReverse {
    background:#182639; color:#eaf3fc; border:1px solid #526a86;
    border-radius:8px; padding:6px 9px; font-size:11px; font-weight:750;
    min-height:0; max-height:36px;
}
QLineEdit#OrderSearch:hover, QComboBox#OrderFilter:hover,
QPushButton#CalendarTrigger:hover, QPushButton#OrderReset:hover,
QToolButton#OrderSortReverse:hover {background:#273c55; border-color:#8bb4db;}
QLineEdit#OrderSearch:focus, QComboBox#OrderFilter:focus,
QPushButton#CalendarTrigger:focus, QPushButton#OrderReset:focus,
QToolButton#OrderSortReverse:focus {border:1px solid #a5cffa;}
QToolButton#OrderSortReverse {padding:0; font-size:16px;}
QLabel#OrderMetrics {color:#c4d8ea; font-size:11px; font-weight:800;}
QLabel#OrderSelectedCount {
    color:#e5f4ff; background:#2c435d; border:1px solid #6487a9;
    border-radius:8px; padding:6px 10px; font-weight:900;
}
QPushButton#Nav {font-size:16px; font-weight:850; padding:9px 19px 8px;}
QPushButton#OrdersSubnav {font-size:12px; font-weight:850;}
QFrame#OrderRow {border:1px solid #405772; border-radius:9px; background:#1b293c;}
QFrame#OrderRow[orderStatus="havuz"] {border-left:3px solid #c5a06b;}
QFrame#OrderRow[orderStatus="aktif"] {border-left:3px solid #659cc9;}
QFrame#OrderRow[orderStatus="tamamlandi"] {border-left:3px solid #6bbd9c;}
QFrame#OrderRow:hover {background:#20354a; border-color:#86b3d8;}
QFrame#OrderRow[orderSelected="true"] {background:#282c49; border:2px solid #ae96ef;}
QFrame#OrderRow[orderRecent="true"] {background:#1d354c; border:2px solid #70bff1;}
QFrame#OrderRow[orderFocused="true"] {border:2px solid #f6c985;}
QFrame#OrderRow[orderSelected="true"][orderRecent="true"] {
    background:#303650; border:2px solid #d3b5ff;
}
QPushButton#DetailAction, QToolButton#MoreActions {
    border:1px solid #587391; border-radius:8px; font-weight:850;
}
QPushButton#DetailAction:hover, QToolButton#MoreActions:hover {
    background:#304a67; border-color:#97bee4;
}
QPushButton#DetailAction:pressed, QToolButton#MoreActions:pressed {background:#1a2f46;}
QToolButton#MoreActions {padding:0; font-size:15px;}
QPushButton#Success {border-radius:8px;}
QPushButton#Success:hover {background:#82e3b9; color:#103526; border-color:#a8ffd9;}
QPushButton#Success:disabled {background:#334c46; color:#9dbbb0; border:1px solid #4b6c62;}
QPushButton#PoolDeleteAction {border-radius:8px;}
QLabel#OrderRevenuePill {border-radius:7px;}
QLabel#OrderPoolQty, QLabel#OrderPoolPages,
QLabel#OrderActiveQty, QLabel#OrderActivePages {border-radius:7px;}
"""


QSS += """
/* V4.31 - clear visual hierarchy without changing the base layout. */
QDialog#OrderTrackTabsWindow { background:#101925; }
QFrame#TrackTabsHeader {
    background:#1c2e43; border:1px solid #45607b; border-radius:8px;
}
QLabel#TrackTabsHeading {
    background:transparent; color:#d9eaff; font-size:11px; font-weight:900;
    letter-spacing:.5px;
}
QLabel#TrackTabsHelp { background:transparent; color:#91abc6; font-size:10px; }
QLabel#TrackTabsCount {
    background:#284564; border:1px solid #5a7b9c; color:#e1f3ff;
    border-radius:7px; padding:4px 9px; font-size:10px; font-weight:850;
}
QTabWidget#OrderTrackTabs { background:transparent; border:0; }
QTabWidget#OrderTrackTabs::pane {
    background:#101b29; border:1px solid #405875; border-radius:8px;
    top:-1px;
}
QTabBar#OrderTrackTabBar { background:transparent; border:0; }
QTabBar#OrderTrackTabBar::tab {
    background:#202f42; border:1px solid #435a73;
    border-bottom:2px solid #435a73; border-radius:7px;
    padding:9px 13px; margin:3px 5px 4px 0;
    min-width:110px; font-size:11px; font-weight:900;
}
QTabBar#OrderTrackTabBar::tab:hover {
    background:#304764; border-color:#86b7e6;
}
QTabBar#OrderTrackTabBar::tab:selected {
    background:#304b67; border:1px solid #81c5f1;
    border-bottom:3px solid #f0b56e;
}
QFrame#TrackActionToolbar {
    background:#17283b; border:1px solid #405773; border-radius:9px;
}
QLabel#TrackActionsHeading {
    color:#a6c9e9; font-size:10px; font-weight:900;
    background:transparent; letter-spacing:.5px;
}
QLabel#TrackControlsCaption {
    color:#b0cde6; font-size:9px; font-weight:850;
    background:transparent;
}
QCheckBox#TrackSelectAll { font-size:11px; font-weight:750; }
QFrame#TrackBookCard { border:1px solid #465d79; border-radius:9px; }
QFrame#TrackBookCard:hover { border:1px solid #89bfea; background:#23384d; }
QFrame#TrackBookCard[trackSelected="true"] {
    border:2px solid #c2a7f2; background:#2b2b46;
}
QFrame#TrackBookCard[trackRecent="true"] {
    border:2px solid #73c7ec; background:#213b50;
}
QFrame#TrackZoneDivider { background:#4d6786; border:0; }
QPushButton#TrackPdfButton { border-radius:7px; }
QPushButton#TrackPdfButton:hover { border-color:#9bc9f0; }
QFrame#OrderRightPanel {
    background:#1a3045; border:1px solid #3f5975; border-radius:9px;
}
QFrame#OrderProgressGroup {
    background:#182739; border:1px solid #364c65; border-radius:6px;
}
QLabel#OrderProgressCaption { color:#bdd0e4; font-size:10px; font-weight:700; }
QLabel#OrderProgressNumber { color:#f1f6ff; font-size:10px; font-weight:900; }
QLabel#OrderPoolInfo {
    color:#ebc88e; font-size:10px; font-weight:800;
    background:transparent;
}
QPushButton#DetailAction { border-radius:7px; }
QToolButton#MoreActions { border-radius:7px; }
QPushButton#DetailAction:hover, QToolButton#MoreActions:hover {
    border-color:#9cccf4; background:#385673;
}
"""

QSS += """
/* V4.32 — Görsel netlik, dengeli işlem kontrolleri ve okunabilir durumlar. */
QLabel#PoolActiveScope {
    background:#1d433e; border:1px solid #4fae92; border-radius:8px;
    color:#c3ffe8; font-size:11px; font-weight:900; padding:5px 8px;
}
QFrame#BookPoolToolbar {border-color:#496987;}
QFrame#PoolBookRow:hover {background:#21364b; border-color:#8ab8e1;}
QFrame#TrackActionToolbar {border-color:#55718f;}
QFrame#TrackActionReady, QFrame#TrackActionBoxed {
    border-radius:8px; min-height:42px;
}
QFrame#TrackActionReady {background:#2b2c48; border:1px solid #7774b7;}
QFrame#TrackActionBoxed {background:#1e3c42; border:1px solid #519493;}
QLabel#TrackActionLabel {
    background:transparent; font-size:10px; font-weight:900; letter-spacing:.2px;
    color:#e5effb; padding:0 3px;
}
QPushButton#TrackBulkPositive, QPushButton#TrackBulkNegative {
    min-height:0; max-height:32px; padding:0 9px;
    font-size:12px; font-weight:900; border-radius:6px;
}
QPushButton#TrackBulkPositive {background:#4ca78b; color:#0b2a21; border:1px solid #83e6c5;}
QPushButton#TrackBulkPositive:hover {background:#68cfab; border-color:#aaf5d9;}
QPushButton#TrackBulkPositive:pressed {background:#3b8f77;}
QPushButton#TrackBulkNegative {background:#384f6a; color:#f0f6ff; border:1px solid #7393b5;}
QPushButton#TrackBulkNegative:hover {background:#4b6989; border-color:#aacbe8;}
QPushButton#TrackBulkNegative:pressed {background:#2c425d;}
QPushButton#TrackBulkPositive:disabled, QPushButton#TrackBulkNegative:disabled {
    background:#283441; color:#8295a6; border:1px solid #44586c;
}
QCheckBox#TrackSelectAll {font-weight:850; color:#e9f5ff;}
QFrame#TrackBookCard:hover {border-color:#9dd1ef;}
QPushButton#TrackPdfButton:hover {background:#3d6083;}
QFrame#OrderRightPanel {border-color:#516f8c;}
QFrame#OrderProgressGroup {border-color:#49637f;}
QFrame#OrderProgressGroup:hover {border-color:#6c9cbc;}
QPushButton#DetailAction:hover {border-color:#a4cff0;}
"""


QSS += """
/* V4.33: baskı takibi için tamamı ortalanan araç şeridi ve açık filtre. */
QFrame#TrackActionToolbar {
    background:#182b40; border:1px solid #567492; border-radius:10px;
}
QWidget#TrackActionsRow {background:transparent; border:0;}
QPushButton#TrackSelectAllToggle, QPushButton#TrackUnpreparedToggle {
    min-height:0; max-height:39px; padding:0 11px; border-radius:8px;
    font-size:12px; font-weight:900;
}
QPushButton#TrackSelectAllToggle {
    background:#263b55; border:1px solid #7596bf; color:#eef7ff;
}
QPushButton#TrackSelectAllToggle:hover {background:#34557b; border-color:#a6d3fa;}
QPushButton#TrackSelectAllToggle:checked {
    background:#654b90; border:1px solid #c6a1fd; color:#fff;
}
QPushButton#TrackUnpreparedToggle {
    background:#2d394b; border:1px solid #7193ac; color:#e7f3ff;
}
QPushButton#TrackUnpreparedToggle:hover {background:#3a5166; border-color:#a4cbdf;}
QPushButton#TrackUnpreparedToggle:checked {
    background:#70512c; border:1px solid #f0bf6f; color:#fff1ce;
}
QPushButton#TrackSelectAllToggle:disabled {color:#77899c; background:#263442; border-color:#3e5266;}
QLabel#TrackFilterEmpty {
    background:#1d3044; border:1px dashed #7892ac; border-radius:9px;
    color:#b6d4e7; padding:12px; font-size:12px; font-weight:750;
}
QFrame#TrackActionReady, QFrame#TrackActionBoxed {min-height:39px; max-height:43px;}
QPushButton#PdfAction {font-size:12px; font-weight:900; border-radius:8px;}
"""


QSS += """
/* V4.35: Kargo kodu hizası tek merkezi QSS tanımıyla yönetilir. */
QPushButton#CopyCode {text-align:left; padding-left:10px; padding-right:8px;}
"""

QSS += """
/* V4.39: Tek satır, eşit genişlikli toplu işlem kontrolleri. */
QWidget#TrackActionsRow {background:transparent; border:0;}
QPushButton#TrackSelectAllToggle, QPushButton#TrackUnpreparedToggle,
QPushButton#PdfAction, QFrame#TrackActionReady, QFrame#TrackActionBoxed {
    min-height:46px; max-height:46px; border-radius:9px;
}
QPushButton#TrackSelectAllToggle, QPushButton#TrackUnpreparedToggle, QPushButton#PdfAction {
    font-size:12px; font-weight:850; padding:0 5px;
}
QFrame#TrackActionReady:hover {border:1px solid #b69cfa; background:#343456;}
QFrame#TrackActionBoxed:hover {border:1px solid #79dfc1; background:#244a4a;}
"""
