"""Kullanıcı ayarları ve taşınabilir yerel yedek (internet gerekmez)."""
from pathlib import Path
import json
import os
import tempfile
import shutil
import zipfile

DEFAULTS = {'tema': 'koyu', 'ozel_katalog': None, 'bildirim_sesi': 'klasik'}
BACKUP_NAMES = ('alfa_siparisler.json', 'alfa_sepet_hafiza.json', 'alfa_siparis_sayac.json',
                'alfa_islem_gunlugu.jsonl', 'alfa_pdf_ayarlari.json',
                'alfa_ayarlar.json', 'alfa_katalog_ozel.xlsx',
                'alfa_muhasebe_gunleri.json')


class UserSettings:
    def __init__(self, data_dir):
        self.data_dir=Path(data_dir)
        self.path=self.data_dir/'alfa_ayarlar.json'
        self.values=dict(DEFAULTS)
        if self.path.is_file():
            try:
                stored=json.loads(self.path.read_text(encoding='utf-8'))
                if isinstance(stored,dict):
                    self.values.update({k:v for k,v in stored.items() if k in DEFAULTS})
            except (OSError,ValueError,TypeError):
                pass

    def get(self,key,default=None):
        return self.values.get(key,default)

    def set(self,key,value):
        if key not in DEFAULTS:
            raise ValueError('Bilinmeyen ayar')
        self.values[key]=value
        self.save()

    def save(self):
        self.data_dir.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix='.alfa_cfg_',suffix='.tmp',dir=str(self.data_dir))
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(self.values,f,ensure_ascii=False,indent=2)
            os.replace(name,self.path)
        finally:
            if os.path.exists(name):os.unlink(name)


def write_backup(data_dir,target):
    data_dir=Path(data_dir)
    target=Path(target)
    if target.suffix.lower()!='.zip':
        target=target.with_suffix('.zip')
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in BACKUP_NAMES:
            file=data_dir/name
            if file.is_file():
                archive.write(file,arcname=name)
        archive.writestr('ALFA_ERP_YEDEK_OKU.txt',
                         'Bu yedek JSON veri, islem gunlugu ve ayarlari icerir. '
                         'PDF dosyalarinin kendisi ve kapak gorselleri dahil degildir.\n')
    return target


def restore_backup(data_dir,source):
    """Yalnızca beyaz listedeki isimlere izin ver; eski dosyaları ayrıca yedekle.

    Çağıran taraf restorasyondan sonra uygulamayı sonlandırmalı; eski bellekteki
    nesnelerle çalışıp yeni dosyaların üzerine yazılmamalıdır.
    """
    root=Path(data_dir)
    src=Path(source)
    if not src.is_file(): raise ValueError('Yedek ZIP bulunamadı.')
    with zipfile.ZipFile(src) as z:
        files={n for n in z.namelist() if n in BACKUP_NAMES and not n.endswith('/')}
        if 'alfa_siparisler.json' not in files:
            raise ValueError('Yedekte sipariş verisi bulunamadı.')
        # Ön kontrol: veriler yazılmadan önce JSON doğrulanmalı.
        for name in files:
            payload=z.read(name)
            if len(payload)>100*1024*1024: raise ValueError(f'Yedek girdisi çok büyük: {name}')
            if name.endswith('.json'):
                parsed=json.loads(payload.decode('utf-8'))
                if name=='alfa_siparisler.json' and not isinstance(parsed,list):
                    raise ValueError('Sipariş veri biçimi geçersiz.')
        root.mkdir(parents=True,exist_ok=True)
        previous=root/'yedekler'
        previous.mkdir(exist_ok=True)
        from datetime import datetime
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        # Tüm eski dosyaların geri dönüş kopyası.
        for name in files:
            existing=root/name
            if existing.is_file():
                shutil.copy2(existing,previous/f'{stamp}_{name}')
        for name in files:
            fd,tmp=tempfile.mkstemp(prefix='.alfa_restore_',suffix='.tmp',dir=str(root))
            try:
                with os.fdopen(fd,'wb') as stream:
                    stream.write(z.read(name));stream.flush();os.fsync(stream.fileno())
                os.replace(tmp,root/name)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
        # Başka bilgisayardan gelen mutlak katalog yolu bu makinede geçersiz
        # olabilir. Yedekteki özel katalog bu veri klasörüne taşındı.
        if 'alfa_katalog_ozel.xlsx' in files and 'alfa_ayarlar.json' in files:
            config_path=root/'alfa_ayarlar.json'
            configuration=json.loads(config_path.read_text(encoding='utf-8'))
            if isinstance(configuration,dict) and configuration.get('ozel_katalog'):
                configuration['ozel_katalog']=str(root/'alfa_katalog_ozel.xlsx')
                temp=root/'alfa_ayarlar_restore.tmp'
                temp.write_text(json.dumps(configuration,ensure_ascii=False,indent=2),encoding='utf-8')
                temp.replace(config_path)
    return sorted(files)


