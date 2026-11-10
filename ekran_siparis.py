"""Sipariş listesi: tek kompakt filtre şeridi, kart önbelleği ve dinamik seçim."""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QCheckBox,
    QFrame, QToolButton, QListView, QAbstractItemView, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from widgets import text, button, scrollable, error, confirm
from utils import metin_eslesiyor_mu
from kart_siparis import SiparisKarti
from editor_siparis import SiparisEditor
from takvim import TarihPopup
from kargo_fisi import dosyaya_yaz, tarayicida_ac
from kargo_ucreti import request_shipping_cost
from siparis_arsivi import ayir_tamamlananlar
from temali_combo import AlfaTemaliCombo


class SiparisView(QWidget):
    def __init__(self, db, covers, on_open_pool=None, admin_mode=False):
        super().__init__()
        self.db = db
        self.admin_mode = bool(admin_mode)
        self.covers = covers
        self.status = 'havuz'
        self.selected = set()
        self.from_date = self.to_date = None
        self.windows = {}
        self.popup = None
        self.on_open_pool = on_open_pool
        self._row_cache = {}
        self._row_signatures = {}
        self._empty_row = None
        self._recent_sid = None
        # Tamamlananlar: yalnızca son 5 günlük kartları otomatik oluştur.
        # Arşiv siparişleri kullanıcı çağırana kadar widget olarak yüklenmez.
        self._archive_open = False
        self._archive_limit = 25
        self._archive_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        self.toolbar = QFrame()
        self.toolbar.setObjectName('OrderToolbar')
        outer = QVBoxLayout(self.toolbar)
        outer.setContentsMargins(9, 5, 9, 5)
        outer.setSpacing(6)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.search = QLineEdit()
        self.search.setObjectName('OrderSearch')
        self.search.setPlaceholderText('Sipariş no, kargo kodu veya kitap adıyla arayın...')
        self.search.setToolTip('Sipariş numarası, kitap adı veya kargo kodu araması')
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(36)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(lambda: self.refresh_rows(reset_position=True))
        self.search.textChanged.connect(lambda *_: self._search_timer.start())
        filters.addWidget(self.search, 1)

        self.filter_segment = QFrame()
        self.filter_segment.setObjectName('OrderFilterSegment')
        segment = QHBoxLayout(self.filter_segment)
        segment.setContentsMargins(4, 3, 4, 3)
        segment.setSpacing(4)
        self.day = AlfaTemaliCombo()
        self.day.setObjectName('OrderFilter')
        self.day.setMaxVisibleItems(12)
        self.day.setFixedSize(142, 36)
        self.day.currentIndexChanged.connect(self.on_day_changed)
        self.day.setToolTip('Sadece sipariş bulunan tarihleri gösterir')
        segment.addWidget(self.day)
        self.calendar_btn = button('▦  Takvim', 'CalendarTrigger')
        self.calendar_btn.setFixedSize(94, 36)
        self.calendar_btn.setToolTip('Bir gün seç; Shift ile tarih aralığı seç')
        self.calendar_btn.clicked.connect(self.open_calendar)
        segment.addWidget(self.calendar_btn)
        self.sort = AlfaTemaliCombo()
        self.sort.setObjectName('OrderFilter')
        self.sort.setMaxVisibleItems(10)
        self.sort.setFixedSize(153, 36)
        for label, kind in (
            ('Eklenme tarihi', 'date'), ('Sipariş no', 'id'),
            ('Ciro', 'money'), ('Kitap sayısı', 'adet'), ('Sayfa sayısı', 'sayfa'),
        ):
            self.sort.addItem(label, kind)
        self.sort.currentIndexChanged.connect(self.refresh_rows)
        self.sort.setToolTip('Sıralama ölçütü')
        segment.addWidget(self.sort)
        self.reverse_btn = QToolButton()
        self.reverse_btn.setObjectName('OrderSortReverse')
        self.reverse_btn.setText('↓')
        self.reverse_btn.setCheckable(True)
        self.reverse_btn.setFixedSize(36, 36)
        self.reverse_btn.setToolTip('Sıralamayı tersine çevir')
        self.reverse_btn.toggled.connect(self.reverse_sort)
        segment.addWidget(self.reverse_btn)
        reset = button('Temizle', 'OrderReset')
        reset.setFixedSize(72, 36)
        reset.setToolTip('Arama, tarih ve sıralamayı sıfırla')
        reset.clicked.connect(self.reset_filters)
        segment.addWidget(reset)
        filters.addWidget(self.filter_segment)
        outer.addLayout(filters)

        summary = QHBoxLayout()
        summary.setSpacing(9)
        self.metrics = text('', 'OrderMetrics')
        summary.addWidget(self.metrics)
        summary.addStretch()
        self.all_cb = QCheckBox('Görünen siparişleri seç')
        self.all_cb.stateChanged.connect(self.select_visible)
        summary.addWidget(self.all_cb)
        self.selected_label = text('0 seçili', 'OrderSelectedCount')
        summary.addWidget(self.selected_label)
        self.pool_btn = button('▤  Siparişlere genel bakış', 'OrderPoolCTA')
        self.pool_btn.setToolTip('Kitap bazlı toplam baskı havuzunu aç')
        self.pool_btn.setAccessibleName('Siparişlere genel bakış penceresini aç')
        self.pool_btn.clicked.connect(lambda: self.on_open_pool() if self.on_open_pool else None)
        self.print_btn = button('▣  Seçilenlerin kargo fişi', 'OrderPrintCTA')
        self.print_btn.setToolTip('İşaretlediğiniz siparişlerin kargo fişlerini oluşturur')
        self.print_btn.setAccessibleName('Seçilen siparişlerin kargo fişlerini oluştur')
        self.print_btn.clicked.connect(self.print_selected)
        # Yan yana duran ana işlemler aynı yükseklik, köşe yarıçapı,
        # tipografi ve hover davranışını tema üzerinden paylaşır.
        for action in (self.pool_btn, self.print_btn):
            action.setFixedHeight(38)
            action.setMinimumWidth(178)
            action.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        summary.addWidget(self.pool_btn)
        summary.addWidget(self.print_btn)
        outer.addLayout(summary)
        root.addWidget(self.toolbar)

        self.archive_header = QFrame()
        self.archive_header.setObjectName('CompletedArchiveBar')
        arch_layout = QHBoxLayout(self.archive_header)
        arch_layout.setContentsMargins(12, 5, 12, 5)
        arch_layout.setSpacing(10)
        self.archive_text = text('Son 5 günün tamamlanan siparişleri', 'ArchiveStatus')
        arch_layout.addWidget(self.archive_text)
        arch_layout.addStretch(1)
        self.archive_btn = button('Arşivi aç', 'ArchiveToggle')
        self.archive_btn.setToolTip('5 günden eski tamamlanan siparişleri yalnızca talep edildiğinde görüntüler')
        self.archive_btn.clicked.connect(self.toggle_archive)
        arch_layout.addWidget(self.archive_btn)
        self.archive_header.setVisible(False)
        root.addWidget(self.archive_header)

        self.rows = QWidget()
        self.rows_lay = QVBoxLayout(self.rows)
        self.rows_lay.setSpacing(8)
        self.rows_lay.setContentsMargins(1, 1, 6, 6)
        self.rows_scroll = scrollable(self.rows)
        self.rows_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(self.rows_scroll, 1)
        self.archive_more = button('25 sipariş daha göster', 'ArchiveLoadMore')
        self.archive_more.setToolTip('Arşivdeki bir sonraki 25 kaydı yükle')
        self.archive_more.clicked.connect(self.load_more_archive)
        self.archive_more.setVisible(False)
        root.addWidget(self.archive_more, 0, Qt.AlignmentFlag.AlignHCenter)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(90)
        self._resize_timer.timeout.connect(self._adapt_cards)
        self.refresh()
        QTimer.singleShot(0, self._adapt_cards)

    def showEvent(self,event):
        super().showEvent(event)
        self._resize_timer.start(0)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if event.size().width()!=event.oldSize().width() and hasattr(self,'_resize_timer'):
            self._resize_timer.start()

    def _adapt_cards(self):
        width=self.rows_scroll.viewport().width()
        compact=width<1080
        for card in self._row_cache.values():
            card.set_compact_mode(compact)
        # Preserve every function when the window is narrow; use shorter labels
        # instead of generating a window-wide horizontal scrollbar.
        self.all_cb.setText('Seç' if compact else 'Görünen siparişleri seç')
        self.pool_btn.setText('▤  Kitap havuzu' if compact else '▤  Siparişlere genel bakış')
        self.print_btn.setText('▣  Kargo fişi' if compact else '▣  Seçilenlerin kargo fişi')
        # Dar pencere boyutlarında metin kısalır; iki buton yine aynı
        # geometri ve hizada kalır. Kartları yeniden üretmeye gerek yok.
        for action in (self.pool_btn, self.print_btn):
            action.setMinimumWidth(112 if compact else 178)

    def current(self):
        return [o for o in self.db.siparisler if self.db.siparis_durumu(o) == self.status]

    def _completed_partitions(self):
        return ayir_tamamlananlar(self.current())

    def dates(self):
        if self.status == 'tamamlandi':
            recent, archived = self._completed_partitions()
            source = archived if self._archive_open else recent
            # Tamamlanma gününü değil, filtrelemede kullanılan eklenme
            # tarihini göster; arşivde seçilen tarih gerçekten eşleşir.
        else:
            source = self.current()
        return sorted({str(o.get('tarih',''))[:10] for o in source
                       if len(str(o.get('tarih',''))) >= 10}, reverse=True)

    def toggle_archive(self):
        if self.status != 'tamamlandi':
            return
        self._archive_open = not self._archive_open
        self._archive_limit = 25
        self.from_date = self.to_date = None
        self.calendar_btn.setText('▦  Takvim')
        self.refresh(reset_date=True)
        self.rows_scroll.verticalScrollBar().setValue(0)

    def load_more_archive(self):
        if self.status != 'tamamlandi' or not self._archive_open:
            return
        self._archive_limit += 25
        self.refresh_rows()

    def change_status(self, status):
        if status not in ('havuz', 'aktif', 'tamamlandi'):
            return
        if self.status != status:
            self.status = status
            self._archive_open = False
            self._archive_limit = 25
            self.selected.clear()
            self.from_date = self.to_date = None
            self._search_timer.stop()
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
            self.calendar_btn.setText('▦  Takvim')
            self.refresh(reset_date=True)
        else:
            self.refresh()

    def refresh(self, reset_date=False):
        selected_date = None if reset_date else self.day.currentData()
        self.day.blockSignals(True)
        self.day.clear()
        self.day.addItem('Tarih seç', None)
        for value in self.dates():
            try:
                label = datetime.fromisoformat(value).strftime('%d.%m.%Y')
            except ValueError:
                label = value
            self.day.addItem(label, value)
        self.day.setCurrentIndex(max(0, self.day.findData(selected_date)))
        self.day.blockSignals(False)
        self.refresh_rows()

    def on_day_changed(self, *_):
        if self.day.currentData() is not None:
            self.from_date = self.to_date = None
            self.calendar_btn.setText('▦  Takvim')
        self.refresh_rows(reset_position=True)

    def reverse_sort(self, checked):
        self.reverse_btn.setText('↑' if checked else '↓')
        self.refresh_rows(reset_position=True)

    def filtered(self):
        day = self.day.currentData()
        query = self.search.text().strip()
        result = []
        if self.status == 'tamamlandi':
            recent, archived = self._completed_partitions()
            source = archived if self._archive_open else recent
        else:
            source = self.current()
        for order in source:
            date = str(order.get('tarih',''))[:10]
            if day and date != day:
                continue
            if self.from_date and date < self.from_date:
                continue
            if self.to_date and date > self.to_date:
                continue
            if query and not metin_eslesiyor_mu(query, self.db.siparis_ara_metin(order)):
                continue
            result.append(order)
        reverse = not self.reverse_btn.isChecked()
        kind = self.sort.currentData()
        if kind == 'id':
            result.sort(key=lambda o:int(o['id']) if str(o['id']).isdigit() else str(o['id']), reverse=reverse)
        elif kind == 'money':
            result.sort(key=lambda o:float(o.get('ciro',0) or 0), reverse=reverse)
        elif kind in ('adet','sayfa'):
            result.sort(key=lambda o:self.db.siparis_ozeti(o)[kind], reverse=reverse)
        elif self.status == 'tamamlandi':
            # Arşiv tarih sırasını gerçekten tamamlanma gününe göre yap.
            result.sort(key=lambda o:str(o.get('tamamlanma_tarihi') or o.get('tarih','')), reverse=reverse)
        else:
            result.sort(key=lambda o:str(o.get('tarih','')), reverse=reverse)
        self._archive_count = len(result) if self.status == 'tamamlandi' else 0
        if self.status == 'tamamlandi' and self._archive_open:
            return result[:self._archive_limit]
        return result

    def _signature(self, order):
        # Hazır/koli miktarları bilerek bu imzaya katılmıyor:
        # sadece ilerleme değiştiğinde 30 kapak yeniden üretilmiyor.
        books = tuple((str(i.get('kod','')), str(i.get('tur','SB')),
                       int(i.get('adet',0))) for i in order.get('kitaplar', []))
        return (self.db.siparis_durumu(order), str(order.get('kod','')),
                str(order.get('platform','')), str(order.get('tarih','')),
                str(order.get('tamamlanma_tarihi','')),
                str(order.get('ciro',0)), books)

    def refresh_rows(self, *_, reset_position=False):
        old_pos = self.rows_scroll.verticalScrollBar().value()
        orders = self.filtered()
        totals = {'adet':0,'sayfa':0}
        revenue = 0
        # Mevcut widget'ları yerinde tut; sil-yeniden çiz döngüsünü önle.
        while self.rows_lay.count():
            item = self.rows_lay.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                if widget is self._empty_row:
                    widget.deleteLater()
                    self._empty_row = None
        existing_ids = {str(o['id']) for o in self.db.siparisler}
        rendered_ids = {str(o['id']) for o in orders}
        for sid in list(self._row_cache):
            # Arşiv sayfaları arasında widget biriktirme: yalnızca gerçekten
            # görünen kartlar önbellekte tutulur. Verilerde değişiklik yok.
            if sid not in existing_ids or (self.status == 'tamamlandi' and sid not in rendered_ids):
                old = self._row_cache.pop(sid)
                old.hide();old.deleteLater()
                self._row_signatures.pop(sid, None)
        for order in orders:
            sid = str(order['id'])
            overview = self.db.siparis_ozeti(order)
            totals['adet'] += overview['adet']
            totals['sayfa'] += overview['sayfa']
            revenue += float(order.get('ciro',0) or 0)
            signature = self._signature(order)
            if sid not in self._row_cache or self._row_signatures.get(sid) != signature:
                old = self._row_cache.pop(sid, None)
                if old is not None:
                    old.hide();old.deleteLater()
                self._row_cache[sid] = SiparisKarti(
                    self.db, order, self.covers, self.open_editor,
                    self.change_order, self.check_order,
                    selected=sid in self.selected, on_delete=self.delete_order if self.admin_mode else None,
                    allow_edit=self.admin_mode,
                )
                self._row_signatures[sid] = signature
            else:
                self._row_cache[sid].refresh_progress(self.db, order)
                self._row_cache[sid].set_selected(sid in self.selected)
            widget = self._row_cache[sid]
            widget.set_compact_mode(self.rows_scroll.viewport().width()<1080)
            self._update_recent_style(widget, sid)
            self.rows_lay.addWidget(widget)
            widget.show()
        if not orders:
            if self.status == 'tamamlandi' and not self._archive_open:
                empty_note = 'Son 5 günde tamamlanan sipariş bulunamadı. Daha eski kayıtlar için Arşivi açın.'
            elif self.status == 'tamamlandi':
                empty_note = 'Arşivde bu arama veya tarih seçimine uygun sipariş yok.'
            else:
                empty_note = 'Bu filtreye uygun sipariş yok. Arama veya tarih seçimini temizleyebilirsiniz.'
            self._empty_row = text(empty_note, 'Muted')
            self.rows_lay.addWidget(self._empty_row)
        self.rows_lay.addStretch()
        self.metrics.setText(
            f"{len(orders)} sipariş    ·    {totals['adet']} kitap    ·    "
            f"{totals['sayfa']:,} sayfa    ·    {revenue:,.2f} TL"
        )
        completed = self.status == 'tamamlandi'
        self.archive_header.setVisible(completed)
        if completed:
            recent, archived = self._completed_partitions()
            if self._archive_open:
                self.archive_text.setText(
                    f'Arşiv · {len(orders)} / {self._archive_count} sipariş gösteriliyor'
                )
                self.archive_btn.setText('← Son 5 güne dön')
                self.archive_more.setVisible(self._archive_count > len(orders))
            else:
                self.archive_text.setText(
                    f'Son 5 gün · {len(recent)} sipariş  |  Arşivde {len(archived)} sipariş'
                )
                self.archive_btn.setText(f'Arşivi aç  ({len(archived)})')
                self.archive_more.setVisible(False)
            self.archive_btn.setEnabled(bool(archived) or self._archive_open)
        else:
            self.archive_more.setVisible(False)
        active = self.status == 'aktif'
        for widget in (self.all_cb, self.selected_label, self.print_btn, self.pool_btn):
            widget.setVisible(active)
        self._update_selected(orders)
        QTimer.singleShot(0, lambda pos=0 if reset_position else old_pos:
                          self.rows_scroll.verticalScrollBar().setValue(pos))

    def _update_selected(self, orders=None):
        self.selected_label.setText(f'{len(self.selected)} seçili')
        self.print_btn.setEnabled(bool(self.selected))
        orders = self.filtered() if orders is None else orders
        visible_ids = {str(o['id']) for o in orders}
        is_all = bool(visible_ids) and visible_ids.issubset(self.selected)
        self.all_cb.blockSignals(True)
        self.all_cb.setChecked(is_all)
        self.all_cb.blockSignals(False)

    def _update_recent_style(self, row, sid):
        recent = str(sid) == self._recent_sid
        if row.property('orderRecent') != recent:
            row.setProperty('orderRecent', recent)
            row.style().unpolish(row)
            row.style().polish(row)
            row.update()

    def mark_recent(self, sid):
        self._recent_sid = str(sid)
        for code, row in self._row_cache.items():
            self._update_recent_style(row, code)

    def check_order(self, sid, checked):
        sid = str(sid)
        if checked:
            self.selected.add(sid)
        else:
            self.selected.discard(sid)
        if sid in self._row_cache:
            self._row_cache[sid].set_selected(checked)
        self._update_selected()

    def select_visible(self, checked):
        ids = {str(o['id']) for o in self.filtered()}
        if checked:
            self.selected.update(ids)
        else:
            self.selected.difference_update(ids)
        for sid in ids:
            if sid in self._row_cache:
                self._row_cache[sid].set_selected(sid in self.selected)
        self._update_selected()

    def change_order(self, order, new_status):
        action = {'aktif':'aktife alınsın','tamamlandi':'tamamlansın',
                  'havuz':'havuza geri alınsın'}.get(new_status, 'değiştirilsin')
        shipping_fee = None
        if new_status == 'tamamlandi':
            category = self.db.kargo_kategorisi(order)
            if category:
                label = 'Telafi siparişi' if category == 'telafi' else 'Normal açık adres siparişi'
                shipping_fee = request_shipping_cost(self, order, category)
                if shipping_fee is None:
                    return
        if not confirm(self, f"#{order['id']} numaralı sipariş {action} mı?"):
            return
        if new_status == 'tamamlandi':
            from alici_bilgileri import request_buyer_details
            from kargonomi_akisi import request_kargonomi_completion
            required=('alici_adi','telefon','adres','il','ilce')
            if any(not str(order.get(k) or '').strip() for k in required):
                buyer=request_buyer_details(self,order)
                if buyer is None:return
                order.update(buyer)
                self.db.siparisleri_kaydet()
            if not request_kargonomi_completion(self,self.db,order):
                return
        try:
            self.db.siparis_durumunu_degistir(order, new_status, kargo_ucreti=shipping_fee)
        except Exception as exc:
            return error(self, exc)
        self.selected.discard(str(order['id']))
        self.mark_recent(order['id'])
        self.refresh()

    def delete_order(self, order):
        durum = self.db.siparis_durumu(order)
        ad = {'tamamlandi':'tamamlanan sipariş', 'aktif':'aktif sipariş',
              'havuz':'havuz siparişi'}.get(durum, 'sipariş')
        if not confirm(self, f"#{order['id']} numaralı {ad} kalıcı olarak silinsin mi?\n"
                       "Önce verinizi yedeklemeniz önerilir."):
            return
        try:
            self.db.siparis_sil(order)
        except Exception as exc:
            return error(self, exc)
        self._recent_sid = None
        self.refresh()

    def _after_editor_updated(self):
        self.refresh()
        # A concurrently open book-pool popup should not display stale totals.
        main=self.window()
        pool=getattr(main,'bookpool',None)
        if pool is not None and pool.isVisible():
            pool.refresh()

    def open_editor(self, sid, tab='track'):
        """Sipariş penceresini aç; olası hatayı sessizce yutmak yerine göster."""
        if tab == 'edit' and not self.admin_mode:
            return error(self, 'Bu işlem Yönetici Paneli üzerinden yapılır.')
        mode = 'edit' if tab == 'edit' else 'track'
        self.mark_recent(sid)
        if mode == 'track':
            from editor_siparis import SiparisTakipSekmeleri
            key = 'track_hub'

            def build_track_window():
                hub = SiparisTakipSekmeleri(self.db, self.covers, self._after_editor_updated, self)
                self.windows[key] = hub
                hub.destroyed.connect(lambda obj=None,k=key:self.windows.pop(k,None))
                return hub

            window = None
            try:
                window = self.windows.get(key)
                if window is None:
                    window = build_track_window()
                try:
                    window.add_order(sid)
                except RuntimeError:
                    # Daha önce silinmiş Qt nesnesinin Python referansı kalmış.
                    self.windows.pop(key, None)
                    window = build_track_window()
                    window.add_order(sid)
                window.showNormal()
                window.raise_()
                window.activateWindow()
            except Exception as exc:
                self.windows.pop(key, None)
                error(self, f'Sipariş #{sid} detayı açılamadı:\n{type(exc).__name__}: {exc}')
            return

        key = f'{sid}:{mode}'
        try:
            if key in self.windows:
                try:
                    window = self.windows[key]
                    window.showNormal()
                    window.raise_()
                    window.activateWindow()
                    return
                except RuntimeError:
                    self.windows.pop(key, None)
            window = SiparisEditor(self.db, self.covers, sid, self._after_editor_updated, self, mode=mode)
            self.windows[key] = window
            window.destroyed.connect(lambda obj=None,k=key:self.windows.pop(k,None))
            window.show()
        except Exception as exc:
            self.windows.pop(key, None)
            error(self, f'Sipariş #{sid} düzenleme ekranı açılamadı:\n{type(exc).__name__}: {exc}')

    def focus_order(self, sid):
        """Kitap havuzundaki sipariş bağlantısına tıklandığında ilgili kartı gösterir."""
        sid = str(sid)
        self.from_date = self.to_date = None
        self.calendar_btn.setText('▦  Takvim')
        self.day.blockSignals(True)
        self.day.setCurrentIndex(0)
        self.day.blockSignals(False)
        self._search_timer.stop()
        self.search.blockSignals(True)
        self.search.setText(sid)
        self.search.blockSignals(False)
        self.refresh_rows(reset_position=True)
        if sid in self._row_cache:
            self.mark_recent(sid)
            row = self._row_cache[sid]
            row.setProperty('orderFocused', True)
            row.style().unpolish(row);row.style().polish(row)
            row.update()

    def print_selected(self):
        orders = [o for o in self.current() if str(o['id']) in self.selected]
        if not orders:
            return error(self, 'Önce en az bir aktif sipariş seçin.')
        try:
            tarayicida_ac(dosyaya_yaz(orders, self.db))
        except Exception as exc:
            error(self, exc)

    def open_calendar(self):
        self.popup = TarihPopup(self.dates(), self)
        self.popup.selected.connect(self.set_range)
        self.popup.open()

    def set_range(self, start, end):
        self.from_date = start
        self.to_date = (end or start) if start else None
        self.day.blockSignals(True)
        self.day.setCurrentIndex(0)
        self.day.blockSignals(False)
        if start:
            if end:
                self.calendar_btn.setText(f'▦ {start[8:10]}.{start[5:7]} – {end[8:10]}.{end[5:7]}')
            else:
                self.calendar_btn.setText(f'▦ {start[8:10]}.{start[5:7]}')
        else:
            self.calendar_btn.setText('▦  Takvim')
        self.refresh_rows(reset_position=True)

    def reset_filters(self):
        self._search_timer.stop()
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.from_date = self.to_date = None
        self.calendar_btn.setText('▦  Takvim')
        self.sort.blockSignals(True)
        self.sort.setCurrentIndex(0)
        self.sort.blockSignals(False)
        self.reverse_btn.blockSignals(True)
        self.reverse_btn.setChecked(False)
        self.reverse_btn.setText('↓')
        self.reverse_btn.blockSignals(False)
        self.refresh(reset_date=True)
        self.rows_scroll.verticalScrollBar().setValue(0)

    def clear_dates(self):
        self.from_date = self.to_date = None
        self.calendar_btn.setText('▦  Takvim')
        self.day.setCurrentIndex(0)
        self.refresh_rows(reset_position=True)
