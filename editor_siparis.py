"""Yerel Qt pencereleri: takip ve düzenleme ayrı açılır."""
from pathlib import Path
from utils import otomatik_platform_bul, format_kargo_kodu
from PySide6.QtCore import Qt, QUrl, QTimer, QMimeData, Signal
from PySide6.QtGui import QDesktopServices, QColor, QDrag
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QFrame, QLabel, QScrollArea,
    QCheckBox, QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QFormLayout, QGridLayout, QAbstractSpinBox,
    QMessageBox, QFileDialog, QTabWidget, QTabBar, QPushButton, QSizePolicy, QApplication
)
from widgets import text, button, cover_label, scrollable, clear_layout, error, confirm
from kart_siparis import ProgressCover
from pdf_kitap import PdfKutuphane
from ilerleme_kontrol import sonraki_ilerleme, buton_durumlari


def ciro_metinini_sayiya_cevir(raw):
    """Accept TR/EN money input without rewriting text/caret during entry."""
    import re
    value = str(raw).strip().replace('\u00a0', '').replace(' ', '').replace('₺', '')
    value = re.sub(r'(?i)tl$', '', value)
    if not value:
        return 0.0
    if not re.fullmatch(r'[0-9.,]+', value):
        raise ValueError('Ciro için yalnızca rakam, virgül ve nokta kullanın.')
    if ',' in value and '.' in value:
        decimal = ',' if value.rfind(',') > value.rfind('.') else '.'
    elif ',' in value:
        decimal = ',' if len(value.rsplit(',', 1)[-1]) <= 2 else None
    elif '.' in value:
        decimal = '.' if len(value.rsplit('.', 1)[-1]) <= 2 else None
    else:
        decimal = None
    if decimal:
        integral, fraction = value.rsplit(decimal, 1)
        normalized = integral.replace(',', '').replace('.', '') + '.' + fraction
    else:
        normalized = value.replace(',', '').replace('.', '')
    try:
        amount = float(normalized)
    except ValueError as exc:
        raise ValueError('Geçerli bir ciro tutarı girin.') from exc
    if not 0 <= amount < 1_000_000_000:
        raise ValueError('Ciro tutarı 0 ile 1 milyar TL arasında olmalıdır.')
    return round(amount, 2)