def theme_styles(name):
    """Baz QSS'in üstüne önemli renkler için son katman; ayar hemen uygulanır."""
    if name=='kontrast':
        return '''
        QWidget#AppRoot, QWidget#AppBody, QDialog#OrderTrackWindow,
        QDialog#OrderEditWindow, QDialog#BookPoolDialog {background:#060b11; color:#ffffff;}
        QFrame#OrderRow, QFrame#Panel, QFrame#Card, QFrame#AnalyticsMetric,
        QFrame#AnalyticsTable, QFrame#AnalyticsToolbar, QFrame#SettingsCard,
        QFrame#AuditEvent, QFrame#BookPoolToolbar {background:#101b2b; border:1px solid #85a9ce;}
        QFrame#OrderRow:hover, QFrame#AuditEvent:hover {border:2px solid #59d3ff;}
        QPushButton:focus, QComboBox:focus, QLineEdit:focus {border:2px solid #f6d67b;}
        QFrame#OrderRow[orderSelected="true"] {border:2px solid #ffdb6f;}
        QPushButton#OrderPoolCTA, QPushButton#OrderPrintCTA {
            border-radius:9px; font-size:12px; font-weight:900;
            padding:6px 13px; min-height:0; max-height:38px;
        }
        QPushButton#OrderPoolCTA {background:#57469e; color:#fff; border:2px solid #c8b5ff;}
        QPushButton#OrderPrintCTA {background:#efb05f; color:#152335; border:2px solid #ffe7a4;}
        QPushButton#OrderPrintCTA:disabled {background:#3a4550; color:#b5c0cd; border-color:#657587;}
        QPushButton#TrackSelectAllToggle:checked {background:#8e63c0; color:#fff; border-color:#d9beff;}
        QWidget#InventoryHost {background:#060b11;color:#ffffff;}
        QPushButton#InventoryModeTab {background:#142741;color:#ffffff;border:1px solid #a3d4ff;}
        QPushButton#InventoryModeTab:checked {background:#195c9a;border:2px solid #ffe28e;color:#ffffff;}
        QPushButton#TrackUnpreparedToggle:checked {background:#927038; color:#fff; border-color:#f5d183;}
        '''
    if name=='acik':
        return '''
        QWidget#AppRoot, QWidget#AppBody, QMainWindow,
        QDialog#OrderTrackWindow, QDialog#OrderEditWindow,
        QDialog#BookPoolDialog, QWidget#AnalyticsPage, QWidget#SettingsPage {
            background:#f6f1e8; color:#23384f;
        }
        QLabel {color:#30465d;}
        QLabel#Muted, QLabel#Tiny, QLabel#AnalyticsHint, QLabel#AccountingHelp {color:#6d7d8f;}
        QPushButton {
            background:#f1e8d8; color:#294158; border:1px solid #c7b89e;
        }
        QPushButton:hover {background:#eadfcb; border-color:#ad936f;}
        QPushButton:disabled, QToolButton:disabled, QComboBox:disabled,
        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
            background:#eee6da; color:#a19789; border:1px solid #d2c4b0;
        }
        QToolButton {background:#f1e8d8; color:#294158; border:1px solid #c7b89e;}
        QToolButton:hover {background:#eadfcb; border-color:#ad936f;}
        QPushButton#Accent {background:#d8a25f; color:#fffaf1; border-color:#c89557;}
        QPushButton#Success {background:#cde7d8; color:#24513f; border-color:#8ab79e;}
        QPushButton#Danger {background:#efd6d1; color:#723f44; border-color:#d3a0a0;}
        QPushButton#InventoryModeTab {background:#e8dcc9;color:#28485f;border:1px solid #ad9677;}
        QPushButton#InventoryModeTab:hover {background:#d5c2a6;color:#18334d;border-color:#a88c65;}
        QPushButton#InventoryModeTab:checked {background:#d8a45c;color:#17324b;border:2px solid #a97d3c;}
        QPushButton#Nav {color:#31506b; background:transparent;}
        QPushButton#Nav:hover {background:#efe4d4; color:#21405b;}
        QPushButton#Nav:checked {color:#21405b; background:#e2d2bb; border-bottom:2px solid #c89252;}
        QPushButton#SettingsGear {color:#2f4a62; background:#eee2d2; border-color:#c8b69f;}
        QPushButton#Segment:checked, QPushButton#OrderType:checked, QPushButton#SettingsNav:checked {
            background:#d8c3a5; color:#2f4359; border-color:#b38d61;
        }
        QCheckBox {color:#33485d;}
        QLineEdit, QComboBox, QSpinBox, QTextEdit, QDoubleSpinBox {
            background:#fbf7ef; color:#22384d; border:1px solid #cbbca5;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QDoubleSpinBox:focus {
            border-color:#c89252;
        }
        QComboBox QAbstractItemView {background:#fffaf2;color:#22384d;selection-background-color:#e8d9c5;}
        QTableWidget#AnalyticsDataTable {
            background:#fffaf4; color:#22384d; alternate-background-color:#f5eee4; gridline-color:#deceb7;
        }
        QHeaderView::section {background:#eadfcf;color:#2a435a;}
        QScrollBar:vertical, QScrollBar:horizontal {background:#e9decd;}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {background:#baa98d;}
        QFrame#Header, QFrame#OrdersSubbar {background:#f1e8dc; border-color:#d7c9b3;}
        QFrame#Panel, QFrame#Card, QFrame#OrderRow, QFrame#BasketRow,
        QFrame#CatalogToolbar, QFrame#BasketPanel, QFrame#BookHead, QFrame#BasketGroup,
        QFrame#CompactBookCard, QFrame#PortraitBookCard, QFrame#OrderToolbar,
        QFrame#OrderFilterSegment, QFrame#OrderEditPanel, QFrame#OrderEditBookRow,
        QFrame#TrackBookCard, QFrame#PoolBookRow, QFrame#PoolOrderLinks,
        QFrame#TrackVariantSB, QFrame#TrackVariantRNK,
        QFrame#AnalyticsMetric, QFrame#AnalyticsToolbar, QFrame#SettingsCard,
        QFrame#AnalyticsTable, QFrame#AuditEvent, QFrame#BookPoolToolbar,
        QFrame#AccountingCalendarPanel, QFrame#AccountingPill, QFrame#PoolOverviewGroup,
        QFrame#PoolOverviewBook {
            background:#fbf7ef; border:1px solid #d7c9b3;
        }
        QFrame#OrderRow:hover, QFrame#AnalyticsMetric:hover, QFrame#PoolOverviewBook:hover,
        QFrame#AccountingPill:hover {border:2px solid #c89252;}
        QFrame#TrackVariantSB {background:#efe8fb;border:1px solid #baaed6;}
        QFrame#TrackVariantRNK {background:#fff0e5;border:1px solid #ddb396;}
        QFrame#OrderRow[orderSelected="true"] {background:#efe8db;border:2px solid #b38655;}
        QLabel#BookName, QLabel#PortraitBookName, QLabel#TrackBookName,
        QLabel#PoolBookName, QLabel#OrderID, QLabel#OrderEditBookName,
        QLabel#TrackBookInfo, QLabel#BookPages, QLabel#AnalyticsCaption,
        QLabel#AnalyticsTitle, QLabel#AnalyticsSection, QLabel#AnalyticsTableTitle,
        QLabel#SettingsTitle, QLabel#SettingsHeading, QLabel#AuditHeading,
        QLabel#AuditDescription, QLabel#AuditChildTitle, QLabel#SettingsPath,
        QLabel#OrderMeta, QLabel#OrderMetrics, QLabel#OrderQuantity,
        QLabel#OrderDoneDate, QLabel#AccountingMonthTitle, QLabel#AccountingWeekday,
        QLabel#AccountingPeriod, QLabel#AccountingLegend, QLabel#AccountingSelection,
        QLabel#AccountingPillTitle {
            color:#2e465e;
        }
        QLabel#AnalyticsValue {color:#2b6588;}
        QLabel#OrderMoney, QLabel#AccountingPillValue {color:#1f7a63;}
        QLabel#OrderShippingCost {color:#7a4c28;background:#f7e4cc;border:1px solid #d6b28c;}
        QLabel#SettingsPath, QLabel#AccountingSelection {background:#f2eadf;border:1px solid #cfbea7;}
        QFrame#OrderEditRevenueBox {background:#f7efe4;border:1px solid #d5c0a1;}
        QLineEdit#OrderEditRevenueInput {color:#173b56;background:#fffaf2;}
        QLabel#OrderEditCurrencyLabel {color:#236e55;}
        QPushButton#AccountingMonthArrow, QPushButton#AccountingQuick {
            background:#e8dcc9; color:#294158; border:1px solid #c8b395;
        }
        QPushButton#AccountingMonthArrow:hover, QPushButton#AccountingQuick:hover {background:#ddceb7;}
        QPushButton#AccountingDay {
            background:#f7f1e7; color:#31485f; border:1px solid #d3c4ad;
        }
        QPushButton#AccountingDay:hover {background:#ebdec9; border:2px solid #c89252;}
        QPushButton#AccountingDay[outsideMonth="true"] {color:#9b907f;}
        QPushButton#AccountingDay[accountState="done"] {background:#e4bf62;color:#6a4713;border:1px solid #cf9d28;}
        QPushButton#AccountingDay[accountState="review"] {background:#edc887;color:#724c14;border:2px dashed #c89252;}
        QPushButton#AccountingDay[accountState="paid"] {background:#89bce4;color:#17334c;border:1px solid #5d99ca;}
        QPushButton#AccountingDay[accountState="active"] {background:#dfe9f1;color:#35516a;border:1px solid #acc0d1;}
        QPushButton#AccountingDay[selectedDay="true"] {border:3px solid #35516a;}
        QPushButton#AccountingPaidAction {background:#9fc7e6;color:#17334c;border:1px solid #5d99ca;}
        QPushButton#AccountingPaidAction:hover {background:#8bb8dc;}
        QPushButton#AccountingUnpaidAction {background:#eadfc9;color:#6c4d22;border:1px solid #c5a46a;}
        QPushButton#AccountingUnpaidAction:hover {background:#e0d1b5;}
        QLabel#BadgeSB {color:#6a5896; background:#ece5f7;}
        QLabel#BadgeRNK {color:#94552e; background:#f6e6da;}
        QWidget#StandaloneHeader, QWidget#StandaloneQuantities,
        QWidget#StandaloneCounterSB, QWidget#StandaloneCounterRNK {border-color:#ccb9a1;}
        QWidget#StandaloneCounterSB {background:#e9e3f3;}
        QWidget#StandaloneCounterRNK {background:#f3dfd3;}
        QFrame#AnalyticsMetricGroup {background:#f4ebdd; border:1px solid #d8c6ad;}
        QLabel#AnalyticsGroupTitle {color:#45536b; background:transparent;}
        QLabel#AnalyticsGroupTitle[groupKind="finance"] {color:#17765a;}
        QLabel#AnalyticsGroupTitle[groupKind="shipping"] {color:#98611e;}
        QLabel#AnalyticsGroupTitle[groupKind="orders"] {color:#236c9e;}
        QLabel#AnalyticsGroupTitle[groupKind="books"] {color:#7453a0;}
        QLabel#AnalyticsGroupTitle[groupKind="printing"] {color:#a95436;}
        QFrame#CompletedArchiveBar {background:#f4e9d7; border:1px solid #d3bea0;}
        QLabel#ArchiveStatus {color:#40516a;}
        QPushButton#ArchiveToggle {background:#edd2a5; color:#694719; border:1px solid #c5a071;}
        QPushButton#ArchiveToggle:hover {background:#e5c392; border-color:#b58a50;}
        QPushButton#ArchiveLoadMore {background:#e3dfd1; color:#38536d; border:1px solid #afc0c3;}
        QPushButton#ArchiveLoadMore:hover {background:#d5d9c9;}
        QLabel#StandaloneName, QLabel#StandalonePages, QLabel#StandaloneCount,
        QLabel#StandaloneSB, QLabel#StandaloneRNK {color:#284158;}
        /* Üst işlem butonları her temada eş biçimde görünmeli. */
        QPushButton#OrderPoolCTA, QPushButton#OrderPrintCTA {
            border-radius:9px; font-size:12px; font-weight:900;
            padding:6px 13px; min-height:0; max-height:38px;
        }
        QPushButton#OrderPoolCTA {
            background:#ded2ed; color:#523d76; border:1px solid #b9a2ce;
        }
        QPushButton#OrderPoolCTA:hover {background:#d0bfdf; border-color:#8f6eae;}
        QPushButton#OrderPoolCTA:pressed {background:#c3add8;}
        QPushButton#OrderPrintCTA {
            background:#f1ca95; color:#563715; border:1px solid #d3a46c;
        }
        QPushButton#OrderPrintCTA:hover {background:#e7b878; border-color:#bc8240;}
        QPushButton#OrderPrintCTA:pressed {background:#dca568;}
        QPushButton#OrderPrintCTA:disabled {
            background:#efe7da; color:#9d907f; border:1px solid #d5c9b9;
        }
        QPushButton#Success:hover {background:#b5dcc6; color:#24513f; border-color:#6fa88a;}
        QPushButton#Success:disabled {background:#e2e4dc; color:#8b9990; border-color:#c6cec1;}
        QFrame#OrderToolbar {background:#f8f2e9; border:1px solid #d6c5ab;}
        QFrame#OrderFilterSegment {background:#eee3d3; border:1px solid #d4c3aa;}
        QLineEdit#OrderSearch, QComboBox#OrderFilter, QPushButton#CalendarTrigger,
        QPushButton#OrderReset, QToolButton#OrderSortReverse {
            background:#fcf8f1; color:#30475d; border:1px solid #cbbba5;
            border-radius:8px;
        }
        QLineEdit#OrderSearch:focus, QComboBox#OrderFilter:focus,
        QPushButton#CalendarTrigger:focus, QPushButton#OrderReset:focus,
        QToolButton#OrderSortReverse:focus {border-color:#bc8b52;}
        QFrame#OrderRow[orderStatus="havuz"] {border-left:3px solid #c49b64;}
        QFrame#OrderRow[orderStatus="aktif"] {border-left:3px solid #659bc3;}
        QFrame#OrderRow[orderStatus="tamamlandi"] {border-left:3px solid #6ba88b;}
        QFrame#OrderRow:hover {background:#fcf5e9; border-color:#b99b73;}
        QFrame#OrderRow[orderSelected="true"] {background:#f1e7f9; border:2px solid #9b79bb;}
        QFrame#OrderRow[orderRecent="true"] {background:#e6f1f5; border:2px solid #6aa6c9;}
        QFrame#OrderRow[orderFocused="true"] {border:2px solid #c69651;}
        QDialog#OrderTrackTabsWindow {background:#f6f1e8;}
        QFrame#TrackTabsHeader {background:#eadfce; border:1px solid #ccb99d;}
        QLabel#TrackTabsHeading {color:#2c4a64;}
        QLabel#TrackTabsHelp {color:#6c7c8d;}
        QLabel#TrackTabsCount {background:#f6eee1; color:#38546b; border:1px solid #cbb89c;}
        QTabWidget#OrderTrackTabs::pane {background:#fbf7ef; border:1px solid #d1c0a9;}
        QTabBar#OrderTrackTabBar::tab {background:#e9ddca; border-color:#cdbba1; color:#36516b;}
        QTabBar#OrderTrackTabBar::tab:selected {background:#f9f1e6; border-color:#b68b55; border-bottom:3px solid #c89457; color:#25415b;}
        QTabBar#OrderTrackTabBar::tab:hover {background:#f3e7d5;}
        QFrame#TrackActionToolbar {background:#f6eee3; border:1px solid #d0bea5;}
        QLabel#TrackActionsHeading, QLabel#TrackControlsCaption {color:#456783;}
        QFrame#TrackZoneDivider {background:#ccb99e;}
        QFrame#OrderRightPanel {background:#f5ecdf; border:1px solid #d4c2a9;}
        QFrame#OrderProgressGroup {background:#fcf7ef; border:1px solid #d5c8b5;}
        QLabel#OrderProgressCaption {color:#45617a;}
        QLabel#OrderProgressNumber {color:#29455e;}
        QLabel#OrderPoolInfo {color:#8f621e;}
        QLabel#PoolActiveScope {background:#d9e9dd; color:#28644d; border:1px solid #90bea4;}
        QFrame#TrackActionReady {background:#eae5f5; border:1px solid #b3a5d4;}
        QFrame#TrackActionBoxed {background:#dbefea; border:1px solid #8fbdb4;}
        QLabel#TrackActionLabel {color:#405770;}
        QPushButton#TrackBulkPositive {background:#a8dfc4; color:#1e5a42; border:1px solid #77bd9a;}
        QPushButton#TrackBulkPositive:hover {background:#8cd6b4; border-color:#469e76;}
        QPushButton#TrackBulkNegative {background:#e1e7ec; color:#35536d; border:1px solid #adbccd;}
        QPushButton#TrackBulkNegative:hover {background:#cfdce6; border-color:#789bb8;}
        QPushButton#TrackBulkPositive:disabled, QPushButton#TrackBulkNegative:disabled {background:#e7e2d9; color:#a8a097; border-color:#d0c7b7;}
        QFrame#TrackActionToolbar {border-color:#c8b49b;}

        QFrame#OrderToolbar QLineEdit#OrderSearch,
        QFrame#OrderToolbar QComboBox#OrderFilter,
        QFrame#OrderToolbar QPushButton#CalendarTrigger,
        QFrame#OrderToolbar QPushButton#OrderReset,
        QFrame#OrderToolbar QToolButton#OrderSortReverse {
            background:#fcf8f1; color:#30475d; border:1px solid #cbbba5;
        }
        QFrame#OrderToolbar QLineEdit#OrderSearch:hover,
        QFrame#OrderToolbar QComboBox#OrderFilter:hover,
        QFrame#OrderToolbar QPushButton#CalendarTrigger:hover,
        QFrame#OrderToolbar QPushButton#OrderReset:hover,
        QFrame#OrderToolbar QToolButton#OrderSortReverse:hover {
            background:#f3e8d9; border-color:#bc8b52;
        }
        QFrame#OrderToolbar QLabel#OrderMetrics {color:#3c566e;}
        QLabel#OrderSelectedCount {
            color:#31506a; background:#ede3d3; border:1px solid #cbb89d;
        }
        QWidget#CatalogToolbar, QFrame#CatalogToolbar {
            background:#f7efe4; border:1px solid #d6c5ab; border-radius:10px;
        }
        QWidget#CatalogToolbar QLineEdit {
            background:#fffaf3; color:#294158; border:1px solid #ccb79d; border-radius:9px;
            padding:8px 12px;
        }
        QWidget#CatalogToolbar QLineEdit:focus {border-color:#bc8b52;}
        QWidget#CatalogToolbar QLabel#Muted {color:#6d7d8f;}
        QFrame#BasketPanel {
            background:#f7efe4; border-left:1px solid #d7c7af; border-top:0; border-right:0; border-bottom:0;
        }
        QFrame#BasketTotals {background:transparent; border-top:1px solid #d8c7af;}
        QFrame#BasketGroup {background:#fbf6ef; border:1px solid #d9c9b0; border-radius:10px;}
        QFrame#BasketRow {background:#f9f3ea; border:1px solid #ddceb8;}
        QLabel#BasketGroupTitle {color:#8f6228;}
        QPushButton#DangerText {color:#b45a67; background:transparent; border:0;}
        QPushButton#DangerText:hover {color:#8d3f4b; background:#f4e7e4; border-radius:6px;}
        QPushButton#QuickSB {background:#e8def6; color:#5a4a86; border:1px solid #b9a6d2;}
        QPushButton#QuickSB:hover {background:#ddd0f0; border-color:#8c71b2;}
        QPushButton#QuickRNK {background:#f1ddcf; color:#8b5735; border:1px solid #d6af91;}
        QPushButton#QuickRNK:hover {background:#e9ceb8; border-color:#bc835c;}
        QPushButton#OrderType {background:#ebe0d1; color:#52657a; border:1px solid #d4c2a8;}
        QPushButton#OrderType:hover {background:#e1d3c0;}
        QWidget#FloatingPrice {background:transparent; border:0;}
        QLineEdit#FloatingPriceInput {
            background:rgba(255,250,242,0.92); color:#2d455c; border:1px solid #ccb89e;
        }
        QLineEdit#FloatingPriceInput:focus {background:#fffaf2; border-color:#bc8b52;}
        QLabel#FloatingPriceLabel {background:transparent;}
        QFrame#BookHead {background:#eae0d2; border:1px solid #d2bea3;}
        QLabel#BookName {color:#294158;}
        QLabel#BookPages {color:#a26c34;}
        QCheckBox#BookSelect {color:#6b7a8d;}
        QFrame#PoolOverviewGroup {background:#f8f1e7; border:1px solid #d8c7af;}
        QFrame#PoolOverviewBook {background:#fbf7ef; border:1px solid #d7c7ae;}
        QFrame#PoolOverviewBook:hover {border:2px solid #bc8b52;}
        QMenu#OrdersHoverMenu {background:#fffaf2; border:1px solid #d4c3aa; border-top:2px solid #c89252;}
        QMenu#OrdersHoverMenu::item {color:#2d465d;}
        QMenu#OrdersHoverMenu::item:selected {background:#efe4d4; color:#8a6129;}
        QTabWidget#OrderTrackTabs::pane {background:#fbf7ef; border:1px solid #d1c0a9;}
        QProgressBar {background:#e7dccd;}
        QProgressBar::chunk {background:#6fa88a;}

        /* V4.35: complete light-mode coverage for interactive components. */
        QWidget#StandaloneHeader {
            background:#e9dcc8; border:1px solid #cbb89d; border-bottom:0;
        }
        QWidget#StandaloneHeader:hover {background:#e4d4bd; border-color:#b9986c;}
        QLabel#StandaloneName {color:#2e455e; background:transparent;}
        QLabel#StandalonePages {color:#87633e; background:transparent;}
        QWidget#StandaloneQuantities {border-color:#c7b79f;}
        QWidget#StandaloneCounterSB {background:#ddd4ee;}
        QWidget#StandaloneCounterRNK {background:#edd0b8;}
        QWidget#StandaloneCounterSB QLabel#StandaloneSB,
        QWidget#StandaloneCounterRNK QLabel#StandaloneRNK,
        QLabel#StandaloneCount {color:#2d4055;}
        QWidget#StandaloneCounterSB QPushButton#StandaloneStep {
            background:#a494cb; color:#1f1d3d; border:0;
        }
        QWidget#StandaloneCounterRNK QPushButton#StandaloneStep {
            background:#c99673; color:#422910; border:0;
        }
        QWidget#StandaloneCounterSB QPushButton#StandaloneStep:hover {background:#8975b8; color:white;}
        QWidget#StandaloneCounterRNK QPushButton#StandaloneStep:hover {background:#ba7d55; color:white;}
        QPushButton#OrdersSubnav[orderStage="havuz"] {color:#93632a; background:transparent;}
        QPushButton#OrdersSubnav[orderStage="aktif"] {color:#326b97; background:transparent;}
        QPushButton#OrdersSubnav[orderStage="tamamlandi"] {color:#267a5d; background:transparent;}
        QPushButton#OrdersSubnav[orderStage="havuz"]:hover {
            background:#eedcc1; color:#704b23;
        }
        QPushButton#OrdersSubnav[orderStage="aktif"]:hover {
            background:#dcebf3; color:#215778;
        }
        QPushButton#OrdersSubnav[orderStage="tamamlandi"]:hover {
            background:#d8ebdd; color:#1f694f;
        }
        QPushButton#OrdersSubnav[orderStage="havuz"]:checked {
            background:#e5cba7; color:#61401c; border-bottom:3px solid #b8874b;
        }
        QPushButton#OrdersSubnav[orderStage="aktif"]:checked {
            background:#d2e3ef; color:#244d6a; border-bottom:3px solid #5a99c3;
        }
        QPushButton#OrdersSubnav[orderStage="tamamlandi"]:checked {
            background:#cfe6d8; color:#235e49; border-bottom:3px solid #60a77e;
        }
        QFrame#OrderToolbar QLineEdit#OrderSearch {
            background:#fffbf4; color:#2a4059; border:1px solid #cbb99e;
        }
        QFrame#OrderToolbar QLineEdit#OrderSearch:hover {
            background:#fffdf8; border-color:#b79c79;
        }
        QFrame#OrderToolbar QLineEdit#OrderSearch:focus {
            background:#fffdf8; border:2px solid #c79556;
            selection-background-color:#ead1a9; selection-color:#223b54;
        }
        QPushButton#CopyCode {
            background:#efe7da; color:#2d445a; border:1px solid #c7b69c;
            text-align:left;
        }
        QPushButton#CopyCode:hover {background:#e5d9c7; color:#213d55; border-color:#ae9169;}
        QPushButton#CopyCode:pressed {background:#dbcbb5;}
        QFrame#OrderRow[orderStatus="havuz"],
        QFrame#OrderRow[orderStatus="aktif"],
        QFrame#OrderRow[orderStatus="tamamlandi"] {
            background:#faf5ed; border-top:1px solid #d7c6ad;
            border-right:1px solid #d7c6ad; border-bottom:1px solid #d7c6ad;
        }
        QFrame#OrderRow[orderStatus="havuz"] {border-left:3px solid #bb995f;}
        QFrame#OrderRow[orderStatus="aktif"] {border-left:3px solid #6a9fbf;}
        QFrame#OrderRow[orderStatus="tamamlandi"] {border-left:3px solid #77ae92;}
        QFrame#OrderRow[orderStatus="havuz"]:hover {background:#f5e9d7; border-color:#b99a71;}
        QFrame#OrderRow[orderStatus="aktif"]:hover {background:#edf3f6; border-color:#83a8c2;}
        QFrame#OrderRow[orderStatus="tamamlandi"]:hover {background:#e8f2e9; border-color:#81b498;}
        QFrame#OrderRow[orderSelected="true"],
        QFrame#OrderRow[orderSelected="true"]:hover {
            background:#ede4f5; border:2px solid #9e7cb9;
        }
        QFrame#OrderRow[orderRecent="true"],
        QFrame#OrderRow[orderRecent="true"]:hover {
            background:#e0eef4; border:2px solid #70a9c8;
        }
        QFrame#OrderRow[orderFocused="true"] {border:2px solid #b8894e;}
        QFrame#OrderRow[orderSelected="true"][orderRecent="true"] {
            background:#e7e1f2; border:2px solid #a181bf;
        }
        QLabel#OrderID, QLabel#OrderMeta, QLabel#OrderMetrics,
        QLabel#OrderProgressCaption, QLabel#OrderProgressNumber {color:#2e455a;}
        QLabel#OrderDoneTag {background:#d6ecdf; color:#2c7356; border:1px solid #8dbc9f;}
        QLabel#OrderDoneDate {color:#38795e;}
        QProgressBar#ReadyProgress, QProgressBar#BoxProgress {background:#dce2e2;}
        QProgressBar#ReadyProgress::chunk {background:#78afe2;}
        QProgressBar#BoxProgress::chunk {background:#79bea0;}
        QPushButton#DetailAction, QToolButton#MoreActions {
            background:#efe6d7; color:#2b455e; border:1px solid #cbb69a;
        }
        QPushButton#DetailAction:hover, QToolButton#MoreActions:hover {
            background:#e2d3be; color:#23415b; border-color:#ae8f67;
        }
        QPushButton#DetailAction:disabled, QToolButton#MoreActions:disabled {
            background:#eee8dd; color:#a09689;
        }
        QMenu#OrderActionsMenu {background:#fffaf2; border:1px solid #d2c0a9;}
        QMenu#OrderActionsMenu::item {color:#294257;}
        QMenu#OrderActionsMenu::item:selected {background:#ebddca; color:#4b3621;}
        QMenu#OrderActionsMenu::separator {background:#d7c5b0;}
        QDialog#OrderTrackTabsWindow, QDialog#OrderTrackWindow {background:#f6f0e6;}
        QFrame#TrackTabsHeader {background:#eee2d0; border:1px solid #cdb99d;}
        QLabel#TrackTabsHeading {color:#2d4b64;}
        QLabel#TrackTabsHelp {color:#687a89;}
        QLabel#TrackTabsCount {background:#f9f1e5; color:#36516a; border:1px solid #d0bda3;}
        QTabWidget#OrderTrackTabs::pane {
            background:#faf5ec; border:1px solid #cfbca0;
        }
        QTabBar#OrderTrackTabBar::tab {
            background:#e9dcc9; color:#2a4860; border:1px solid #c6b297;
            border-bottom:2px solid #c6b297;
        }
        QTabBar#OrderTrackTabBar::tab:hover {
            background:#decab0; color:#25435b; border-color:#a98a60;
        }
        QTabBar#OrderTrackTabBar::tab:selected {
            background:#d7e5ec; color:#25435b; border:1px solid #8eafc3;
            border-bottom:3px solid #5e91ad;
        }
        QFrame#TrackActionToolbar {background:#f3e8d9; border:1px solid #c7af8f;}
        QLabel#TrackActionsHeading, QLabel#TrackControlsCaption {color:#36566f;}
        QLabel#TrackActionLabel {color:#36556d; background:transparent;}
        QPushButton#TrackSelectAllToggle, QPushButton#TrackUnpreparedToggle {
            background:#e9dfcf; color:#304b62; border:1px solid #bfa98b;
            min-height:0; max-height:44px;
        }
        QPushButton#TrackSelectAllToggle:hover, QPushButton#TrackUnpreparedToggle:hover {
            background:#deceb9; color:#263f56; border-color:#a78c68;
        }
        QPushButton#TrackSelectAllToggle:checked {
            background:#d9c6ea; color:#533d73; border:1px solid #ac91c5;
        }
        QPushButton#TrackSelectAllToggle:checked:hover {background:#cdb6e2;}
        QPushButton#TrackUnpreparedToggle:checked {
            background:#f1d6a7; color:#785123; border:1px solid #c7a06b;
        }
        QPushButton#TrackUnpreparedToggle:checked:hover {background:#ebc68d;}
        QFrame#TrackActionReady {background:#e9e2f3; border:1px solid #b6a3d0;}
        QFrame#TrackActionReady:hover {background:#e0d4f1; border-color:#9d7bc6;}
        QFrame#TrackActionBoxed:hover {background:#c9e7da; border-color:#67a58c;}
        QFrame#TrackActionBoxed {background:#def0e9; border:1px solid #8cbfad;}
        QPushButton#PdfAction, QPushButton#TrackPdfButton {
            background:#e4e6e1; color:#2c4c63; border:1px solid #b4b9ae;
        }
        QPushButton#PdfAction:hover, QPushButton#TrackPdfButton:hover {
            background:#d2dfdb; border-color:#7ba59f;
        }
        QFrame#TrackBookCard {background:#fbf7ef; border:1px solid #d7c5a8;}
        QFrame#TrackBookCard:hover {background:#f3ebdd; border:1px solid #bfa076;}
        QFrame#TrackBookCard[trackSelected="true"] {background:#eee6f4; border:2px solid #af91c8;}
        QFrame#TrackBookCard[trackRecent="true"] {background:#e8f1f3; border:2px solid #81adbd;}
        QFrame#TrackBookCard[trackSelected="true"][trackRecent="true"] {
            background:#e9e4f1; border:2px solid #a789bf;
        }
        QWidget#TrackControlZone, QWidget#TrackCoverZone {background:transparent;}
        QFrame#TrackZoneDivider {background:#cfbfaa;}
        QLabel#TrackBookName {color:#30465d;}
        QLabel#TrackBookInfo {color:#6e7984;}
        QLabel#TrackCode {background:#efe5d5; color:#976b36; border:1px solid #d1b998;}
        QLabel#TrackVariantTitleSB {color:#71579a;}
        QLabel#TrackVariantTitleRNK {color:#a5663c;}
        QLabel#TrackVariantAmount, QLabel#TrackStepLabel {color:#425a72;}
        QLabel#TrackStepCount {background:#fffaf2; color:#29445d; border:1px solid #c9b69a;}
        QPushButton#TrackStep {background:#e5d8c5; color:#29465e; border:1px solid #c9b397;}
        QPushButton#TrackStep:hover {background:#d7c3a8; border-color:#a7885f;}
        QPushButton#TrackStep:disabled {background:#eee9df; color:#999b93; border-color:#d4caba;}
        QLabel#TrackFilterEmpty {background:#f5eee2; border:1px dashed #c9ad89; color:#516a7b;}
        QFrame#TrackVariantSB {background:#ece5f7; border:1px solid #baabda;}
        QFrame#TrackVariantRNK {background:#f6e6d9; border:1px solid #d8ab8a;}
        QPushButton#TrackBulkPositive {background:#a8dcc2; color:#245540; border:1px solid #76b594;}
        QPushButton#TrackBulkPositive:hover {background:#8dceb0; color:#214e3b;}
        QPushButton#TrackBulkNegative {background:#e2e9e9; color:#395669; border:1px solid #adc0c5;}
        QPushButton#TrackBulkNegative:hover {background:#d1dfe1; color:#305265;}
        QPushButton#TrackBulkPositive:disabled, QPushButton#TrackBulkNegative:disabled {
            background:#eee9df; color:#a39d91; border:1px solid #d5cabc;
        }
        QCheckBox::indicator:unchecked {background:#fffaf2; border:1px solid #9d9b90;}
        QCheckBox::indicator:checked {background:#bd9665; border:1px solid #9f7747;}

        /* V4.36: son açık tema kaçakları ve takvim/detay iyileştirmeleri. */
        QPushButton#SmallAction, QPushButton#CalendarArrow,
        QPushButton#AnalyticsExport, QPushButton#SettingsNav,
        QPushButton#ArchiveLoadMore {
            background:#efe5d6; color:#2d455b; border:1px solid #c8b79e;
        }
        QPushButton#SmallAction:hover, QPushButton#CalendarArrow:hover,
        QPushButton#AnalyticsExport:hover, QPushButton#SettingsNav:hover,
        QPushButton#ArchiveLoadMore:hover {
            background:#e5d8c6; color:#213e56; border-color:#ae9168;
        }
        QDialog#DatePickerDialog {
            background:#f6f0e6; color:#294158; border:1px solid #cfbea6;
        }
        QLabel#CalendarTitle {color:#24435b; font-size:15px; font-weight:900;}
        QLabel#CalendarHelp, QLabel#CalendarSelection {color:#5d7186;}
        QLabel#CalendarMonth {color:#28445d; font-size:13px; font-weight:900;}
        QLabel#CalendarWeekday {color:#6f8093; font-weight:800;}
        QPushButton#CalendarArrow {
            background:#efe5d6; color:#32506a; border:1px solid #c8b69f; border-radius:10px;
        }
        QPushButton#CalendarArrow:hover {background:#e2d3bd; border-color:#ae8d63;}
        QPushButton#CalendarDay {
            background:#fbf7ef; color:#2f4860; border:1px solid #d3c5b0; border-radius:10px;
            font-weight:800;
        }
        QPushButton#CalendarDay:hover {background:#f2e7d7; border-color:#bc9159;}
        QPushButton#CalendarDay[otherMonth="true"] {
            background:#f3ecdf; color:#a1937f; border:1px solid #e0d3c0;
        }
        QPushButton#CalendarDay[hasOrder="true"] {
            background:#d8ece2; color:#285d4a; border:2px solid #80c5a2;
        }
        QPushButton#CalendarDay[selectedDay="true"] {
            background:#ead6b8; color:#5f411a; border:2px solid #cc9959;
        }
        QPushButton#CalendarDay[hasOrder="true"][selectedDay="true"] {
            background:#dbe8d8; color:#36533f; border:2px solid #b28a57;
        }
        QLabel#CalendarMarker {color:#4da57d;}
        QDialog#OrderEditWindow, QDialog#OrderTrackWindow, QDialog#OrderTrackTabsWindow {
            background:#f6f0e6;
        }
        QFrame#OrderEditPanel, QFrame#OrderEditBookRow,
        QFrame#OrderArchiveHeader, QFrame#OrderArchiveCard {
            background:#fbf7ef; border:1px solid #d6c6ae;
        }
        QFrame#OrderEditBookRow:hover, QFrame#OrderArchiveCard:hover {
            background:#f2e8da; border-color:#ba8f5a;
        }
        QLabel#OrderEditSection {color:#48627c;}
        QLabel#OrderEditPlatform {
            background:#dfeaf0; color:#254d6b; border:1px solid #adc0cd;
        }
        QComboBox#OrderBookSearch {
            background:#fffaf2; color:#294158; border:1px solid #ccb79d;
        }
        QComboBox#OrderBookSearch:hover {background:#f6efe3; border-color:#b99261;}
        QComboBox#OrderBookSearch:focus {border:2px solid #c79556;}
        QFrame#PoolBookRow:hover {background:#f1e8da; border:1px solid #b58d5c;}
        QFrame#PoolBookRow[poolRecent="true"] {background:#e6f0ef; border:1px solid #8eb8b1;}
        QPushButton#AccountingPaidAction:disabled, QPushButton#AccountingUnpaidAction:disabled {
            background:#eee6da; color:#a19789; border:1px solid #d2c4b0;
        }
        QPushButton#AccountingDay[selectedDay="true"] {border:3px solid #bc8b52;}
        QPushButton#AccountingDay[outsideMonth="true"] {
            background:#f3ecdf; color:#a1937f; border:1px solid #e0d3c0;
        }
        QPushButton#AccountingDay[selectedDay="true"][accountState="done"] {border:3px solid #8d671f;}
        QPushButton#AccountingDay[selectedDay="true"][accountState="paid"] {border:3px solid #4678a6;}
        QPushButton#AccountingDay[selectedDay="true"][accountState="active"] {border:3px solid #8c6f46;}
        QPushButton#AccountingDay[selectedDay="true"][accountState="review"] {border:3px solid #b37f3a;}
        QPushButton#DetailAction:pressed, QToolButton#MoreActions:pressed,
        QPushButton#SmallAction:pressed, QPushButton#CalendarArrow:pressed {
            background:#dcc9b2;
        }
        QFrame#OrderRightPanel {background:#f6efe4; border:1px solid #c8b89f;}
        QFrame#OrderProgressGroup {background:#fcf7ef; border:1px solid #d3c5b1;}
        QPushButton#DetailAction, QToolButton#MoreActions {
            background:#efe6d7; color:#2b455e; border:1px solid #cbb69a;
        }
        QPushButton#DetailAction:hover, QToolButton#MoreActions:hover {
            background:#e5d7c3; color:#23415b; border-color:#ae8f67;
        }
        QPushButton#OrderPoolCTA:disabled, QPushButton#OrderPrintCTA:disabled {
            background:#eee6da; color:#a19789; border:1px solid #d2c4b0;
        }
                QFrame#OrderRightPanel {border-color:#c8b89f;}
        '''
    # Koyu tema tamamen temel QSS üzerinden uygulanır; eski açık tema
    # bloğunun bu yoldan kazara yüklenmesini önlüyoruz.
    return ''
