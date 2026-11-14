"""Siparişlere Genel Bakış: bütün siparişlerin kitap kodu bazlı baskı havuzu."""
from PySide6.QtCore import Qt, QTimer, QUrl, QEvent
from PySide6.QtWidgets import (
    QWidget, QDialog, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit,
    QProgressBar, QScrollArea, QGridLayout, QFileDialog, QMessageBox
)
from PySide6.QtGui import QDesktopServices
from pathlib import Path
from pdf_kitap import PdfKutuphane
from widgets import button, text, cover_label, scrollable, clear_layout
from utils import metin_eslesiyor_mu
from temali_combo import AlfaTemaliCombo
from kart_siparis import ProgressCover, pool_cover_group, set_boxed_card_style


class SiparisKitapHavuzu(QDialog):
    """Katalogdaki tekil kitap kodlarını siparişlerdeki SB/RNK adetleriyle birleştirir."""
    def __init__(self, db, covers, on_open_order, parent=None):
        super().__init__(parent)
        self.setObjectName("BookPoolDialog")
        self.setWindowTitle("ALFA ERP · Siparişlere Genel Bakış")
        self.resize(1400, 790)
        self.setMinimumSize(940, 590)
        self._recent_code = None
        self.db = db
        self.covers = covers
        self.on_open_order = on_open_order
        self.rows_data = []
        self.visible_limit = 48
        self._card_states = {}
        self._layout_columns = None
        self._orders_timer = QTimer(self)
        self._orders_timer.setSingleShot(True)
        self._orders_timer.setInterval(180)
        self._orders_timer.timeout.connect(self._refresh_orders_behind)
        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.setInterval(65)
        self._reflow_timer.timeout.connect(self._adapt_grid)
        self.pdfs = PdfKutuphane(Path(db.sepet_dosyasi).parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(9)
        root.setContentsMargins(13, 13, 13, 13)

        bar = QFrame();bar.setObjectName('BookPoolToolbar')
        bar_l = QVBoxLayout(bar);bar_l.setContentsMargins(12,10,12,10);bar_l.setSpacing(8)
        first = QHBoxLayout()
        first.addWidget(text('KİTAP BAZINDA BASKI HAVUZU','BookPoolTitle'))
        self.metrics = text('', 'OrderMetrics')
        first.addStretch();first.addWidget(self.metrics)
        close = button("Kapat", "SmallAction")
        close.clicked.connect(self.close)
        first.addWidget(close)
        bar_l.addLayout(first)

        filters = QHBoxLayout();filters.setSpacing(7)
        self.search = QLineEdit()
        self.search.setObjectName('OrderSearch')
        self.search.setPlaceholderText('Kitap adı, kod veya alt grup ile ara...')
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(36)
        filters.addWidget(self.search,1)
        # Yalnızca aktif siparişlerde bulunan kitaplar işlem yapılabilir.
        # Havuz/tamamlanan kayıtları dahil etmek yanlış baskı sayacı üretiyordu.
        active_tag = text('●  AKTİF SİPARİŞLER', 'PoolActiveScope')
        active_tag.setToolTip('Buradaki kitaplar ve adetler yalnızca aktif siparişlerden hesaplanır.')
        active_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        active_tag.setFixedSize(160, 36)
        filters.addWidget(active_tag)
        self.group = AlfaTemaliCombo();self.group.setObjectName('OrderFilter')
        self.group.setFixedSize(175,36)
        self.group.setToolTip('Kitap alt grubuna göre süz')
        filters.addWidget(self.group)
        self.progress_filter = AlfaTemaliCombo();self.progress_filter.setObjectName('OrderFilter')
        for label,key in (
            ('Tüm ilerlemeler','all'),('Baskı bekleyenler','unready'),
            ('Hazırlananlar','progress'),('Kolileme bekleyenler','unboxed'),
            ('Tamamı kolilenenler','boxed'),
        ):
            self.progress_filter.addItem(label,key)
        self.progress_filter.setFixedSize(165,36)
        filters.addWidget(self.progress_filter)
        self.sort = AlfaTemaliCombo();self.sort.setObjectName('OrderFilter')
        for name,key in (('Kalan baskı ↓','remaining'),('Toplam adet ↓','total'),
                         ('Kitap adı A–Z','name'),('Kod ↑','code')):
            self.sort.addItem(name,key)
        self.sort.setFixedSize(130,36)
        filters.addWidget(self.sort)
        bar_l.addLayout(filters)
        root.addWidget(bar)

        self.result_note = text('', 'Muted')
        root.addWidget(self.result_note)
        self.container = QWidget()
        self.container_layout = QGridLayout(self.container)
        self.container_layout.setContentsMargins(0,0,5,10)
        self.container_layout.setHorizontalSpacing(10)
        self.container_layout.setVerticalSpacing(10)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.area = scrollable(self.container)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.area.viewport().installEventFilter(self)
        root.addWidget(self.area,1)
        self.more = button('Daha fazla kitap göster', 'SmallAction')
        self.more.clicked.connect(self.show_more)
        root.addWidget(self.more,0,Qt.AlignmentFlag.AlignHCenter)

        self.timer = QTimer(self);self.timer.setSingleShot(True)
        self.timer.setInterval(220)
        self.timer.timeout.connect(self.apply_filters)
        self.search.textChanged.connect(lambda *_:self.timer.start())
        self.group.currentIndexChanged.connect(self.apply_filters)
        self.progress_filter.currentIndexChanged.connect(self.apply_filters)
        self.sort.currentIndexChanged.connect(self.apply_filters)
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        screen = self.screen()
        if screen:
            area = screen.availableGeometry()
            width = min(self.width(), max(570, area.width()-36))
            height = min(self.height(), max(480, area.height()-36))
            self.setMinimumSize(min(570,width),min(480,height))
            if self.width()>width or self.height()>height:
                self.resize(width,height)
            if not getattr(self,'_positioned_once',False):
                frame=self.frameGeometry()
                frame.moveCenter(area.center())
                self.move(frame.topLeft())
                self._positioned_once=True
        self._reflow_timer.start(0)

    def eventFilter(self, source, event):
        if source is getattr(self, 'area', None).viewport() and event.type() == QEvent.Type.Resize:
            self._reflow_timer.start()
        return super().eventFilter(source, event)

    def _column_count(self):
        w = self.area.viewport().width()
        return 4 if w>=1380 else 3 if w>=1050 else 2 if w>=700 else 1

    def _adapt_grid(self):
        if self._column_count() != self._layout_columns:
            self.render()

    def _aggregate(self):
        all_items = {}
        for order in self.db.siparisler:
            status = self.db.siparis_durumu(order)
            if status != 'aktif':
                continue
            for item in order.get('kitaplar',[]):
                code = str(item.get('kod','')).strip()
                if not code:
                    continue
                try:
                    qty = max(0,int(item.get('adet',0)))
                    ready = min(qty,max(0,int(item.get('hazir',0))))
                    boxed = min(ready,max(0,int(item.get('koli',0))))
                except (TypeError,ValueError):
                    continue
                if not qty:
                    continue
                book = self.db.katalog.get(code,{'kod':code,'isim':f'Kitap #{code}'})
                row = all_items.setdefault(code,{
                    'kod':code,'book':book,'name':book.get('isim',code),
                    'group':book.get('grup',''),'sb':0,'rnk':0,
                    'sb_ready':0,'rnk_ready':0,'sb_boxed':0,'rnk_boxed':0,
                    'sb_active':0,'rnk_active':0,'sb_active_ready':0,'rnk_active_ready':0,
                    'sb_active_boxed':0,'rnk_active_boxed':0,
                    'eligible':{},
                    'orders':{},
                })
                kind = 'rnk' if str(item.get('tur','SB')).upper() == 'RNK' else 'sb'
                row[kind] += qty
                row[kind+'_ready'] += ready
                row[kind+'_boxed'] += boxed
                if status == 'aktif':
                    row[kind+'_active'] += qty
                    row[kind+'_active_ready'] += ready
                    row[kind+'_active_boxed'] += boxed
                    elig = row['eligible']
                    for field, delta, can in (
                        ('hazir', 1, ready < qty), ('hazir', -1, ready > 0),
                        ('koli', 1, boxed < ready), ('koli', -1, boxed > 0),
                    ):
                        elig[kind,field,delta] = bool(elig.get((kind,field,delta),False) or can)
                row['orders'][str(order['id'])] = {
                    'id':str(order['id']),'status':status,
                    'platform':str(order.get('platform','')),
                }
        return list(all_items.values())

    def refresh(self,*_):
        self.rows_data = self._aggregate()
        old_group = self.group.currentData()
        self.group.blockSignals(True)
        self.group.clear()
        self.group.addItem('Bütün alt gruplar',None)
        for name in sorted({str(r['group']) for r in self.rows_data if r['group']}):
            self.group.addItem(name,name)
        self.group.setCurrentIndex(max(0,self.group.findData(old_group)))
        self.group.blockSignals(False)
        self.apply_filters()

    def _matches(self,row):
        query = self.search.text().strip()
        if query and not metin_eslesiyor_mu(query,' '.join((row['kod'],row['name'],str(row['group'])))):
            return False
        if self.group.currentData() and row['group'] != self.group.currentData():
            return False
        total = row['sb']+row['rnk']
        ready = row['sb_ready']+row['rnk_ready']
        boxed = row['sb_boxed']+row['rnk_boxed']
        kind = self.progress_filter.currentData()
        if kind=='unready' and ready>=total:return False
        if kind=='progress' and ready<=0:return False
        if kind=='unboxed' and ready<=boxed:return False
        if kind=='boxed' and boxed<total:return False
        return True

    def apply_filters(self,*_):
        data = [r for r in self.rows_data if self._matches(r)]
        key = self.sort.currentData()
        if key == 'name':
            data.sort(key=lambda r:r['name'].casefold())
        elif key == 'code':
            data.sort(key=lambda r:int(r['kod']) if r['kod'].isdigit() else 999999)
        elif key == 'total':
            data.sort(key=lambda r:r['sb']+r['rnk'],reverse=True)
        else:
            data.sort(key=lambda r:r['sb']+r['rnk']-r['sb_ready']-r['rnk_ready'],reverse=True)
        self.filtered_data = data
        self.visible_limit = 48
        self.render()
        self.area.verticalScrollBar().setValue(0)

    def render(self):
        clear_layout(self.container_layout)
        self._card_states = {}
        display = self.filtered_data[:self.visible_limit]
        total = sum(r['sb']+r['rnk'] for r in self.filtered_data)
        ready = sum(r['sb_ready']+r['rnk_ready'] for r in self.filtered_data)
        boxed = sum(r['sb_boxed']+r['rnk_boxed'] for r in self.filtered_data)
        self.metrics.setText(
            f"{len(self.filtered_data)} çeşit   ·   {total} kitap   ·   "
            f"{total-ready} baskı bekliyor   ·   {boxed} kolilendi"
        )
        self.result_note.setText(
            f"{len(display)} / {len(self.filtered_data)} kitap gösteriliyor. "
            'Yalnızca aktif siparişler gösterilir. Sipariş numarasına tıklayarak detayını açabilirsiniz.'
        )
        width = self.area.viewport().width()
        columns = self._column_count()
        self._layout_columns = columns
        self._card_count = len(display)
        for i,row in enumerate(display):
            self.container_layout.addWidget(self.make_row(row), i//columns, i%columns)
        if not display:
            self.container_layout.addWidget(text('Aktif siparişlerde bu filtreye uygun kitap yok.','Muted'),0,0)
        for col in range(4):
            self.container_layout.setColumnStretch(col,1 if col < columns else 0)
        self.more.setVisible(len(self.filtered_data)>len(display))

    def show_more(self):
        self.visible_limit += 48
        previous = self.area.verticalScrollBar().value()
        self.render()
        QTimer.singleShot(0,lambda:self.area.verticalScrollBar().setValue(previous))

    def open_pdf(self, code):
        """Kitap kodu ile tekil PDF aç; ilk kullanımda klasör seçtir."""
        if not self.pdfs.folder or not self.pdfs.folder.is_dir():
            chosen = QFileDialog.getExistingDirectory(self,'Kitap PDF klasörünü seç',str(Path.home()))
            if not chosen:
                return
            self.pdfs.set_folder(chosen)
        paths, missing = self.pdfs.resolve_many([code])
        if missing or not paths:
            QMessageBox.warning(self,'PDF bulunamadı',
                                f'#{code} için PDF bulunamadı. Dosya adını {code}.pdf yapabilirsiniz.')
            return
        for path in paths:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def change_progress(self,code,kind,field,delta):
        """Toplam sipariş adedine dokunmadan aktif kayıtlarda bir kopya ilerlet."""
        choices=[]
        for order in self.db.siparisler:
            if self.db.siparis_durumu(order) != 'aktif':
                continue
            for item in order.get('kitaplar',[]):
                if str(item.get('kod')) == str(code) and str(item.get('tur','SB')).upper() == kind:
                    choices.append((order,item))
        choices.sort(key=lambda pair: str(pair[0].get('tarih','')))
        if delta < 0:
            choices.reverse()
        for order,item in choices:
            amount=int(item.get('adet',0));ready=int(item.get('hazir',0));boxed=int(item.get('koli',0))
            if field=='hazir':
                next_ready=max(0, min(amount, ready+delta))
                if next_ready == ready:
                    continue
                # Hazır düşerse koli de yeni tavana otomatik iner.
                next_boxed=min(boxed, next_ready)
            else:
                next_boxed=boxed+delta
                if not (0<=next_boxed<=ready):
                    continue
                next_ready=ready
            try:
                self.db.siparis_ilerleme_degistir(order,code,kind,next_ready,next_boxed)
            except Exception as exc:
                QMessageBox.warning(self,'İşlem yapılamadı',str(exc))
                return
            self._recent_code = str(code)
            self._update_after_progress(str(code))
            self._orders_timer.start()
            return
        self.result_note.setText(
            f'#{code}: Bu işlem için uygun aktif sipariş kopyası bulunamadı. '
            'İlgili kitap için değiştirilebilir aktif sipariş adedi yok.'
        )

    def _refresh_orders_behind(self):
        main=self.parentWidget()
        orders=getattr(main,'orders',None)
        if orders is not None:
            orders.refresh_rows()
            orders.refresh_open_track_progress()

    def _update_after_progress(self, code):
        """Single book counters update in place. Do not recreate cards or jump scroll."""
        data = {r['kod']:r for r in self._aggregate()}
        current = data.get(str(code))
        if not current:
            return
        for old in self.rows_data:
            if old['kod']==str(code):
                old.update(current)
        state = self._card_states.get(str(code))
        if state:
            state['quantity'].setText(self._quantity_text(current))
            for kind in ('sb','rnk'):
                if kind not in state['variants']:
                    continue
                var=state['variants'][kind]
                amount=current[kind]
                var['amount'].setText(f'{amount} adet')
                var['active'].setText(f'Aktif toplam: {current[kind+"_active"]} adet')
                for field,suffix in (('hazir','ready'),('koli','boxed')):
                    var[field].setText(f'{current[kind+"_"+suffix]}/{amount}')
                    for delta in (-1,1):
                        var['buttons'][(field,delta)].setEnabled(
                            current['eligible'].get((kind,field,delta),False))
            card = state['card']
            card.setProperty('poolRecent',True)
            progress=pool_cover_group(current)
            state['cover'].set_progress(progress,active=True)
            set_boxed_card_style(card,progress)
            card.style().unpolish(card)
            card.style().polish(card)
            card.update()
        total=sum(r['sb']+r['rnk'] for r in self.rows_data)
        ready=sum(r['sb_ready']+r['rnk_ready'] for r in self.rows_data)
        boxed=sum(r['sb_boxed']+r['rnk_boxed'] for r in self.rows_data)
        self.metrics.setText(f'{len(self.rows_data)} çeşit · {total} kitap · {total-ready} baskı bekliyor · {boxed} kolilendi')
        self.result_note.setText(f'#{code} güncellendi. Aktif siparişlerin yeni Hazır/Koli durumu kaydedildi.')

    @staticmethod
    def _quantity_text(row):
        total = row['sb']+row['rnk']
        ready = row['sb_ready']+row['rnk_ready']
        return f'{total} kitap · {total-ready} baskı bekliyor'

    def make_row(self,row):
        """Üst solda kapak/bilgi, sağda SB/RNK; altta sipariş bağlantıları ve PDF."""
        frame = QFrame()
        frame.setObjectName('PoolBookRow')
        state = {'card':frame,'variants':{}}
        self._card_states[str(row['kod'])] = state
        frame.setProperty('poolRecent', str(row['kod']) == self._recent_code)
        progress=pool_cover_group(row)
        set_boxed_card_style(frame,progress)
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(11, 10, 11, 10)
        outer.setSpacing(9)

        top = QHBoxLayout()
        top.setSpacing(11)
        left = QVBoxLayout()
        left.setSpacing(4)
        cover = ProgressCover(row['book'],self.covers,progress,112,155,active=True,show_partial=False)
        state['cover']=cover
        left.addWidget(cover, 0, Qt.AlignmentFlag.AlignHCenter)
        title = text(row['name'], 'PoolBookName', wrap=True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setMaximumHeight(45)
        title.setToolTip(row['name'])
        left.addWidget(title)
        sub = text(f"#{row['kod']} · {row['book'].get('sayfa',0)} sayfa", 'PoolBookInfo')
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(sub)
        grp = text(str(row['group']), 'PoolBookInfo', wrap=True)
        grp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grp.setMaximumHeight(30)
        left.addWidget(grp)
        left.addStretch(1)
        left_box = QWidget()
        left_box.setObjectName('PoolCoverInfo')
        left_box.setFixedWidth(133)
        left_box.setLayout(left)
        top.addWidget(left_box, 0, Qt.AlignmentFlag.AlignTop)

        right = QVBoxLayout()
        right.setSpacing(7)
        total = row['sb'] + row['rnk']
        ready = row['sb_ready'] + row['rnk_ready']
        quantity = text(self._quantity_text(row), 'PoolQuantityPill')
        quantity.setMinimumHeight(32)
        quantity.setToolTip('Yalnızca aktif siparişlerdeki toplam kitap ve bekleyen baskı adedi.')
        state['quantity'] = quantity
        right.addWidget(quantity)
        for key, label, role in (('sb','SB · Siyah Beyaz','PoolVariantSB'),
                                 ('rnk','RNK · Renkli','PoolVariantRNK')):
            amount = row[key]
            if not amount:
                continue
            block = QFrame(); block.setObjectName(role)
            v = QVBoxLayout(block)
            v.setContentsMargins(8, 7, 8, 7)
            v.setSpacing(6)
            heading = QHBoxLayout()
            heading.addWidget(text(label,'PoolVariantTitle'))
            heading.addStretch()
            amount_label=text(str(amount) + ' adet', 'PoolVariantCount')
            heading.addWidget(amount_label)
            v.addLayout(heading)
            active_label=text(f'Aktif toplam: {row[key+"_active"]} adet','PoolMiniLabel')
            v.addWidget(active_label)
            var_state={'amount':amount_label,'active':active_label,'buttons':{}}
            state['variants'][key]=var_state
            for field, caption in (('hazir','Hazır'), ('koli','Koli')):
                row_controls = QHBoxLayout()
                row_controls.setSpacing(5)
                row_controls.addWidget(text(caption,'PoolMiniLabel'))
                counter=text(f"{row[key+'_'+('ready' if field=='hazir' else 'boxed')]}/{amount}", 'PoolMiniValue')
                counter.setFixedWidth(49)
                counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
                var_state[field]=counter
                row_controls.addWidget(counter)
                row_controls.addStretch()
                for delta, sign in ((-1,'−'),(1,'+')):
                    control = button(sign, 'PoolMiniStep')
                    control.setFixedSize(23, 23)
                    control.setEnabled(row['eligible'].get((key,field,delta),False))
                    var_state['buttons'][(field,delta)]=control
                    control.setAccessibleName(f"#{row['kod']} {label} {caption} {'azalt' if delta<0 else 'artır'}")
                    control.clicked.connect(lambda checked=False,c=row['kod'],k=key.upper(),f=field,d=delta:
                                            self.change_progress(c,k,f,d))
                    row_controls.addWidget(control)
                v.addLayout(row_controls)
            right.addWidget(block)
        right.addStretch()
        top.addLayout(right,1)
        outer.addLayout(top,1)

        bottom = QFrame()
        bottom.setObjectName('PoolOrderLinks')
        b = QVBoxLayout(bottom)
        b.setContentsMargins(8, 7, 8, 7)
        b.setSpacing(5)
        b.addWidget(text('Bulunduğu siparişler', 'PoolLinksTitle'))
        links = QGridLayout();links.setHorizontalSpacing(5);links.setVerticalSpacing(5)
        ids = sorted((sid for sid,o in row['orders'].items() if o['status'] != 'havuz'),
                     key=lambda key:int(key) if key.isdigit() else 0,reverse=True)
        for n, sid in enumerate(ids):
            order = row['orders'][sid]
            chip = button(f'#{sid}', 'PoolOrderLink')
            chip.setToolTip(f"#{sid} · {order['platform']} · {self._status_name(order['status'])} — Siparişe git")
            chip.clicked.connect(lambda checked=False,id=sid:self.on_open_order(id))
            links.addWidget(chip, n//5, n%5)
        if ids:
            b.addLayout(links)
        else:
            b.addWidget(text('Aktif sipariş bulunmuyor', 'Muted'))
        outer.addWidget(bottom)

        footer = QHBoxLayout()
        footer.addStretch()
        pdf = button('PDF Aç  ↗', 'PoolPdfAction')
        pdf.setMinimumWidth(130)
        pdf.clicked.connect(lambda checked=False,c=row['kod']:self.open_pdf(c))
        footer.addWidget(pdf)
        outer.addLayout(footer)
        return frame

    @staticmethod
    def _status_name(status):
        return {'havuz':'Havuz','aktif':'Aktif','tamamlandi':'Tamamlanan'}.get(status,status)