class SiparisEditor(QDialog):
    def __init__(self, db, covers, sid, on_updated, parent=None, mode='track', embedded=False):
        super().__init__(parent)
        self.db = db
        self.covers = covers
        self.sid = sid
        self.on_updated = on_updated
        self.mode = mode
        self.pdfs = PdfKutuphane(Path(db.sepet_dosyasi).parent)
        self.embedded = embedded
        if embedded:
            # A QDialog embedded in QTabWidget must behave like a QWidget.
            self.setWindowFlags(Qt.WindowType.Widget)
        self._track_columns = None
        self._track_layout_signature = None
        self._bulk_toolbar_layout_mode = None
        self._track_cards = []
        self.track_scroll = None
        self.code_checks = {}
        self.track_variant_widgets = {}
        self.track_covers = {}
        self.header_summary = None
        self._recent_code = None
        self.track_cards_by_code = {}
        self._rendered_status = None
        self._parent_refresh_timer = QTimer(self)
        self._parent_refresh_timer.setSingleShot(True)
        self._parent_refresh_timer.setInterval(140)
        self._parent_refresh_timer.timeout.connect(self.on_updated)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        if mode == 'edit':
            self.setObjectName('OrderEditWindow')
            self.setWindowTitle(f'ALFA ERP · Sipariş #{sid} · Sipariş Düzenle')
            self.resize(1050, 780)
            self.setMinimumSize(760, 520)
        else:
            self.setObjectName('OrderTrackWindow')
            self.setWindowTitle(f'ALFA ERP · Sipariş #{sid} · Kitap Takibi')
            self.resize(1180, 740)
            # Embedded pages must not force their parent tab pane to be wider
            # than the available window: that clipped the lower control bar.
            self.setMinimumSize(0, 0) if embedded else self.setMinimumSize(920, 600)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(14, 12, 14, 14)
        self.root.setSpacing(10)
        self.header_lay = QHBoxLayout()
        self.header_lay.setSpacing(8)
        self.root.addLayout(self.header_lay)
        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 0, 0, 0)
        self.body_lay.setSpacing(9)
        self.root.addWidget(self.body, 1)
        self.build_ui()

    def current(self):
        return next((x for x in self.db.siparisler if str(x.get('id')) == str(self.sid)), None)

    def build_ui(self):
        clear_layout(self.header_lay)
        clear_layout(self.body_lay)
        order = self.current()
        if not order:
            self.header_lay.addWidget(text('Sipariş bulunamadı', 'PageTitle'))
            return

        self._rendered_status = self.db.siparis_durumu(order)
        if self.mode == 'edit':
            self.header_lay.addWidget(text(f'Sipariş #{self.sid} · Düzenleme', 'PageTitle'))
            self.header_lay.addWidget(text('Kargo, platform, ciro ve kitap adetlerini güncelle.', 'Muted'))
        else:
            summary = self.db.siparis_ozeti(order)
            self.header_lay.addWidget(text(f'Sipariş #{self.sid} · ' + ('Kitap Listesi' if self._rendered_status=='havuz' else 'Kitap Takibi'), 'PageTitle'))
            badge_role = {'aktif':'OrderStatusBadgeActive', 'tamamlandi':'OrderStatusBadgeDone', 'havuz':'OrderStatusBadgePool'}.get(self._rendered_status, 'OrderStatusBadgePool')
            stage_name = {'aktif':'● AKTİF', 'tamamlandi':'✓ TAMAMLANDI', 'havuz':'○ HAVUZ'}.get(self._rendered_status, '')
            self.header_lay.addWidget(text(stage_name, badge_role))
            self.header_summary = text(f"SB {summary['sb']} · RNK {summary['rnk']} · Hazır {summary['hazir']}/{summary['adet']} · Koli {summary['koli']}/{summary['adet']}", 'Muted')
            self.header_lay.addWidget(self.header_summary)
        self.header_lay.addStretch()
        close = button('Sekmeyi kapat' if self.embedded else 'Kapat')
        close.clicked.connect(lambda: self.track_host.close_order_tab(self.sid) if self.embedded and hasattr(self, 'track_host') else self.close())
        self.header_lay.addWidget(close)

        if self.mode == 'edit':
            self.build_edit()
        elif self.db.siparis_durumu(order) == 'tamamlandi':
            self.build_archive()
        elif self.db.siparis_durumu(order) == 'havuz':
            self.build_pool_overview()
        else:
            self.build_track()

    def build_pool_overview(self):
        """Havuzdaki kitapları baskı işlemleri olmadan grup grup göster."""
        order = self.current()
        summary = self.db.siparis_ozeti(order)
        self.header_summary.setText(
            f"{summary['adet']} kitap · {summary['sayfa']:,} sayfa · SB {summary['sb']} / RNK {summary['rnk']}")
        heading = text('SİPARİŞ HAVUZU · KİTAP LİSTESİ', 'OrderEditSection')
        self.body_lay.addWidget(heading)
        groups = {}
        for entry in self.db.siparis_gruplari(order):
            group_name = str(entry.get('kitap_grubu') or 'Diğer')
            groups.setdefault(group_name, []).append(entry)
        view = QWidget(); outer = QVBoxLayout(view)
        outer.setContentsMargins(2,2,7,8); outer.setSpacing(12)
        for group_name, books in groups.items():
            group_frame=QFrame();group_frame.setObjectName('PoolOverviewGroup')
            group_lay=QVBoxLayout(group_frame)
            group_lay.setContentsMargins(12,10,12,12);group_lay.setSpacing(9)
            total = sum(int(b.get('adet',0)) for b in books)
            group_lay.addWidget(text(f'{group_name}   ·   {len(books)} çeşit / {total} kitap','PoolOverviewHeading'))
            grid=QGridLayout();grid.setSpacing(9)
            for idx,entry in enumerate(books):
                code=str(entry['kod'])
                book=self.db.katalog.get(code, {'kod':code,'isim':entry['isim']})
                card=QFrame();card.setObjectName('PoolOverviewBook')
                lay=QHBoxLayout(card);lay.setContentsMargins(8,7,8,7);lay.setSpacing(9)
                lay.addWidget(cover_label(book,self.covers,75,107))
                info=QVBoxLayout();info.setSpacing(5)
                title=text(entry['isim'],'TrackBookName',wrap=True)
                info.addWidget(title)
                info.addWidget(text(f"#{code} · {entry.get('sayfa_birim',0)} sayfa",'Muted'))
                info.addWidget(text(f"SB {entry.get('sb',0)}  ·  RNK {entry.get('rnk',0)}",'PoolOverviewCounts'))
                info.addStretch()
                lay.addLayout(info,1)
                grid.addWidget(card,idx//3,idx%3)
            group_lay.addLayout(grid)
            outer.addWidget(group_frame)
        if not groups:
            outer.addWidget(text('Siparişte henüz kitap bulunmuyor.','Muted'))
        outer.addStretch()
        area=scrollable(view)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body_lay.addWidget(area,1)

    def build_archive(self):
        """Tamamlanan siparişi değiştirilemeyen okunabilir arşiv olarak göster."""
        order = self.current()
        overview = self.db.siparis_ozeti(order)
        date_value = str(order.get('tamamlanma_tarihi') or order.get('tarih') or '')
        bar = QFrame(); bar.setObjectName('OrderArchiveHeader')
        line = QHBoxLayout(bar)
        line.setContentsMargins(12,8,12,8)
        line.addWidget(text('✓ Tamamlanan sipariş arşivi', 'Title'))
        line.addStretch()
        line.addWidget(text(f"Tarih: {date_value[:16].replace('T',' ')}   ·   {overview['adet']} kitap   ·   {overview['sayfa']:,} sayfa", 'Muted'))
        self.body_lay.addWidget(bar)
        if order.get('kargo_turu') in ('telafi','acik_adres'):
            group = 'Telafi siparişi' if order.get('kargo_turu') == 'telafi' else 'Açık adres siparişi'
            self.body_lay.addWidget(text(f"{group} · Kargo gideri: {float(order.get('kargo_ucreti',0) or 0):,.2f} TL", 'OrderShippingCost'))
        content = QWidget(); grid = QGridLayout(content)
        grid.setContentsMargins(4,4,6,8)
        grid.setHorizontalSpacing(10); grid.setVerticalSpacing(10)
        groups = self.db.siparis_gruplari(order)
        for i, group in enumerate(groups):
            code = str(group['kod'])
            book = self.db.katalog.get(code, {'kod':code,'isim':group['isim']})
            card = QFrame(); card.setObjectName('OrderArchiveCard')
            row = QHBoxLayout(card); row.setContentsMargins(9,8,9,8); row.setSpacing(10)
            row.addWidget(cover_label(book,self.covers,86,121))
            info = QVBoxLayout(); info.setSpacing(4)
            name = text(group['isim'],'TrackBookName',wrap=True)
            info.addWidget(name)
            info.addWidget(text(f"#{code} · {group['sayfa_birim']} sayfa",'Muted'))
            info.addWidget(text(f"SB {group.get('sb',0)}  ·  RNK {group.get('rnk',0)}",'Muted'))
            info.addWidget(text(f"{group.get('adet',0)} kitap · {group.get('sayfa',group.get('adet',0)*group.get('sayfa_birim',0))} sayfa",'Muted'))
            info.addStretch()
            row.addLayout(info,1)
            grid.addWidget(card,i//3,i%3)
        grid.setColumnStretch(0,1);grid.setColumnStretch(1,1);grid.setColumnStretch(2,1)
        self.body_lay.addWidget(scrollable(content),1)

    def _find_variant(self, code, kind):
        order = self.current()
        if not order:
            return None
        return next((i for i in order.get('kitaplar', [])
                     if str(i.get('kod')) == str(code)
                     and str(i.get('tur', 'SB')).upper() == kind), None)

    def step_progress(self, code, kind, field, delta):
        """Tek tıklamayla kayıt, ardından sadece ilgili etiket/kapakların yenilenmesi."""
        order = self.current()
        if not order or self.db.siparis_durumu(order) != 'aktif':
            return
        item = self._find_variant(code, kind)
        if item is None:
            return
        try:
            ready, boxed = sonraki_ilerleme(
                item['adet'], item.get('hazir', 0), item.get('koli', 0), field, delta
            )
            if (ready, boxed) == (int(item.get('hazir', 0)), int(item.get('koli', 0))):
                return
            self.db.siparis_ilerleme_degistir(order, code, kind, ready, boxed)
        except Exception as exc:
            return error(self, exc)
        self._recent_code = str(code)
        self._update_card_styles()
        self.refresh_progress_labels()
        self._parent_refresh_timer.start()

    def refresh_progress_labels(self):
        """Kaydırmayı ve kitap seçimlerini sıfırlamadan sayaçları güncelle."""
        order = self.current()
        if not order:
            return
        active = self.db.siparis_durumu(order) == 'aktif'
        for (code, kind), controls in self.track_variant_widgets.items():
            item = self._find_variant(code, kind)
            if not item:
                continue
            amount = int(item['adet'])
            ready = int(item.get('hazir', 0))
            boxed = int(item.get('koli', 0))
            controls['hazir'].setText(f'{ready}/{amount}')
            controls['koli'].setText(f'{boxed}/{amount}')
            for (field, delta), enabled in buton_durumlari(amount, ready, boxed, active).items():
                controls['buttons'][(field, delta)].setEnabled(enabled)
        groups = {str(g['kod']): g for g in self.db.siparis_gruplari(order)}
        for code, cover in self.track_covers.items():
            if code in groups:
                cover.set_progress(groups[code], active=self.db.siparis_durumu(order) in ('aktif', 'tamamlandi'))
        summary = self.db.siparis_ozeti(order)
        if self.header_summary:
            self.header_summary.setText(
                f"SB {summary['sb']} · RNK {summary['rnk']} · "
                f"Hazır {summary['hazir']}/{summary['adet']} · Koli {summary['koli']}/{summary['adet']}"
            )
        # A card may become fully prepared immediately after a bulk or single
        # item update. Hide it without rebuilding the card or resetting selection.
        if getattr(self,'track_scroll',None) is not None:
            self.reflow_track()

    def build_track(self):
        order = self.current()
        status = self.db.siparis_durumu(order)
        summary = self.db.siparis_ozeti(order)

        toolbar = QFrame()
        toolbar.setObjectName('TrackActionToolbar')
        toolbar_lay = QVBoxLayout(toolbar)
        toolbar_lay.setContentsMargins(12, 9, 12, 10)
        toolbar_lay.setSpacing(8)
        toolbar_lay.addWidget(text('TOPLU İŞLEMLER', 'TrackActionsHeading'))
        # Tek satır: beş eşit genişlikli kontrol, pencereye göre uyarlanır.
        self.track_toolbar = toolbar
        row_box = QWidget()
        row_box.setObjectName('TrackActionsRow')
        row_layout = QHBoxLayout(row_box)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        self._bulk_row_widgets = [row_box]
        self._bulk_action_rows = [row_layout]
        toolbar_lay.addWidget(row_box)

        self.select_all = button('☐  Hepsini seç', 'TrackSelectAllToggle')
        self.select_all.setCheckable(True)
        self.select_all.setMinimumHeight(46)
        self.select_all.setToolTip('Görünen kitapları toplu işlem için seç veya seçimi kaldır')
        self.select_all.toggled.connect(self.select_everything)
        # One pillbox split into two independent-looking, mutually exclusive
        # filters; no additional top-level toolbar item or width inflation.
        self.pending_filters = QFrame()
        self.pending_filters.setObjectName('TrackPendingFilters')
        pending_row = QHBoxLayout(self.pending_filters)
        pending_row.setContentsMargins(0, 0, 0, 0)
        pending_row.setSpacing(0)
        self.only_unprepared = button('◯  Hazırlanmayanlar', 'TrackUnpreparedToggle')
        self.only_unprepared.setCheckable(True)
        self.only_unprepared.setMinimumHeight(46)
        self.only_unprepared.setToolTip('Henüz hazırlanması tamamlanmayan kitaplar')
        self.only_unprepared.toggled.connect(self.toggle_unprepared)
        self.only_unboxed = button('◯  Kolilenmeyenler', 'TrackUnboxedToggle')
        self.only_unboxed.setCheckable(True)
        self.only_unboxed.setMinimumHeight(46)
        self.only_unboxed.setToolTip('Henüz tamamı kolilenmeyen kitaplar')
        self.only_unboxed.toggled.connect(self.toggle_unboxed)
        pending_row.addWidget(self.only_unprepared, 1)
        pending_row.addWidget(self.only_unboxed, 1)

        segments=[]
        for title,positive,negative,operation,role in (
            ('HAZIRLAMA','Hazırla','Geri al','hazir','TrackActionReady'),
            ('KOLİLEME','Kolile','Geri al','koli','TrackActionBoxed'),
        ):
            segment = QFrame()
            segment.setObjectName(role)
            segment_row = QHBoxLayout(segment)
            segment.setMinimumHeight(46)
            segment_row.setContentsMargins(7,4,7,4)
            segment_row.setSpacing(5)
            caption = text(title, 'TrackActionLabel')
            caption.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            caption.setMinimumWidth(70)
            segment_row.addWidget(caption)
            plus = button(positive,'TrackBulkPositive')
            plus.setMinimumSize(60, 34)
            plus.setAccessibleName(f'Seçilen kitapları {positive.lower()}')
            plus.clicked.connect(lambda checked=False,target=operation:self.bulk(target))
            minus = button(negative,'TrackBulkNegative')
            minus.setMinimumSize(57, 34)
            minus.setAccessibleName(f'Seçilen kitapların {title.lower()} işlemini geri al')
            minus.clicked.connect(lambda checked=False,target=operation:self.bulk_clear(target))
            plus.setEnabled(status=='aktif')
            minus.setEnabled(status=='aktif')
            plus.setToolTip(f'Seçili kitapları {title.lower()} olarak işaretle')
            minus.setToolTip(f'Seçili kitapların {title.lower()} işaretini geri al')
            segment_row.addWidget(plus)
            segment_row.addWidget(minus)
            segments.append(segment)
        pdf_bulk = button('▣  Seçilen PDF’leri Aç','PdfAction')
        pdf_bulk.setMinimumHeight(46)
        pdf_bulk.setToolTip('Seçili kitapların koduna göre PDF dosyalarını açar')
        pdf_bulk.clicked.connect(self.open_selected_pdfs)
        self._bulk_widgets=[self.select_all,self.pending_filters,*segments,pdf_bulk]
        self.body_lay.addWidget(toolbar)

        self.code_checks = {}
        self.track_variant_widgets = {}
        self.track_covers = {}
        self.track_cards_by_code = {}
        self.track_body = QWidget()
        self.track_body.setObjectName('TrackGridBody')
        self.track_grid = QVBoxLayout(self.track_body)
        self.track_grid.setContentsMargins(0, 0, 0, 0)
        self.track_grid.setSpacing(0)
        self.track_inner = QWidget()
        self.track_cards_grid = QGridLayout(self.track_inner)
        self.track_cards_grid.setContentsMargins(4, 4, 5, 8)
        self.track_cards_grid.setHorizontalSpacing(10)
        self.track_cards_grid.setVerticalSpacing(10)
        self.track_cards_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.track_grid.addWidget(self.track_inner, 0, Qt.AlignmentFlag.AlignTop)
        self.track_grid.addStretch(1)
        self._track_cards = []
        for group in self.db.siparis_gruplari(order):
            card = self.make_track_card(group, status)
            self._track_cards.append(card)
        self._filter_empty_label = text('Bu filtreye uygun kitap bulunmuyor. Tümünü görmek için filtreyi kapatın.', 'TrackFilterEmpty')
        self._filter_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._filter_empty_label.setMinimumHeight(96)
        self._filter_empty_label.setVisible(False)
        if not self._track_cards:
            self._filter_empty_label.setText('Bu siparişte kitap yok.')
        self.track_scroll = scrollable(self.track_body)
        self.track_scroll.setObjectName('TrackScroll')
        self.track_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body_lay.addWidget(self.track_scroll, 1)
        self._track_columns = None
        self._track_layout_signature = None
        self._bulk_toolbar_layout_mode = None
        QTimer.singleShot(0, self._layout_bulk_toolbar)
        QTimer.singleShot(0, self.reflow_track)

    def make_track_card(self, group, status):
        """Solda daha büyük kapak/bilgi, sağda SB/RNK/PDF işlemleri."""
        code = str(group['kod'])
        book = self.db.katalog.get(code, {'kod': code, 'isim': group['isim']})
        card = QFrame()
        card.setObjectName('TrackBookCard')
        card.setMinimumWidth(292)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setProperty('trackRecent', code == self._recent_code)
        self.track_cards_by_code[code] = card
        root = QHBoxLayout(card)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Birinci bölüm: kitap kapağı ve hemen altındaki tanımlayıcı bilgiler.
        cover_zone = QWidget()
        cover_zone.setObjectName('TrackCoverZone')
        cover_zone.setFixedWidth(140)
        cover_layout = QVBoxLayout(cover_zone)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setSpacing(4)
        cover = ProgressCover(book, self.covers, group, 125, 178,
                              active=status in ('aktif', 'tamamlandi'))
        self.track_covers[code] = cover
        cover_layout.addWidget(cover, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        name = QLabel(group['isim'])
        name.setObjectName('TrackBookName')
        name.setWordWrap(True)
        name.setMaximumHeight(41)
        name.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        name.setToolTip(group['isim'])
        cover_layout.addWidget(name)
        details = QLabel(f"#{code} · {group['sayfa_birim']} sayfa")
        details.setObjectName('TrackBookInfo')
        details.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cover_layout.addWidget(details)
        subgroup = QLabel(str(group.get('kitap_grubu', '')))
        subgroup.setObjectName('TrackBookInfo')
        subgroup.setWordWrap(True)
        subgroup.setMaximumHeight(30)
        subgroup.setToolTip(str(group.get('kitap_grubu', '')))
        subgroup.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cover_layout.addWidget(subgroup)
        cover_layout.addStretch()
        root.addWidget(cover_zone)
        root.addWidget(self.make_track_divider())

        # İkinci bölüm: seçim + kod ve mevcut baskı varyantları.
        control_zone = QWidget()
        control_zone.setObjectName('TrackControlZone')
        controls = QVBoxLayout(control_zone)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(6)
        pick = QCheckBox()
        pick.setAccessibleName(f'Kitap {code} toplu işlem seçimi')
        pick.setToolTip('Bu kitabı toplu işlem veya PDF açmak için seç')
        self.code_checks[code] = pick
        pick.toggled.connect(lambda checked,c=code:self._set_track_selected(c,checked))
        top.addWidget(pick)
        top.addWidget(text(f'#{code}', 'TrackCode'))
        top.addStretch()
        top.addWidget(text('BASKI KONTROLÜ', 'TrackControlsCaption'))
        controls.addLayout(top)
        for kind in ('SB', 'RNK'):
            item = self._find_variant(code, kind)
            if item:
                controls.addWidget(self.variant_panel(code, kind, item, status))
        pdf = button('▣  PDF Aç', 'TrackPdfButton')
        pdf.setToolTip(f'#{code} numaralı kitabın PDF dosyasını aç')
        pdf.clicked.connect(lambda checked=False,c=code:self.open_pdfs([c]))
        controls.addWidget(pdf)
        controls.addStretch()
        root.addWidget(control_zone, 1)
        return card

    def _set_track_selected(self, code, selected):
        card = self.track_cards_by_code.get(str(code))
        if card is not None:
            card.setProperty('trackSelected', bool(selected))
            card.style().unpolish(card)
            card.style().polish(card)
            card.update()
        self._sync_select_all()

    def _update_card_styles(self):
        for code, card in self.track_cards_by_code.items():
            card.setProperty('trackRecent', code == self._recent_code)
            card.style().unpolish(card)
            card.style().polish(card)
            card.update()

    @staticmethod
    def make_track_divider():
        divider = QFrame()
        divider.setObjectName('TrackZoneDivider')
        divider.setFrameShape(QFrame.Shape.NoFrame)
        divider.setFixedWidth(1)
        return divider

    def _layout_bulk_toolbar(self):
        """Beş aracı daima tek satırda ve eşit hücrelerde göster."""
        if not hasattr(self, '_bulk_action_rows'):
            return
        layout = self._bulk_action_rows[0]
        if layout.count() == len(self._bulk_widgets):
            return
        while layout.count():
            layout.takeAt(0)
        for control in self._bulk_widgets:
            control.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            layout.addWidget(control, 1, Qt.AlignmentFlag.AlignVCenter)

    def _needs_preparation(self, code):
        order=self.current()
        if not order:return False
        return any(
            str(item.get('kod'))==str(code) and
            int(item.get('adet',0))>int(item.get('hazir',0))
            for item in order.get('kitaplar',[])
        )

    def _needs_boxing(self, code):
        order = self.current()
        if not order:
            return False
        return any(
            str(item.get('kod')) == str(code)
            and int(item.get('adet', 0)) > int(item.get('koli', 0))
            for item in order.get('kitaplar', [])
        )

    def toggle_unprepared(self, enabled):
        if enabled and self.only_unboxed.isChecked():
            self.only_unboxed.blockSignals(True)
            self.only_unboxed.setChecked(False)
            self.only_unboxed.blockSignals(False)
            self.only_unboxed.setText('◯  Kolilenmeyenler')
        self.only_unprepared.setText(
            '●  Hazırlanmayanlar' if enabled else '◯  Hazırlanmayanlar')
        self.reflow_track()

    def toggle_unboxed(self, enabled):
        if enabled and self.only_unprepared.isChecked():
            self.only_unprepared.blockSignals(True)
            self.only_unprepared.setChecked(False)
            self.only_unprepared.blockSignals(False)
            self.only_unprepared.setText('◯  Hazırlanmayanlar')
        self.only_unboxed.setText(
            '●  Kolilenmeyenler' if enabled else '◯  Kolilenmeyenler')
        self.reflow_track()

    def _visible_track_codes(self):
        if getattr(self, 'only_unprepared', None) and self.only_unprepared.isChecked():
            return tuple(c for c in self.track_cards_by_code if self._needs_preparation(c))
        if getattr(self, 'only_unboxed', None) and self.only_unboxed.isChecked():
            return tuple(c for c in self.track_cards_by_code if self._needs_boxing(c))
        return tuple(self.track_cards_by_code)

    def _sync_select_all(self):
        if not getattr(self,'select_all',None) or not getattr(self,'code_checks',None):
            return
        visible=self._visible_track_codes()
        all_selected=bool(visible) and all(self.code_checks[c].isChecked() for c in visible)
        self.select_all.blockSignals(True)
        self.select_all.setChecked(all_selected)
        self.select_all.setText('✓  Hepsi seçili' if all_selected else '☐  Hepsini seç')
        self.select_all.setEnabled(bool(visible))
        self.select_all.blockSignals(False)

    def reflow_track(self):
        if not self.track_scroll or not hasattr(self,'track_cards_grid'):
            return
        width=self.track_scroll.viewport().width()
        cols=4 if width>=1480 else 3 if width>=1010 else 2 if width>=630 else 1
        visible_codes=self._visible_track_codes()
        signature=(cols,visible_codes)
        if signature==self._track_layout_signature:
            self._sync_select_all()
            return
        self._track_layout_signature=signature
        self._track_columns=cols
        # A hidden selected card must never accidentally be included in a
        # subsequent bulk command or PDF operation.
        hidden=set(self.track_cards_by_code)-set(visible_codes)
        for code in hidden:
            self.code_checks[code].setChecked(False)
        while self.track_cards_grid.count():
            self.track_cards_grid.takeAt(0)
        for code,card in self.track_cards_by_code.items():
            card.setVisible(code in visible_codes)
        for index, code in enumerate(visible_codes):
            self.track_cards_grid.addWidget(
                self.track_cards_by_code[code], index//cols,index%cols)
        if not visible_codes:
            self._filter_empty_label.setVisible(True)
            self.track_cards_grid.addWidget(self._filter_empty_label,0,0,1,cols)
        else:
            self._filter_empty_label.hide()
        for col in range(4):
            self.track_cards_grid.setColumnStretch(col,1 if col<cols else 0)
        self._sync_select_all()

    def variant_panel(self, code, kind, item, status):
        """Kompakt SB/RNK paneli: satırlar yatay, kontroller net ve kapakla hizalı."""
        amount = int(item['adet'])
        ready = int(item.get('hazir', 0))
        boxed = int(item.get('koli', 0))
        frame = QFrame()
        frame.setObjectName('TrackVariantSB' if kind == 'SB' else 'TrackVariantRNK')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(4)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)
        header.addWidget(text(kind, 'TrackVariantTitleSB' if kind == 'SB' else 'TrackVariantTitleRNK'))
        header.addStretch()
        header.addWidget(text(f'{amount} ad.', 'TrackVariantAmount'))
        layout.addLayout(header)

        entry = {'buttons': {}}
        for label, field, count in (('Hazır', 'hazir', ready), ('Koli', 'koli', boxed)):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            tag = text(label, 'TrackStepLabel')
            tag.setFixedWidth(30)
            row.addWidget(tag)
            count_label = text(f'{count}/{amount}', 'TrackStepCount')
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setMinimumWidth(34)
            row.addWidget(count_label)
            row.addStretch(1)
            minus = button('−', 'TrackStep')
            minus.setFixedSize(20, 20)
            minus.setToolTip(f'{kind} · ' + ('Hazır' if field == 'hazir' else 'Koli') + ' azalt')
            minus.clicked.connect(lambda checked=False, c=code, k=kind, f=field:
                                  self.step_progress(c, k, f, -1))
            entry['buttons'][(field, -1)] = minus
            row.addWidget(minus)
            plus = button('+', 'TrackStep')
            plus.setFixedSize(20, 20)
            plus.setToolTip(f'{kind} · ' + ('Hazır' if field == 'hazir' else 'Koli') + ' artır' + (' (önce hazırlanmalı)' if field == 'koli' else ''))
            plus.clicked.connect(lambda checked=False, c=code, k=kind, f=field:
                                 self.step_progress(c, k, f, 1))
            entry['buttons'][(field, 1)] = plus
            row.addWidget(plus)
            layout.addLayout(row)
            entry[field] = count_label
        self.track_variant_widgets[(code, kind)] = entry
        for (field, delta), enabled in buton_durumlari(amount, ready, boxed, status == 'aktif').items():
            entry['buttons'][(field, delta)].setEnabled(enabled)
        return frame

    def choose_pdf_folder(self):
        source = str(self.pdfs.folder or Path.home())
        path = QFileDialog.getExistingDirectory(self, 'Kitap PDF klasörünü seç', source)
        if not path:
            return False
        try:
            self.pdfs.set_folder(path)
        except Exception as exc:
            error(self, exc)
            return False
        QMessageBox.information(self, 'PDF klasörü', f'PDF dosyaları bu klasörde aranacak:\n{path}')
        return True

    def open_selected_pdfs(self):
        codes = [code for code, check in self.code_checks.items() if check.isChecked()]
        if not codes:
            return error(self, 'PDF açmak için önce kitapları seç.')
        self.open_pdfs(codes)

    def open_pdfs(self, codes):
        if self.pdfs.folder is None or not self.pdfs.folder.is_dir():
            if not self.choose_pdf_folder():
                return
        found, missing = self.pdfs.resolve_many(codes)
        if len(found) > 8 and not confirm(self, f'{len(found)} PDF ayrı pencerelerde açılacak. Devam edilsin mi?'):
            return
        failed = []
        for file in found:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(file))):
                failed.append(file.name)
        if missing or failed:
            sections = []
            if missing:
                sections.append('PDF bulunamayan kitap kodları: ' + ', '.join(missing))
            if failed:
                sections.append('Açılamayan dosyalar: ' + ', '.join(failed))
            sections.append('Dosya isimlerini örn. 31.pdf veya kitap_31.pdf olarak düzenleyebilirsin.')
            error(self, '\n'.join(sections))

    def select_everything(self, state):
        # Only visible books are selected. Filtered-out books are not changed.
        for code in self._visible_track_codes():
            self.code_checks[code].setChecked(bool(state))
        self._sync_select_all()

    def bulk(self, target):
        codes = [code for code, check in self.code_checks.items() if check.isChecked()]
        if not codes:
            return error(self, 'Önce kitapları seç.')
        try:
            self.db.siparis_toplu_ilerlet(self.current(), codes, target)
        except Exception as exc:
            return error(self, exc)
        self._recent_code = str(codes[0])
        self._update_card_styles()
        self.refresh_progress_labels()
        self._parent_refresh_timer.start()


    def bulk_clear(self, target):
        codes = {code for code, check in self.code_checks.items() if check.isChecked()}
        if not codes:
            return error(self, 'Önce kitapları seçin.')
        order = self.current()
        if not order or self.db.siparis_durumu(order) != 'aktif':
            return error(self, 'Bu işlem yalnızca aktif siparişte yapılabilir.')
        chosen = [item for item in order.get('kitaplar', [])
                  if str(item.get('kod')) in codes]
        originals = [(item, int(item.get('hazir',0)), int(item.get('koli',0)))
                     for item in chosen]
        try:
            for item, hazir, koli in originals:
                if target == 'hazir':
                    item['hazir'] = 0
                    item['koli'] = 0
                else:
                    item['koli'] = 0
            # Bütün seçili kitaplar için bir defa kayıt yaz.
            self.db.siparisleri_kaydet()
        except Exception as exc:
            for item, hazir, koli in originals:
                item['hazir'] = hazir
                item['koli'] = koli
            return error(self, exc)
        self._recent_code = next(iter(codes))
        self._update_card_styles()
        self.refresh_progress_labels()
        self._parent_refresh_timer.start()

    def _shipping_edited(self, value):
        self.platform_value = otomatik_platform_bul(value)
        self.platform_label.setText(self.platform_value)

    def _format_shipping(self):
        value = self.shipping.text().strip()
        formatted = format_kargo_kodu(value)
        if formatted != value:
            self.shipping.setText(formatted)

    def build_edit(self):
        order = self.current()
        status = self.db.siparis_durumu(order)
        editable = status in ('havuz', 'aktif')
        header = text('GÖNDERİ VE SİPARİŞ BİLGİLERİ', 'OrderEditSection')
        self.body_lay.addWidget(header)

        info_panel = QFrame(); info_panel.setObjectName('OrderEditPanel')
        info_grid = QGridLayout(info_panel)
        info_grid.setContentsMargins(15, 14, 15, 14)
        info_grid.setHorizontalSpacing(14)
        info_grid.setVerticalSpacing(7)

        self.shipping = QLineEdit(str(order.get('kod', '')))
        self.shipping.setPlaceholderText('Kargo kodu veya açık adres')
        self.platform_value = str(order.get('platform') or otomatik_platform_bul(self.shipping.text()))
        self.platform_label = QLabel(self.platform_value)
        self.platform_label.setObjectName('OrderEditPlatform')
        self.platform_label.setMinimumHeight(35)
        self.shipping.textEdited.connect(self._shipping_edited)
        self.shipping.editingFinished.connect(self._format_shipping)

        # QDoubleSpinBox's suffix/locale painting misaligned the edit cursor in
        # some Windows scaling configurations. Use a plain, stable text field.
        self.revenue = QLineEdit()
        self.revenue.setObjectName('OrderEditRevenueInput')
        self.revenue.setText(f"{float(order.get('ciro', 0) or 0):.2f}".replace('.', ','))
        self.revenue.setPlaceholderText('Örnek: 1234,50')
        self.revenue.setToolTip('Ciro tutarı. 1234,50 veya 1234.50 yazabilirsiniz.')
        self.revenue.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.revenue.setMinimumHeight(38)
        self.revenue.setMaxLength(24)
        self.revenue_box = QFrame()
        self.revenue_box.setObjectName('OrderEditRevenueBox')
        revenue_lay = QHBoxLayout(self.revenue_box)
        revenue_lay.setContentsMargins(5, 2, 10, 2)
        revenue_lay.setSpacing(5)
        revenue_lay.addWidget(self.revenue, 1)
        suffix = QLabel('TL')
        suffix.setObjectName('OrderEditCurrencyLabel')
        suffix.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        suffix.setFixedWidth(26)
        revenue_lay.addWidget(suffix)
        self.kind = QComboBox()
        kinds = ['Normal Sipariş', 'Telafi Sipariş', 'Özel Sipariş', 'Toplu Sipariş']
        current_kind = str(order.get('siparis_turu', '') or 'Normal Sipariş')
        if current_kind not in kinds:
            kinds.insert(0, current_kind)
        self.kind.addItems(kinds)
        self.kind.setCurrentText(current_kind)

        for col, (label, widget) in enumerate((('KARGO KODU / ADRES', self.shipping), ('PLATFORM · OTOMATİK', self.platform_label))):
            info_grid.addWidget(text(label, 'Tiny'), 0, col)
            info_grid.addWidget(widget, 1, col)
        for col, (label, widget) in enumerate((('CİRO', self.revenue_box), ('SİPARİŞ TÜRÜ', self.kind))):
            caption=text(label, 'Tiny')
            info_grid.addWidget(caption, 2, col)
            info_grid.addWidget(widget, 3, col)
            if col==0:
                self.revenue_caption=caption
        self.telafi_caption=QLabel(
            'Telafi · 0 TL ciro · Kargo gideri tamamlanırken girilir')
        self.telafi_caption.setObjectName('OrderShippingCost')
        self.telafi_caption.setWordWrap(True)
        info_grid.addWidget(self.telafi_caption, 3, 0)
        self.kind.currentTextChanged.connect(self._sync_compensation_kind)
        info_grid.setColumnStretch(0, 3)
        info_grid.setColumnStretch(1, 2)
        self.shipping.setEnabled(editable)
        self.revenue.setEnabled(editable)
        self.kind.setEnabled(editable)
        self._sync_compensation_kind(self.kind.currentText())
        self.body_lay.addWidget(info_panel)

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(text('KİTAPLAR VE BASKI ADETLERİ', 'OrderEditSection'))
        top.addStretch()
        self.add_combo = QComboBox()
        self.add_combo.setObjectName('OrderBookSearch')
        self.add_combo.setEditable(True)
        self.add_combo.setMinimumWidth(320)
        self.add_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for book in self.db.kitaplar:
            self.add_combo.addItem(f"#{book['kod']} · {book['isim']}", str(book['kod']))
        completer = self.add_combo.completer()
        if completer:
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.add_combo.lineEdit().setPlaceholderText('Kod veya kitap adıyla ekle...')
        add_sb = button('+ SB ekle', 'QuickSB')
        add_sb.clicked.connect(lambda checked=False: self.add_book('SB'))
        add_rnk = button('+ RNK ekle', 'QuickRNK')
        add_rnk.clicked.connect(lambda checked=False: self.add_book('RNK'))
        self.add_combo.setEnabled(editable)
        add_sb.setEnabled(editable)
        add_rnk.setEnabled(editable)
        top.addWidget(self.add_combo)
        top.addWidget(add_sb)
        top.addWidget(add_rnk)
        self.body_lay.addLayout(top)

        rows = QWidget(); rows.setObjectName('OrderEditBooks')
        self.rows_lay = QVBoxLayout(rows)
        self.rows_lay.setContentsMargins(1, 1, 5, 1)
        self.rows_lay.setSpacing(5)
        self.qty_inputs = {}
        for group in self.db.siparis_gruplari(order):
            self.add_book_row(str(group['kod']))
        self.rows_lay.addStretch()
        self.body_lay.addWidget(scrollable(rows), 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addWidget(text('Kaydedilen adet değişiklikleri mevcut hazırlanma/kolileme sayılarının üstüne çıkmaz.', 'Muted'))
        footer.addStretch()
        self.save_btn = button('Değişiklikleri kaydet', 'Accent')
        self.save_btn.setEnabled(editable)
        self.save_btn.clicked.connect(self.save_edit)
        footer.addWidget(self.save_btn)
        self.body_lay.addLayout(footer)

    def _sync_compensation_kind(self,kind):
        from utils import tr_kucult
        is_telafi='telafi' in tr_kucult(kind)
        if is_telafi:
            self.revenue.setText('0,00')
        self.revenue_box.setVisible(not is_telafi)
        self.revenue_caption.setVisible(not is_telafi)
        self.telafi_caption.setVisible(is_telafi)
        self.revenue.setEnabled(
            not is_telafi and self.db.siparis_durumu(self.current()) in ('havuz','aktif'))

    def add_book_row(self, code):
        code = str(code)
        if (code, 'SB') in self.qty_inputs:
            return
        book = self.db.katalog.get(code)
        if not book:
            return
        group = QFrame(); group.setObjectName('OrderEditBookRow')
        line = QHBoxLayout(group)
        line.setContentsMargins(10, 7, 10, 7)
        line.setSpacing(12)
        line.addWidget(cover_label(book, self.covers, 49, 69))
        name_box = QVBoxLayout(); name_box.setSpacing(2)
        name = QLabel(book['isim'])
        name.setObjectName('OrderEditBookName')
        name.setWordWrap(True)
        name_box.addWidget(name)
        name_box.addWidget(text(f"#{code}  ·  {book['sayfa']} sayfa", 'Tiny'))
        line.addLayout(name_box, 1)
        for kind in ('SB', 'RNK'):
            block = QVBoxLayout(); block.setSpacing(4)
            block.addWidget(text(kind, 'BadgeRNK' if kind == 'RNK' else 'BadgeSB'))
            spin = QSpinBox(); spin.setRange(0, 100000)
            spin.setFixedWidth(89)
            entry = next((x for x in self.current()['kitaplar'] if str(x.get('kod')) == code and str(x.get('tur', 'SB')).upper() == kind), None)
            spin.setValue(int(entry.get('adet', 0)) if entry else 0)
            spin.setEnabled((kind == 'SB' or bool(book.get('renkli_opsiyon')) or bool(entry)) and self.db.siparis_durumu(self.current()) != 'tamamlandi')
            self.qty_inputs[code, kind] = spin
            block.addWidget(spin)
            line.addLayout(block)
        self.rows_lay.insertWidget(max(0, self.rows_lay.count() - 1), group)

    def add_book(self, kind='SB'):
        """Seçilen kitap, tercih edilen SB/RNK sayacına doğrudan eklenir."""
        from utils import tr_kucult
        typed = self.add_combo.currentText().strip()
        code = None
        idx = self.add_combo.currentIndex()
        if idx >= 0 and self.add_combo.itemText(idx) == typed:
            code = str(self.add_combo.itemData(idx))
        if code is None:
            import re
            match = re.match(r'^#?(\d+)(?:\D|$)', typed)
            if match and match.group(1) in self.db.katalog:
                code = match.group(1)
        if code is None:
            typed_fold = tr_kucult(typed)
            found = [str(b['kod']) for b in self.db.kitaplar
                     if tr_kucult(str(b.get('isim',''))) == typed_fold or
                     tr_kucult(str(b.get('isim',''))).startswith(typed_fold)]
            if len(found) == 1:
                code = found[0]
        if not code or code not in self.db.katalog:
            return error(self,'Kitap kodunu yaz veya listeden bir kitap seç.')
        book = self.db.katalog[code]
        if kind == 'RNK' and not book.get('renkli_opsiyon', False):
            return error(self,'Bu kitabın katalogda renkli baskı seçeneği bulunmuyor.')
        self.add_book_row(code)
        spin = self.qty_inputs.get((code,kind))
        if spin and spin.isEnabled():
            spin.setValue(spin.value()+1)
            spin.setFocus()
        else:
            return error(self,'Seçilen baskı türü bu kitap için kullanılamıyor.')

    def save_edit(self):
        old = {(str(i['kod']), str(i.get('tur', 'SB')).upper()): i for i in self.current().get('kitaplar', [])}
        items = []
        for (code, kind), spin in self.qty_inputs.items():
            n = spin.value()
            if not n:
                continue
            prev = old.get((code, kind), {})
            ready = min(n, int(prev.get('hazir', 0)))
            boxed = min(ready, int(prev.get('koli', 0)))
            items.append({'kod': code, 'tur': kind, 'adet': n, 'hazir': ready, 'koli': boxed})
        if not items:
            return error(self, 'Siparişte en az bir kitap olmalı.')
        try:
            self.db.siparis_duzenle(
                self.current(),
                {'kod': format_kargo_kodu(self.shipping.text()), 'platform': self.platform_value,
                 'ciro': 0.0 if 'telafi' in self.kind.currentText().casefold()
                         else ciro_metinini_sayiya_cevir(self.revenue.text()),
                 'siparis_turu': self.kind.currentText()},
                items,
            )
        except Exception as exc:
            return error(self, exc)
        self.on_updated()
        self.build_ui()
        QMessageBox.information(self, 'ALFA ERP', 'Sipariş değişiklikleri kaydedildi.')



class OrderDockTabBar(QTabBar):
    """Reorder tabs normally; tear them off by dragging beyond the strip."""
    tearOff = Signal(int, object)
    reattachDrop = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._down_index = -1
        self._down_point = None
        self.setAcceptDrops(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._down_index = self.tabAt(event.position().toPoint())
            self._down_point = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        outside = not self.rect().adjusted(-20,-30,20,30).contains(event.position().toPoint())
        index = self._down_index
        self._down_index = -1
        if (event.button() == Qt.MouseButton.LeftButton and index >= 0
            and outside and self._down_point is not None
            and (event.position().toPoint() - self._down_point).manhattanLength() > 40):
            self.tearOff.emit(index, event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-alfa-order-tab'):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-alfa-order-tab'):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat('application/x-alfa-order-tab'):
            sid = bytes(event.mimeData().data('application/x-alfa-order-tab')).decode('utf-8','ignore')
            self.reattachDrop.emit(sid)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class OrderDragHandle(QPushButton):
    def __init__(self,sid,parent=None):
        super().__init__('↔  Buradan tutup sekme çubuğuna sürükle',parent)
        self.sid = str(sid)
        self._start = None

    def mousePressEvent(self,event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if (not (event.buttons() & Qt.MouseButton.LeftButton)
            or self._start is None
            or (event.position().toPoint()-self._start).manhattanLength() < 12):
            super().mouseMoveEvent(event)
            return
        drag = QDrag(self)
        data = QMimeData()
        data.setData('application/x-alfa-order-tab',self.sid.encode('utf-8'))
        drag.setMimeData(data)
        drag.exec(Qt.DropAction.MoveAction)
        self._start = None


class DetachedOrderWindow(QDialog):
    """A floating order editor which returns to its dock on close."""
    def __init__(self,host,page,location):
        super().__init__(host.parentWidget())
        self.host = host
        self.page = page
        self.sid = str(page.sid)
        self.setObjectName('DetachedOrderWindow')
        self.setWindowTitle(f'ALFA ERP · Sipariş #{self.sid}')
        self.resize(1100,740)
        self.setMinimumSize(750,540)
        root = QVBoxLayout(self)
        root.setContentsMargins(8,8,8,8)
        root.setSpacing(6)
        controls=QHBoxLayout()
        controls.addWidget(OrderDragHandle(self.sid,self),1)
        dock=QPushButton('↩  Sekmeye geri al')
        dock.clicked.connect(lambda:host.reattach_order(self.sid))
        controls.addWidget(dock)
        root.addLayout(controls)
        page.setParent(self)
        root.addWidget(page,1)
        self.move(location)
        self.show()

    def closeEvent(self,event):
        if self.host is not None and self.sid in self.host.detached:
            self.host.reattach_order(self.sid,from_close=True)
        super().closeEvent(event)


class SiparisTakipSekmeleri(QDialog):
    """Birden fazla sipariş detayını tek popup içinde sekmeler halinde toplar."""
    def __init__(self, db, covers, on_updated, parent=None):
        super().__init__(parent)
        self.db = db
        self.covers = covers
        self.on_updated = on_updated
        self.pages = {}
        self.detached = {}
        self.setObjectName('OrderTrackTabsWindow')
        self.setWindowTitle('ALFA ERP · Sipariş Detayları')
        self.resize(1220, 740)
        self.setMinimumSize(980, 620)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(5)
        tabs_header = QFrame()
        tabs_header.setObjectName('TrackTabsHeader')
        tabs_header_lay = QHBoxLayout(tabs_header)
        tabs_header_lay.setContentsMargins(12, 7, 12, 7)
        tabs_header_lay.setSpacing(12)
        tabs_header_lay.addWidget(text('AÇIK SİPARİŞ DETAYLARI', 'TrackTabsHeading'))
        tabs_header_lay.addWidget(text('Sekmeye tıklayarak sipariş değiştir', 'TrackTabsHelp'))
        tabs_header_lay.addStretch(1)
        self.tabs_count = text('0 sekme', 'TrackTabsCount')
        tabs_header_lay.addWidget(self.tabs_count)
        root.addWidget(tabs_header)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("OrderTrackTabs")
        self.tabs.setTabBar(OrderDockTabBar(self.tabs))
        self.tabs.tabBar().setObjectName('OrderTrackTabBar')
        self.tabs.setDocumentMode(False)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.tabBar().setUsesScrollButtons(True)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().tearOff.connect(self.detach_order)
        self.tabs.tabBar().reattachDrop.connect(self.reattach_order)
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_index)
        self.tabs.currentChanged.connect(lambda _index:self._retitle())
        root.addWidget(self.tabs, 1)

    def showEvent(self, event):
        super().showEvent(event)
        screen = self.screen()
        if screen:
            bounds = screen.availableGeometry()
            width = min(self.width(), max(700, bounds.width() - 35))
            height = min(self.height(), max(500, bounds.height() - 35))
            self.setMinimumSize(min(700, width), min(500, height))
            if self.size().width() > width or self.size().height() > height:
                self.resize(width, height)
            if not getattr(self, '_positioned_once', False):
                frame = self.frameGeometry()
                frame.moveCenter(bounds.center())
                self.move(frame.topLeft())
                self._positioned_once = True

    def closeEvent(self,event):
        # A detached editor must not retain a pointer to a closing host.
        # Dock live pages before this popup is destroyed.
        for sid in list(self.detached):
            self.reattach_order(sid)
        super().closeEvent(event)

    def add_order(self, sid):
        sid = str(sid)
        if sid in self.pages:
            if sid in self.detached:
                self.detached[sid].showNormal()
                self.detached[sid].raise_()
                self.detached[sid].activateWindow()
                return
            self.tabs.setCurrentWidget(self.pages[sid])
            self._retitle()
            return
        page = SiparisEditor(self.db, self.covers, sid, self.on_updated, self, mode='track', embedded=True)
        self.pages[sid] = page
        page.track_host = self
        self.tabs.addTab(page, f'#{sid}')
        self.tabs.setCurrentWidget(page)
        self._retitle()

    def close_order_tab(self, sid):
        sid = str(sid)
        page = self.pages.get(sid)
        if page is None:
            return
        if sid in self.detached:
            self.reattach_order(sid)
        index = self.tabs.indexOf(page)
        if index >= 0:
            self._close_index(index)

    def _close_index(self, index):
        widget = self.tabs.widget(index)
        if widget is None:
            return
        sid = str(getattr(widget, 'sid', ''))
        self.tabs.removeTab(index)
        widget.deleteLater()
        self.pages.pop(sid, None)
        self._retitle()
        if not self.pages:
            self.close()

    def detach_order(self,index,global_position):
        page=self.tabs.widget(index)
        if page is None:
            return
        sid=str(page.sid)
        if sid in self.detached:
            return
        self.tabs.removeTab(index)
        window=DetachedOrderWindow(self,page,global_position)
        self.detached[sid]=window
        self._retitle()

    def reattach_order(self,sid,from_close=False):
        sid=str(sid)
        window=self.detached.pop(sid,None)
        if window is None:
            return
        page=self.pages.get(sid)
        if page is not None:
            window.layout().removeWidget(page)
            page.setParent(self.tabs)
            self.tabs.addTab(page,f'#{sid}')
            self.tabs.setCurrentWidget(page)
            page.show()
        window.host=None
        if not from_close:
            window.close()
        window.deleteLater()
        self.showNormal()
        self._retitle()

    def _retitle(self):
        count = self.tabs.count()
        self.tabs_count.setText(f'{count} sekme · {len(self.detached)} ayrı pencere')
        light = bool(QApplication.instance() and QApplication.instance().property('alfa_theme') == 'acik')
        if light:
            stage_labels = {'aktif': ('AKTİF', '#276e9b', '●'),
                            'tamamlandi': ('TAMAMLANDI', '#277a58', '✓'),
                            'havuz': ('HAVUZ', '#936024', '○')}
        else:
            stage_labels = {'aktif': ('AKTİF', '#66b6ff', '●'),
                            'tamamlandi': ('TAMAMLANDI', '#6ce0b0', '✓'),
                            'havuz': ('HAVUZ', '#f1c38f', '○')}
        for index in range(self.tabs.count()):
            page = self.tabs.widget(index)
            sid = str(getattr(page, 'sid', ''))
            order = page.current() if page else None
            state = self.db.siparis_durumu(order) if order else 'havuz'
            label, color, symbol = stage_labels[state]
            self.tabs.setTabText(index, f'{symbol} #{sid} · {label}')
            self.tabs.tabBar().setTabTextColor(index, QColor(color))
            self.tabs.setTabToolTip(index, f'Sipariş #{sid} — {label}')
            if page and page._rendered_status != state:
                page.build_ui()
        current = self.tabs.currentWidget()
        if current is not None:
            sid = getattr(current, 'sid', '')
            self.setWindowTitle(f'ALFA ERP · Sipariş Detayları · #{sid}')
        else:
            self.setWindowTitle('ALFA ERP · Sipariş Detayları')
