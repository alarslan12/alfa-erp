"""ALFA ERP visual product catalog, inventory and sales analytics.

Responsive, variable-sized cards inspired by a bubble-map without hiding product
names, prices or controls. Product changes require the owner session; device
operators can record a sale. Network operations run outside the Qt UI thread.
"""
import base64
import math
from datetime import datetime, date, timedelta
from collections import defaultdict
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QPoint, QRect, QThread, Signal, QBuffer, QIODevice, QUrl, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QDialog, QVBoxLayout, QHBoxLayout,
    QLayout, QLabel, QLineEdit, QComboBox, QPushButton, QScrollArea,
    QTextEdit, QSpinBox, QDoubleSpinBox, QMessageBox, QFileDialog,
    QSizePolicy, QFormLayout, QStackedWidget, QProgressBar, QCompleter,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QInputDialog,
    QToolButton, QAbstractSpinBox
)
from inventory_batches import sorted_batches, batch_stock_value


class MosaicLayout(QLayout):
    """Multi-line Qt flow layout that keeps uneven cards in natural reading order."""
    def __init__(self,parent=None,spacing=13):
        super().__init__(parent)
        self._items=[]
        self.setContentsMargins(4,4,9,18)
        self.setSpacing(spacing)

    def addItem(self,item):self._items.append(item)
    def count(self):return len(self._items)
    def itemAt(self,i):return self._items[i] if 0<=i<len(self._items) else None
    def takeAt(self,i):return self._items.pop(i) if 0<=i<len(self._items) else None
    def expandingDirections(self):return Qt.Orientation(0)
    def hasHeightForWidth(self):return True
    def heightForWidth(self,w):return self._layout(QRect(0,0,w,0),True)
    def sizeHint(self):return self.minimumSize()
    def minimumSize(self):
        size=QSize(200,200)
        for item in self._items:size=size.expandedTo(item.minimumSize())
        m=self.contentsMargins()
        return size+QSize(m.left()+m.right(),m.top()+m.bottom())
    def setGeometry(self,rect):
        super().setGeometry(rect)
        self._layout(rect,False)
    def _layout(self,rect,measure):
        m=self.contentsMargins()
        left=rect.x()+m.left();x=left;y=rect.y()+m.top();line_h=0
        right=rect.x()+rect.width()-m.right()
        for item in self._items:
            if item.widget() and not item.widget().isVisible() and not measure:continue
            width=item.sizeHint().width();height=item.sizeHint().height()
            if x>left and x+width>right:
                x=left;y+=line_h+self.spacing();line_h=0
            if not measure:item.setGeometry(QRect(QPoint(x,y),QSize(width,height)))
            x+=width+self.spacing();line_h=max(line_h,height)
        return y+line_h-rect.y()+m.bottom()


class InventoryJob(QThread):
    success=Signal(object)
    error=Signal(str)
    def __init__(self,action,call,parent=None):
        super().__init__(parent)
        self.action=action;self.call=call
    def run(self):
        try:self.success.emit(self.call())
        except Exception as exc:self.error.emit(str(exc)[:280])


class ProductDialog(QDialog):
    def __init__(self,product=None,parent=None,catalog_only=False):
        super().__init__(parent)
        self.catalog_only=catalog_only
        self.product=dict(product or {})
        self.image_bytes=None
        self.setWindowTitle('Ürün düzenle' if product else 'Yeni ürün oluştur')
        self.resize(640,710)
        self.setMinimumWidth(530)
        root=QVBoxLayout(self);root.setContentsMargins(22,18,22,17);root.setSpacing(10)
        root.addWidget(QLabel('Ürün kartı bilgileri'))
        area=QScrollArea();area.setWidgetResizable(True)
        host=QWidget();form=QFormLayout(host);form.setSpacing(13)
        self.sku=QLineEdit(self.product.get('sku',''));self.sku.setPlaceholderText('Örn. ALFA-001')
        self.title=QLineEdit(self.product.get('title',''));self.title.setPlaceholderText('Ürün adı')
        self.category=QLineEdit(self.product.get('category','Genel'))
        self.tags=QLineEdit(', '.join(self.product.get('tags') or []))
        self.tags.setPlaceholderText('etiket1, etiket2, etiket3')
        self.description=QTextEdit(self.product.get('description',''));self.description.setFixedHeight(87)
        self.description.setPlaceholderText('Ürünün açıklaması, kullanımı, içeriği...')
        attributes=self.product.get('attributes') or {}
        self.attributes=QTextEdit('\n'.join(f'{k}: {v}' for k,v in attributes.items()))
        self.attributes.setFixedHeight(74)
        self.attributes.setPlaceholderText('Marka: ALFA\nBoyut: A4\nRenk: Beyaz')
        self.quantity=QSpinBox();self.quantity.setRange(0,10000000);self.quantity.setValue(int(self.product.get('quantity') or 0))
        self.price=QDoubleSpinBox();self.price.setRange(0,999999999);self.price.setDecimals(2);self.price.setSuffix(' TL');self.price.setValue(float(self.product.get('sale_price') or 0))
        self.cost=QDoubleSpinBox();self.cost.setRange(0,999999999);self.cost.setDecimals(2);self.cost.setSuffix(' TL');self.cost.setValue(float(self.product.get('cost_price') or 0))
        self.preview=QLabel('Görsel seçilmedi');self.preview.setFixedSize(160,104)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.setObjectName('InventoryImagePreview')
        picture=QHBoxLayout();picture.addWidget(self.preview)
        choose=QPushButton('Görsel seç (JPG/PNG/WebP)');choose.clicked.connect(self.pick_image)
        picture.addWidget(choose);picture.addStretch()
        fields=[('Ürün kodu *',self.sku),('Ürün adı *',self.title),('Kategori',self.category),
            ('Etiketler',self.tags),('Açıklama',self.description),
            ('Özellikler (satır başına ad: değer)',self.attributes)]
        if not self.catalog_only:
            fields.append(('Envanterdeki adet',self.quantity))
        # Stok ve fiyat artık ürün ana kartından değil, alım/satım işlemlerinden girilir.
        for title,widget in fields:
            form.addRow(title,widget)
        form.addRow('Ürün görseli',picture)
        area.setWidget(host);root.addWidget(area,1)
        buttons=QHBoxLayout();cancel=QPushButton('Vazgeç');cancel.clicked.connect(self.reject)
        self.accept_button=QPushButton('Ürünü kaydet');self.accept_button.setObjectName('Accent');self.accept_button.clicked.connect(self.validate)
        buttons.addStretch();buttons.addWidget(cancel);buttons.addWidget(self.accept_button)
        root.addLayout(buttons)

    def pick_image(self):
        file,_=QFileDialog.getOpenFileName(self,'Ürün görseli seç',str(Path.home()),'Görseller (*.jpg *.jpeg *.png *.webp)')
        if not file:return
        pix=QPixmap(file)
        if pix.isNull():
            QMessageBox.warning(self,'Ürün görseli','Bu resim okunamadı.');return
        self.preview.setPixmap(pix.scaled(154,100,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        # Shrink large camera photos and send as high-quality JPEG; never ship
        # absolute local file paths to other workstations.
        image=pix.scaled(1000,1000,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation).toImage()
        buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer,'JPG',81)
        data=bytes(buffer.data())
        buffer.close()
        if len(data)>2900000:
            QMessageBox.warning(self,'Ürün görseli','Görsel 2.9 MB sınırını aştı.');return
        self.image_bytes=data

    def validate(self):
        if not self.sku.text().strip() or not self.title.text().strip():
            QMessageBox.warning(self,'Eksik alan','Ürün kodu ve adı zorunludur.');return
        self.accept()

    def value(self):
        attrs={}
        for line in self.attributes.toPlainText().splitlines():
            if ':' in line:
                key,val=line.split(':',1)
                if key.strip():attrs[key.strip()[:60]]=val.strip()[:400]
        return {'id':self.product.get('id'),'sku':self.sku.text().strip(),
            'title':self.title.text().strip(), 'category':self.category.text().strip() or 'Genel',
            'tags':[x.strip() for x in self.tags.text().split(',') if x.strip()][:15],
            'description':self.description.toPlainText().strip(), 'attributes':attrs,
            'quantity':self.quantity.value(),'sale_price':self.price.value(),
            'cost_price':self.cost.value(),'image_url':self.product.get('image_url',''),
            'in_inventory':bool(self.product.get('in_inventory',not self.catalog_only))}



def _date_label(value):
    if not value:return "Eski stok"
    try:
        return datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone().strftime("%d.%m.%Y %H:%M")
    except (ValueError,TypeError,OverflowError):
        return str(value)[:16]


class ProductCard(QFrame):
    """Compact product card with recent cost/date batches."""
    def __init__(self,product,sales,largeness,owner,on_sale,on_edit,on_details,on_cover):
        super().__init__()
        self.product=product;self.setObjectName('InventoryCard')
        width,height=((225,360),(267,395),(312,433))[largeness]
        self.setFixedSize(width,height)
        root=QVBoxLayout(self);root.setContentsMargins(12,12,12,12);root.setSpacing(5)
        top=QHBoxLayout()
        category=QLabel(str(product.get('category') or 'Genel')[:26])
        category.setObjectName('InventoryCategory');top.addWidget(category,1)
        stock=int(product.get('quantity') or 0)
        badge=QLabel(f'{stock} adet');badge.setObjectName('InventoryQty')
        top.addWidget(badge);root.addLayout(top)
        picture=QLabel('📦');picture.setObjectName('InventoryPicture')
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        picture.setFixedHeight({0:78,1:107,2:138}[largeness])
        root.addWidget(picture)
        if product.get('image_url'):on_cover(picture,str(product['image_url']))
        name=QLabel(str(product.get('title') or 'İsimsiz ürün'))
        name.setObjectName('InventoryName');name.setWordWrap(True)
        name.setMaximumHeight(45);root.addWidget(name)
        tags=', '.join(str(t) for t in (product.get('tags') or [])[:2])
        meta=QLabel((str(product.get('sku') or '')+(' · '+tags if tags else ''))[:85])
        meta.setObjectName('InventoryMeta')
        meta.setWordWrap(True);meta.setMaximumHeight(28);root.addWidget(meta)
        title=QLabel('ALIŞ PARTİLERİ · KALAN')
        title.setObjectName('InventoryLotHeading');root.addWidget(title)
        lots=sorted_batches(product)
        lines=[
            f"{_date_label(batch.get('received_at'))} · {int(batch.get('remaining') or 0)} ad · {float(batch.get('unit_cost') or 0):,.2f} TL"
            for batch in lots[:2]]
        if len(lots)>2:lines.append(f'+ {len(lots)-2} parti daha')
        compact=QLabel('\n'.join(lines) if lines else 'Henüz stok girişi yok')
        compact.setObjectName('InventoryLotList')
        compact.setWordWrap(True);compact.setFixedHeight(60)
        compact.setToolTip('\n'.join(
            f"{_date_label(b.get('received_at'))} · {int(b.get('remaining') or 0)} adet · {float(b.get('unit_cost') or 0):,.2f} TL"
            for b in lots))
        root.addWidget(compact);root.addStretch(1)
        price=QHBoxLayout()
        capital=QLabel(f"Stok maliyeti: {batch_stock_value(product):,.2f} TL")
        capital.setObjectName('InventoryPrice');price.addWidget(capital,1)
        if sales:price.addWidget(QLabel(f'{sales} satış'))
        root.addLayout(price)
        buttons=QHBoxLayout();buttons.setSpacing(5)
        detail=QPushButton('Partiler');detail.clicked.connect(lambda:on_details(product))
        buttons.addWidget(detail,1)
        sell=QPushButton('Satış')
        sell.setEnabled(stock>0 and bool(lots))
        sell.clicked.connect(lambda:on_sale(product));buttons.addWidget(sell,1)
        if owner:
            edit=QPushButton('Düzenle');edit.clicked.connect(lambda:on_edit(product))
            buttons.addWidget(edit,1)
        root.addLayout(buttons)


class SalesBars(QWidget):
    """Compact sales chart drawn with QPainter, no heavy chart dependencies."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setMinimumHeight(235)
        self.days=[]

    def set_data(self,days):
        self.days=days
        self.update()

    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        light=(QApplication.instance().property('alfa_theme')=='acik')
        high=(QApplication.instance().property('alfa_theme')=='kontrast')
        label=QColor('#192d41' if light else '#f5f7fb')
        bar=QColor('#d6a542' if high else '#338ab0' if light else '#68c6b2')
        rect=self.rect().adjusted(44,14,-19,-31)
        if rect.width()<50 or rect.height()<50:return
        mx=max([amount for _,amount in self.days]+[1.0])
        painter.setPen(QPen(label,1))
        painter.drawText(5,18,f'{mx:,.0f} TL')
        painter.drawText(8,rect.bottom(), '0')
        if not self.days:
            painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,'Henüz satış verisi bulunmuyor.')
            return
        width=rect.width()/len(self.days)
        painter.setPen(Qt.PenStyle.NoPen)
        for idx,(day,amount) in enumerate(self.days):
            h=(rect.height()-12)*(amount/mx)
            area=QRect(int(rect.left()+idx*width+max(1,width*.13)),int(rect.bottom()-h),
                       max(2,int(width*.73)),max(1,int(h)))
            painter.setBrush(bar)
            painter.drawRoundedRect(area,3,3)
        painter.setPen(label)
        for idx in (0,len(self.days)//2,len(self.days)-1):
            day=self.days[idx][0]
            painter.drawText(int(rect.left()+idx*width),rect.bottom()+17,day[5:])
        painter.end()


class EnvanterView(QWidget):
    def __init__(self,db,parent=None):
        super().__init__(parent)
        self.db=db;self.jobs=set();self.last_signature=None;self._busy_sales=set()
        self.network=QNetworkAccessManager(self)
        self.image_cache={};self.pending_images={}
        self.setObjectName('InventoryRoot')
        main=QVBoxLayout(self);main.setContentsMargins(15,12,15,12);main.setSpacing(11)
        title=QHBoxLayout()
        heading=QLabel('Ürünler & Envanter');heading.setObjectName('PageTitle');title.addWidget(heading)
        title.addStretch()
        self.sync_note=QLabel('Firebase · ortak envanter');self.sync_note.setObjectName('Muted')
        title.addWidget(self.sync_note)
        self.add_button=QPushButton('＋  Alım partisi ekle');self.add_button.setObjectName('Accent')
        self.add_button.clicked.connect(self.add_from_catalog);title.addWidget(self.add_button)
        main.addLayout(title)
        self.summary=QLabel('Ürünler yükleniyor…')
        self.summary.setWordWrap(True);self.summary.setObjectName('InventorySummary')
        main.addWidget(self.summary)
        toolbar=QHBoxLayout();toolbar.setSpacing(9)
        self.search=QLineEdit();self.search.setPlaceholderText('Ürün adı, kodu veya etikette ara…')
        self.search.textChanged.connect(self.render)
        toolbar.addWidget(self.search,3)
        self.category=QComboBox();self.category.addItem('Tüm kategoriler')
        self.category.currentIndexChanged.connect(self.render)
        toolbar.addWidget(self.category,1)
        self.scope=QComboBox();self.scope.addItems(['Tüm envanter','Stokta bulunanlar','Satışı yapılanlar'])
        self.scope.currentIndexChanged.connect(self.render)
        toolbar.addWidget(self.scope,1)
        self.sort=QComboBox();self.sort.addItems(['Mozaik: popüler ürünler','Ürün adı','Stok miktarı','Satış tutarı'])
        self.sort.currentIndexChanged.connect(self.render)
        toolbar.addWidget(self.sort,1)
        main.addLayout(toolbar)
        view_buttons=QHBoxLayout()
        self.catalog_button=QPushButton('▦  Ürün mozaği');self.catalog_button.setCheckable(True)
        self.catalog_button.setChecked(True)
        self.analysis_button=QPushButton('▥  Satış analitiği');self.analysis_button.setCheckable(True)
        self.catalog_button.clicked.connect(lambda:self.select_view(0))
        self.analysis_button.clicked.connect(lambda:self.select_view(1))
        view_buttons.addWidget(self.catalog_button);view_buttons.addWidget(self.analysis_button)
        view_buttons.addStretch()
        main.addLayout(view_buttons)
        self.views=QStackedWidget()
        self.area=QScrollArea();self.area.setWidgetResizable(True)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stage=QWidget();self.flow=MosaicLayout(self.stage,spacing=13)
        self.area.setWidget(self.stage)
        self.views.addWidget(self.area)
        analysis_scroll=QScrollArea();analysis_scroll.setWidgetResizable(True)
        summary_host=QWidget();sales_layout=QVBoxLayout(summary_host)
        sales_layout.setContentsMargins(16,14,16,18);sales_layout.setSpacing(17)
        intro=QLabel('Son 30 gün · Günlük satış cirosu')
        intro.setObjectName('PageTitle');sales_layout.addWidget(intro)
        self.bars=SalesBars();sales_layout.addWidget(self.bars)
        self.sales_stats=QLabel('Satışlar yükleniyor…')
        self.sales_stats.setObjectName('InventorySummary');self.sales_stats.setWordWrap(True)
        sales_layout.addWidget(self.sales_stats)
        detail_title=QLabel('Çok satan ürünler');detail_title.setObjectName('PageTitle')
        sales_layout.addWidget(detail_title)
        self.top_products=QVBoxLayout();self.top_products.setSpacing(9)
        sales_layout.addLayout(self.top_products)
        row=QHBoxLayout()
        history_title=QLabel('SATIŞ GEÇMİŞİ · ALIŞ MALİYETİ VE KÂR')
        history_title.setObjectName('PageTitle')
        row.addWidget(history_title,1)
        self.history_period=QComboBox()
        for name,days in (('Tüm zamanlar',0),('Son 7 gün',7),
                          ('Son 30 gün',30),('Son 90 gün',90),('Son 365 gün',365)):
            self.history_period.addItem(name,days)
        row.addWidget(self.history_period)
        self.cancel_sale_button=QPushButton('↶ Seçili satışı iptal et')
        self.cancel_sale_button.setObjectName('Danger')
        self.cancel_sale_button.setEnabled(False)
        self.cancel_sale_button.setVisible(self.owner)
        self.cancel_sale_button.clicked.connect(self.cancel_selected_sale)
        row.addWidget(self.cancel_sale_button)
        sales_layout.addLayout(row)
        self.history_count=QLabel('')
        self.history_count.setObjectName('InventoryHistoryCount')
        self.history_count.setWordWrap(True)
        sales_layout.addWidget(self.history_count)
        self._history_display=[]
        self.history_table=QTableWidget(0,9)
        self.history_table.setObjectName('InventoryHistoryTable')
        self.history_table.setHorizontalHeaderLabels([
            'Satış tarihi','Ürün','Alım / parti',
            'Adet','Alış/adet','Satış/adet','Ciro','Brüt fark','Durum'])
        self.history_table.verticalHeader().hide()
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_table.itemSelectionChanged.connect(self._sale_selection_changed)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setShowGrid(False)
        self.history_table.setMinimumHeight(350)
        head=self.history_table.horizontalHeader()
        head.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        sales_layout.addWidget(self.history_table,1)
        self.history_period.currentIndexChanged.connect(
            lambda *_:self.update_analytics(
                [p for p in self.db.inventory_products
                 if p.get('in_inventory',True)],
                self.db.inventory_sales))
        sales_layout.addStretch()
        analysis_scroll.setWidget(summary_host)
        self.views.addWidget(analysis_scroll)
        main.addWidget(self.views,1)
        self.apply_theme();self.refresh()

    def select_view(self,index):
        self.views.setCurrentIndex(index)
        self.catalog_button.setChecked(index==0)
        self.analysis_button.setChecked(index==1)

    @property
    def owner(self):
        # The owner build has the manager feature; only a live admin session
        # can authorize writes to the catalog via Supabase.
        return (Path(__file__).resolve().parent/'YONETICI_SURUMU.flag').exists()

    def _admin_request(self):
        return getattr(self.db,'owner_admin_request',None)

    def _parent_sync(self):
        parent=self.window()
        live=getattr(parent,'live',None)
        if live:
            live.force_pull=True
            QTimer.singleShot(250,live.pull)

    def _run_job(self,action,fn,success,on_error=None):
        # Hold the QThread through finished(), not merely its first signal.
        # Worker callables must capture plain values; never modal Qt controls.
        job=InventoryJob(action,fn,self)
        self.jobs.add(job)
        def done(result):
            success(result)
        def failed(message):
            if on_error:on_error(message)
            QMessageBox.warning(self,'Envanter',message)
        def cleanup():
            self.jobs.discard(job)
        job.success.connect(done);job.error.connect(failed)
        job.finished.connect(cleanup)
        job.finished.connect(job.deleteLater)
        job.start()

    def show_details(self,product):
        """All purchase lots, including exhausted ones, visible in one product."""
        dialog=QDialog(self)
        dialog.setWindowTitle('Ürün ve alım partileri · '+str(product.get('title') or 'Ürün'))
        dialog.resize(740,610)
        layout=QVBoxLayout(dialog)
        heading=QLabel(str(product.get('title') or 'Ürün'))
        heading.setObjectName('PageTitle');heading.setWordWrap(True)
        layout.addWidget(heading)
        subtitle=QLabel(
            f"Kod: {product.get('sku','')} · {product.get('category','Genel')}  |  "
            f"Stok: {int(product.get('quantity') or 0)} adet  |  "
            f"Alış sermayesi: {batch_stock_value(product):,.2f} TL")
        subtitle.setWordWrap(True);layout.addWidget(subtitle)
        layout.addWidget(QLabel('ALIŞ TARİHİ / MALİYETİ / KALAN PARTİLER'))
        lots=sorted_batches(product,include_empty=True)
        table=QTableWidget(len(lots),6)
        table.setHorizontalHeaderLabels(['Alış tarihi ve saati','İlk adet','Kalan',
                                         'Alış / adet','Kalan maliyet','Durum'])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for i,lot in enumerate(lots):
            values=[_date_label(lot.get('received_at')),
                    str(int(lot.get('quantity') or 0)),
                    str(int(lot.get('remaining') or 0)),
                    f"{float(lot.get('unit_cost') or 0):,.2f} TL",
                    f"{int(lot.get('remaining') or 0)*float(lot.get('unit_cost') or 0):,.2f} TL",
                    "İptal edildi" if lot.get('voided_at') else
                    "Kullanılmadı" if int(lot.get('remaining') or 0)==int(lot.get('quantity') or 0)
                    else "Kısmen/tamamen kullanıldı"]
            for j,value in enumerate(values):
                item=QTableWidgetItem(value)
                if j==0:
                    item.setData(Qt.ItemDataRole.UserRole,str(lot.get('id') or ''))
                table.setItem(i,j,item)
        layout.addWidget(table,1)
        info=QTextEdit();info.setReadOnly(True);info.setMaximumHeight(110)
        attrs=product.get('attributes') or {}
        details=str(product.get('description') or '')
        if attrs:
            details+='\n\nÖZELLİKLER\n'+'\n'.join(
                f'{key}: {value}' for key,value in attrs.items())
        info.setPlainText(details or 'Ürün açıklaması yok.')
        layout.addWidget(info)
        actions=QHBoxLayout()
        void=QPushButton('↶ Seçili yanlış alımı geri al')
        void.setToolTip('Yalnız hiç kullanılmamış ve satışa bağlanmamış gerçek alım partileri geri alınabilir.')
        void.setVisible(self.owner)
        void.setEnabled(False)
        def selected_lot():
            index=table.currentRow()
            return lots[index] if 0<=index<len(lots) else None
        def selection_changed():
            lot=selected_lot()
            history=(product.get('sales_history') or {}).values()
            used=any(isinstance(x,dict) and
                     str(x.get('batch_id'))==str((lot or {}).get('id')) for x in history)
            void.setEnabled(bool(self.owner and lot and not used and
                not lot.get('legacy') and not lot.get('voided_at') and
                int(lot.get('quantity') or 0)>0 and
                int(lot.get('remaining') or 0)==int(lot.get('quantity') or 0)))
        table.itemSelectionChanged.connect(selection_changed)
        def reverse_selected():
            lot=selected_lot()
            if not lot:return
            bid=str(lot.get('id') or '')
            pid=str(product.get('id') or '')
            reason,ok=QInputDialog.getText(dialog,'Yanlış alım partisi',
                f"{int(lot.get('quantity') or 0)} adetlik kullanılmamış alış geri alınacak.\n"
                "Stoktan çıkarılır, tarih/maliyet kaydı silinmez.\nGerekçe:")
            if not ok or not reason.strip():return
            if QMessageBox.question(dialog,'Alımı geri al',
                'Bu alım partisi stoktan düşülecek, işlemin kaydı korunacak. Onaylıyor musun?',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
                )!=QMessageBox.StandardButton.Yes:return
            dialog.accept()
            self._run_job('inventory_void_acquisition',
                lambda:self._admin_request()('admin_inventory_void_acquisition',
                    product_id=pid,batch_id=bid,reason=reason.strip()),
                lambda _:(self.sync_note.setText('Yanlış alım geri alındı · stok eşitleniyor'),
                           self._parent_sync()))
        void.clicked.connect(reverse_selected)
        actions.addWidget(void)
        remove=QPushButton('Envanterden çıkar')
        remove.setToolTip('Stok sıfırsa ürünü envanterden gizler. Genel katalog ve geçmiş korunur.')
        remove.setVisible(self.owner)
        remove.setEnabled(int(product.get('quantity') or 0)==0 and self.owner)
        def remove_inventory():
            pid=str(product.get('id') or '')
            if QMessageBox.question(dialog,'Envanterden çıkar',
                'Stok sıfır. Ürün envanter ekranından kaldırılacak; '
                'Genel Ürünler kartı, alım ve satış geçmişi korunacak. Devam edilsin mi?',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
                )!=QMessageBox.StandardButton.Yes:return
            dialog.accept()
            self._run_job('inventory_remove',
                lambda:self._admin_request()('admin_inventory_remove',product_id=pid),
                lambda _:(self.sync_note.setText('Ürün envanterden çıkarıldı'),
                           self._parent_sync()))
        remove.clicked.connect(remove_inventory)
        actions.addWidget(remove)
        archive=QPushButton('Katalogdan arşivle')
        archive.setToolTip('Ürünü iki listeden gizler; stok, alışlar ve satış geçmişi korunur. '
                           'Genel Ürünler → Arşivlenenleri göster ile geri alınabilir.')
        archive.setVisible(self.owner)
        def archive_product():
            pid=str(product.get('id') or '')
            count=int(product.get('quantity') or 0)
            warning=(f"Bu üründe {count} adet stok kaydı bulunuyor.\n"
                     "Arşivleme stoğu silmez veya düşmez.\n\n"
                     "Ürün aktif listelerden gizlenecek; Genel Ürünler → "
                     "Arşivlenenleri göster ile tekrar açılabilir. Devam edilsin mi?")
            if QMessageBox.question(dialog,'Ürünü arşivle',warning,
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
                    )!=QMessageBox.StandardButton.Yes:return
            dialog.accept()
            self._run_job('inventory_archive',
                lambda:self._admin_request()('admin_inventory_archive',
                                              product_id=pid,active=False),
                lambda _:(self.sync_note.setText('Ürün arşivlendi · geçmiş korundu'),
                           self._parent_sync()))
        archive.clicked.connect(archive_product)
        actions.addWidget(archive)
        actions.addStretch()
        dismiss=QPushButton('Kapat');dismiss.clicked.connect(dialog.accept)
        actions.addWidget(dismiss)
        layout.addLayout(actions)
        dialog.exec()

    def add_from_catalog(self):
        """Add an immutable-cost stock acquisition, not overwrite total stock."""
        if not self.owner:return
        request=self._admin_request()
        if not callable(request):
            QMessageBox.warning(self,'Envanter','Yönetici bağlantısı bulunamadı.');return
        products=sorted((p for p in self.db.inventory_products if p.get('active',True)),
                        key=lambda p:str(p.get('title') or '').casefold())
        if not products:
            QMessageBox.information(self,'Envanter',
                'Önce Envanter → Genel Ürünler sekmesinde ürün kartı oluştur.')
            return
        dialog=QDialog(self);dialog.setWindowTitle('Yeni stok alımı · Fiyat partisi')
        dialog.setObjectName('InventoryAcquireDialog')
        dialog.resize(685,350)
        palette={
            'acik':('#fffaf3','#243a51','#d7c7b2','#dcebf3','#255572'),
            'koyu':('#101d2d','#f3f8fe','#536f8e','#254966','#f3f8fe'),
            'kontrast':('#080d13','#ffffff','#9cb9d6','#294b6b','#ffffff')}
        bg,fg,edge,stepbg,stepfg=palette.get(
            str(QApplication.instance().property('alfa_theme') or 'koyu'),
            palette['koyu'])
        dialog.setStyleSheet(f"""
            QDialog#InventoryAcquireDialog {{background:{bg};color:{fg};}}
            QDialog#InventoryAcquireDialog QLabel {{color:{fg};background:transparent;}}
            QDialog#InventoryAcquireDialog QSpinBox,
            QDialog#InventoryAcquireDialog QDoubleSpinBox,
            QDialog#InventoryAcquireDialog QComboBox {{
                color:{fg};background:{bg};border:1px solid {edge};
                border-radius:7px;min-height:35px;padding:3px 10px;
            }}
            QDialog#InventoryAcquireDialog QToolButton#InventoryStep {{
                color:{stepfg};background:{stepbg};border:1px solid {edge};
                border-radius:7px;font-size:20px;font-weight:850;
            }}
            QDialog#InventoryAcquireDialog QToolButton#InventoryStep:hover {{
                border:2px solid {fg};
            }}
            QDialog#InventoryAcquireDialog QToolButton#InventoryStep:disabled {{
                color:{edge};background:{bg};
            }}
        """)
        layout=QVBoxLayout(dialog)
        intro=QLabel('Her alış ayrı tarih, saat ve birim maliyetle saklanır. '
            'Önceki stok partilerinin maliyeti ve kalan adedi değişmez.')
        intro.setWordWrap(True);layout.addWidget(intro)
        form=QFormLayout()
        choice=QComboBox();choice.setEditable(True)
        for item in products:
            choice.addItem(f"{item.get('sku','')} · {item.get('title','')}",str(item.get('id')))
        choice.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer=choice.completer()
        if completer is not None:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        quantity=QSpinBox();quantity.setRange(1,100000)
        quantity.setValue(1)
        unit_cost=QDoubleSpinBox();unit_cost.setRange(0,999999999)
        unit_cost.setDecimals(2);unit_cost.setSuffix(' TL')
        unit_cost.setSingleStep(1.0)
        # Native Windows up/down arrows were invisible and offset by the
        # inherited global QSS. Explicit high-contrast stepper pills avoid
        # OS-specific subcontrol positions in every theme.
        def stepper(spin):
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setMinimumWidth(190)
            host=QWidget()
            bar=QHBoxLayout(host)
            bar.setContentsMargins(0,0,0,0);bar.setSpacing(7)
            bar.addWidget(spin,1)
            for sign,fn in (('−',spin.stepDown),('+',spin.stepUp)):
                btn=QToolButton()
                btn.setObjectName('InventoryStep')
                btn.setText(sign)
                btn.setFixedSize(39,39)
                btn.setAccessibleName('Bir azalt' if sign=='−' else 'Bir artır')
                btn.clicked.connect(fn)
                bar.addWidget(btn)
            return host
        quantity_controls=stepper(quantity)
        cost_controls=stepper(unit_cost)
        summary=QLabel('');summary.setWordWrap(True)
        def selected(index):
            if 0<=index<len(products):
                current=products[index]
                summary.setText(
                    f"Şu anda {int(current.get('quantity') or 0)} adet mevcut. "
                    f"{len(sorted_batches(current))} farklı açık alış partisi var.")
                unit_cost.setValue(float(current.get('cost_price') or 0))
        choice.currentIndexChanged.connect(selected)
        form.addRow('Genel katalog ürünü',choice)
        form.addRow('Yeni alınan adet',quantity_controls)
        form.addRow('Bu alışın birim maliyeti',cost_controls)
        form.addRow('Alım tarihi',QLabel('Kaydettiğiniz anın tarih ve saati'))
        layout.addLayout(form);layout.addWidget(summary)
        actions=QHBoxLayout();actions.addStretch()
        cancel=QPushButton('Vazgeç');cancel.clicked.connect(dialog.reject)
        save=QPushButton('Alım partisini kaydet');save.setObjectName('Accent')
        save.clicked.connect(dialog.accept)
        actions.addWidget(cancel);actions.addWidget(save);layout.addLayout(actions)
        selected(0)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        index=choice.currentIndex()
        if (not 0<=index<len(products) or
            choice.currentText().strip()!=choice.itemText(index).strip()):
            QMessageBox.warning(self,'Envanter','Lütfen listeden geçerli bir ürün seç.')
            return
        # This is the QSpinBox-deleted fix: capture everything before dialog
        # controls can be garbage-collected when this function returns.
        product_id=str(products[index]['id'])
        amount=int(quantity.value())
        purchase_price=float(unit_cost.value())
        self.sync_note.setText('Yeni alış partisi Firebase’e kaydediliyor…')
        def success(_result):
            self.sync_note.setText('Alım kaydedildi · ortak stok yenileniyor')
            self._parent_sync()
        self._run_job('inventory_acquire',
            lambda:request('admin_inventory_acquire',product_id=product_id,
                           quantity=amount,unit_cost=purchase_price),
            success)

    def edit_product(self,product):
        if not self.owner:
            return
        request=self._admin_request()
        if request is None:
            QMessageBox.information(self,'Yönetim girişi',
                'Ürün kataloğunu düzenlemek için üstteki Yönetim düğmesine basıp yönetici girişi yapın.\n'
                'Sonra bu sekmeye dönerek ürün ekleyebilirsiniz.')
            return
        editor=ProductDialog(product,self,catalog_only=True)
        if editor.exec()!=QDialog.DialogCode.Accepted:return
        payload=editor.value();image=editor.image_bytes
        self.sync_note.setText('Ürün buluta gönderiliyor…')
        def task():
            if image:
                result=request('admin_inventory_image',mime='image/jpeg',
                    image_base64=base64.b64encode(image).decode('ascii'))
                payload['image_url']=result['url']
            return request('admin_inventory_upsert',product=payload)
        def success(_):
            self.sync_note.setText('Ürün kaydedildi · eşitleniyor')
            self._parent_sync()
        self._run_job('save',task,success)

    def sale(self,product):
        """Sale UI chooses purchase lot first, then requests selling price."""
        pid=str(product.get('id') or '')
        if pid in self._busy_sales:return
        lots=sorted_batches(product,newest_first=False)
        if not lots:
            QMessageBox.information(self,'Envanter','Satılabilir stok partisi bulunmuyor.')
            return
        dialog=QDialog(self)
        dialog.setWindowTitle('Satış · Alım partisini ve satış fiyatını seç')
        dialog.resize(680,400)
        theme=str(QApplication.instance().property('alfa_theme') or 'koyu')
        if theme=='acik':
            bg,card,fg,border='#f6f1e8','#fffaf2','#243a51','#cbbca5'
        elif theme=='kontrast':
            bg,card,fg,border='#060b11','#172638','#ffffff','#85a9ce'
        else:
            bg,card,fg,border='#102033','#1b3045','#eef4fb','#527395'
        dialog.setStyleSheet(f"""
            QDialog {{background:{bg};color:{fg};}}
            QFrame#InventorySaleCard {{background:{card};border:1px solid {border};
                border-radius:12px;}}
            QLabel#InventorySalePill {{background:{card};color:{fg};
                border:1px solid {border};border-radius:8px;padding:9px;font-weight:700;}}
            QLabel#PageTitle, QLabel {{color:{fg};}}
            QComboBox,QSpinBox,QDoubleSpinBox {{background:{card};color:{fg};
                border:1px solid {border};padding:7px;border-radius:6px;}}
        """)
        layout=QVBoxLayout(dialog);layout.setSpacing(12)
        heading=QLabel(str(product.get('title') or 'Ürün'))
        heading.setObjectName('PageTitle');layout.addWidget(heading)
        note=QLabel('Hangi alıştan satıldığını seç; satış fiyatını satışı '
                    'kaydederken gir. Alış maliyeti değişmeden saklanır.')
        note.setWordWrap(True);layout.addWidget(note)
        picker=QComboBox()
        for batch in lots:
            picker.addItem(
                f"{_date_label(batch.get('received_at'))} · "
                f"{int(batch.get('remaining') or 0)} adet · "
                f"Alış {float(batch.get('unit_cost') or 0):,.2f} TL",
                str(batch.get('id')))
        quantity=QSpinBox()
        quantity.setRange(1,max(1,int(lots[0].get('remaining') or 1)))
        selling=QDoubleSpinBox();selling.setRange(0,999999999)
        selling.setDecimals(2);selling.setSuffix(' TL')
        selling.setValue(float(product.get('sale_price') or 0))
        estimate=QLabel('')
        estimate.setObjectName('InventoryLotList')
        def preview(*_):
            idx=picker.currentIndex()
            if idx<0:return
            batch=lots[idx]
            quantity.setMaximum(max(1,int(batch.get('remaining') or 0)))
            unit_cost=float(batch.get('unit_cost') or 0)
            gain=int(quantity.value())*(float(selling.value())-unit_cost)
            estimate.setText(
                f"Alış: {unit_cost:,.2f} TL/adet · "
                f"Bu satışın tahmini brüt farkı: {gain:,.2f} TL")
        picker.currentIndexChanged.connect(preview)
        quantity.valueChanged.connect(preview)
        selling.valueChanged.connect(preview)
        # A clear sale form split into pill-like summary and input groups.
        pills=QHBoxLayout()
        stock_pill=QLabel(f"📦 Stok  {int(product.get('quantity') or 0)} adet")
        stock_pill.setObjectName('InventorySalePill')
        lots_pill=QLabel(f"◈ {len(lots)} alım partisi")
        lots_pill.setObjectName('InventorySalePill')
        detail_pill=QLabel('✓ Firebase kayıtlı satış')
        detail_pill.setObjectName('InventorySalePill')
        for pill in (stock_pill,lots_pill,detail_pill):pills.addWidget(pill,1)
        layout.addLayout(pills)
        card=QFrame();card.setObjectName('InventorySaleCard')
        form=QFormLayout(card)
        form.setContentsMargins(16,14,16,14);form.setSpacing(12)
        form.addRow('Alım partisi',picker)
        form.addRow('Satış adedi',quantity)
        form.addRow('Birim satış fiyatı',selling)
        layout.addWidget(card);layout.addWidget(estimate)
        actions=QHBoxLayout();actions.addStretch()
        cancel=QPushButton('Vazgeç');cancel.clicked.connect(dialog.reject)
        submit=QPushButton('Satışı kaydet');submit.setObjectName('Accent')
        submit.clicked.connect(dialog.accept)
        actions.addWidget(cancel);actions.addWidget(submit);layout.addLayout(actions)
        preview()
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        device=getattr(self.window(),'device',None)
        if device is None or not device.paired:
            QMessageBox.warning(self,'Bulut','Bu cihaz buluta bağlı değil.')
            return
        # Capture primitive values BEFORE the modal QSpinBox is destroyed.
        lot_id=str(picker.currentData())
        sold=int(quantity.value())
        unit_price=float(selling.value())
        self._busy_sales.add(pid)
        self.sync_note.setText('Satış Firebase’e kaydediliyor…')
        def success(_):
            self._busy_sales.discard(pid)
            self.sync_note.setText('Satış kaydedildi · eşitleniyor')
            self._parent_sync()
        def failed(_):
            self._busy_sales.discard(pid)
            self.sync_note.setText('Satış kaydedilemedi · yeniden kontrol et')
        self._run_job('sale',
            lambda:device.inventory_sale(pid,sold,unit_price,lot_id),
            success,failed)

    def _picture(self,label,url):
        if url in self.image_cache:
            self._apply_picture(label,self.image_cache[url]);return
        if url in self.pending_images:
            self.pending_images[url].append(label);return
        self.pending_images[url]=[label]
        req=QNetworkRequest(QUrl(url))
        reply=self.network.get(req)
        def finished():
            pix=QPixmap()
            if reply.error()==reply.NetworkError.NoError:
                data=bytes(reply.readAll())
                if len(data)<3500000:pix.loadFromData(data)
            if not pix.isNull():self.image_cache[url]=pix
            for target in self.pending_images.pop(url,[]):
                try:
                    if not pix.isNull():self._apply_picture(target,pix)
                except RuntimeError:pass
            reply.deleteLater()
        reply.finished.connect(finished)

    @staticmethod
    def _apply_picture(label,pix):
        label.setText('')
        label.setPixmap(pix.scaled(max(80,label.width()-10),max(70,label.height()-10),
            Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

    def apply_theme(self):
        theme=QApplication.instance().property('alfa_theme') or 'koyu'
        if theme=='acik':
            colors=('white','#f1f5f9','#d4e0eb','#1b344d','#4a6478','#18739d','#f0fafc')
        elif theme=='kontrast':
            colors=('#101010','#181818','#f3f3f3','#ffffff','#f3f3f3','#ffe07b','#191919')
        else:
            colors=('#14263d','#1a3553','#4c739b','#f4f8ff','#b9cee4','#34d2b4','#214966')
        surface,pic,border,text,muted,accent,tag=colors
        self.setStyleSheet(f'''
            QFrame#InventoryCard {{background:{surface};border:1px solid {border};border-radius:17px;}}
            QFrame#InventoryCard:hover {{border:2px solid {accent};}}
            QLabel#InventoryPicture {{background:{pic};color:{accent};border-radius:12px;font-size:28px;}}
            QLabel#InventoryName {{color:{text};font-weight:750;font-size:14px;}}
            QLabel#InventoryPrice {{color:{accent};font-weight:800;font-size:15px;}}
            QLabel#InventoryQty,QLabel#InventoryCategory {{color:{text};font-size:11px;}}
            QLabel#InventoryMeta {{color:{muted};font-size:11px;}}
            QLabel#InventorySummary {{color:{text};background:{surface};border:1px solid {border};
                border-radius:13px;padding:15px;font-size:13px;}}
            QLabel#InventoryImagePreview {{background:{pic};border:1px dashed {border};border-radius:9px;}}
            QLabel#InventoryLotHeading {{color:{accent};font-size:10px;font-weight:900;}}
            QLabel#InventoryLotList {{background:{pic};color:{text};font-size:10px;
                border:1px solid {border};border-radius:7px;padding:4px;}}
            QTableWidget#InventoryHistoryTable {{background:{surface};color:{text};
                alternate-background-color:{pic};border:1px solid {border};}}
            QLabel#InventoryHistoryCount {{color:{muted};font-weight:700;}}
        ''')

    def refresh(self):
        rows=getattr(self.db,'inventory_products',[]) or []
        sales=getattr(self.db,'inventory_sales',[]) or []
        counts=defaultdict(int);money=0.0;cost=0.0
        for sale in sales:
            if sale.get('cancelled_at'):continue
            n=int(sale.get('quantity') or 0)
            counts[str(sale.get('product_id'))]+=n
            money+=n*float(sale.get('sale_price') or 0)
            cost+=n*float(sale.get('cost_price') or 0)
        self.sales_counts=dict(counts)
        self.sales_amounts=defaultdict(float)
        for sale in sales:
            if sale.get('cancelled_at'):continue
            self.sales_amounts[str(sale.get('product_id'))]+=int(sale.get('quantity') or 0)*float(sale.get('sale_price') or 0)
        active=[p for p in rows if p.get('active',True) and p.get('in_inventory',True)]
        self.summary.setText(f'   {len(active)} ürün     ·     {sum(int(p.get("quantity") or 0) for p in active):,} mevcut adet'
                             f'     ·     {sum(counts.values()):,} satış     ·     {money:,.2f} TL satış cirosu'
                             f'     ·     {money-cost:,.2f} TL tahmini brüt fark')
        self.add_button.setVisible(self.owner)
        cats=['Tüm kategoriler']+sorted({str(p.get('category') or 'Genel') for p in active})
        selected=self.category.currentText()
        self.category.blockSignals(True);self.category.clear();self.category.addItems(cats)
        if selected in cats:self.category.setCurrentText(selected)
        self.category.blockSignals(False)
        self.apply_theme()
        self.render()
        # Archived products remain in stock and historical reports; only the
        # active sales catalogue hides them.
        # Removed/archived stock cards must not erase old sales from reports.
        # Capital remains derived from each lot's remaining quantity.
        self.update_analytics(rows,sales)

    def update_analytics(self,products,sales):
        """Inventory-only reporting from synced ledger; no additional reads."""
        today=date.today();start=today-timedelta(days=29)
        days={start+timedelta(days=i):0.0 for i in range(30)}
        # Imported legacy entries may overlap nested per-product sales_history.
        unique={}
        for index,row in enumerate(sales):
            if isinstance(row,dict):
                unique[str(row.get('id') or ('legacy-'+str(index)))]=row
        rows=list(unique.values())
        window=int(self.history_period.currentData() or 0)
        cutoff=today-timedelta(days=window-1) if window else None
        filtered=[]
        history_filtered=[]
        for record in rows:
            try:day=date.fromisoformat(str(record.get('created_at') or '')[:10])
            except (ValueError,TypeError):day=None
            amount=int(record.get('quantity') or 0)*float(record.get('sale_price') or 0)
            if cutoff is None or (day is not None and day>=cutoff):
                history_filtered.append(record)
                if not record.get('cancelled_at'):
                    filtered.append(record)
            if day in days and not record.get('cancelled_at'):
                days[day]+=amount
        self.bars.set_data([(day.isoformat(),amount) for day,amount in days.items()])
        units=sum(int(row.get('quantity') or 0) for row in filtered)
        revenue=sum(int(row.get('quantity') or 0)*float(row.get('sale_price') or 0)
                    for row in filtered)
        costs=sum(int(row.get('quantity') or 0)*float(row.get('cost_price') or 0)
                  for row in filtered)
        gain=revenue-costs
        margin=gain/revenue*100 if revenue else 0.0
        capital=sum(batch_stock_value(p) for p in products)
        self.sales_stats.setText(
            f'{len(filtered):,} satış işlemi  ·  {units:,} adet  ·  '
            f'Ciro: {revenue:,.2f} TL  ·  Alış maliyeti: {costs:,.2f} TL\n'
            f'Brüt fark: {gain:,.2f} TL (%{margin:.1f})  ·  '
            f'Mevcut stok sermayesi: {capital:,.2f} TL  ·  '
            f'Ürün çeşidi: {len(products):,}')
        counts=defaultdict(int)
        for row in filtered:
            counts[str(row.get('product_id') or '')]+=int(row.get('quantity') or 0)
        while self.top_products.count():
            entry=self.top_products.takeAt(0)
            if entry.widget():entry.widget().deleteLater()
        product_map={str(p.get('id')):p for p in products}
        ranking=sorted(counts.items(),key=lambda row:-row[1])[:9]
        if not ranking:
            self.top_products.addWidget(QLabel('Bu dönemde satış bulunmuyor.'))
        else:
            maximum=max(counts.values())
            for product_id,amount in ranking:
                product=product_map.get(product_id)
                label=str(product.get('title') or product_id[:12]) if product else product_id[:12]
                line=QHBoxLayout()
                name=QLabel(label);name.setMinimumWidth(180)
                name.setMaximumWidth(300);line.addWidget(name)
                bar=QProgressBar();bar.setRange(0,maximum);bar.setValue(amount)
                bar.setFormat(f'{amount} adet');line.addWidget(bar,1)
                wrapper=QWidget();wrapper.setLayout(line)
                self.top_products.addWidget(wrapper)
        history_filtered.sort(key=lambda row:str(row.get('created_at') or ''),reverse=True)
        shown=history_filtered[:250]
        self._history_display=shown
        self.history_count.setText(
            f'{len(filtered):,} geçerli satış · '
            f'{len(history_filtered)-len(filtered):,} iptal · '
            f'{len(shown)} satır gösteriliyor. '
            'İptaller stok partisine iade edilir ve geçmişte görünür.')
        self.history_table.setRowCount(len(shown))
        for i,record in enumerate(shown):
            pid=str(record.get('product_id') or '')
            p=product_map.get(pid)
            name=str(p.get('title') or p.get('sku') or pid[:12]) if p else pid[:12]
            quantity=int(record.get('quantity') or 0)
            bought=float(record.get('cost_price') or 0)
            sold=float(record.get('sale_price') or 0)
            revenue_row=quantity*sold
            gain_row=quantity*(sold-bought)
            batch_id=str(record.get('batch_id') or '')
            batch_text=_date_label(record.get('purchase_at'))
            if batch_id:batch_text+=' · '+batch_id[:8]
            cancelled=bool(record.get('cancelled_at'))
            values=(
                _date_label(record.get('created_at')),name,batch_text,
                str(quantity),f'{bought:,.2f} TL',
                f'{sold:,.2f} TL',f'{revenue_row:,.2f} TL',
                f'{gain_row:+,.2f} TL',
                'İPTAL · '+_date_label(record.get('cancelled_at')) if cancelled else 'Geçerli')
            for column,value in enumerate(values):
                cell=QTableWidgetItem(value)
                if column==7 and not cancelled:
                    cell.setForeground(QColor('#17805c' if gain_row>=0 else '#b44255'))
                if cancelled:
                    cell.setForeground(QColor('#9a7780'))
                self.history_table.setItem(i,column,cell)
        self._sale_selection_changed()

    def _sale_selection_changed(self):
        index=self.history_table.currentRow()
        item=(self._history_display[index] if
              0<=index<len(self._history_display) else None)
        product=next((p for p in (self.db.inventory_products or [])
                      if item and str(p.get('id'))==str(item.get('product_id'))),None)
        recorded=((product.get('sales_history') or {}).get(str(item.get('id')))
                  if isinstance(product,dict) and item else None)
        self.cancel_sale_button.setEnabled(bool(
            self.owner and item and recorded and
            not item.get('cancelled_at')))

    def cancel_selected_sale(self):
        index=self.history_table.currentRow()
        if not (0<=index<len(self._history_display)):return
        sale=self._history_display[index]
        if sale.get('cancelled_at'):return
        request=self._admin_request()
        if not callable(request):
            QMessageBox.warning(self,'Satış iptali','Yönetici yetkisi gereklidir.')
            return
        qty=int(sale.get('quantity') or 0)
        question=(f"{qty} adetlik satış iptal edilecek.\n"
                  "Aynı alım partisine stok geri eklenecek; satış geçmişi silinmeyecek.\n"
                  "Devam edilsin mi?")
        if QMessageBox.question(self,'Satışı iptal et',question,
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
                )!=QMessageBox.StandardButton.Yes:return
        reason,ok=QInputDialog.getText(self,'Satış iptal nedeni',
                                        'İşlem geçmişi için kısa açıklama:')
        if not ok or not reason.strip():return
        pid=str(sale['product_id'])
        sid=str(sale['id'])
        self.cancel_sale_button.setEnabled(False)
        self.sync_note.setText('Satış iptal işlemi Firebase’de doğrulanıyor…')
        def done(_):
            self.sync_note.setText('Satış iptal edildi · stok güncelleniyor')
            self._parent_sync()
        def failed(_):
            self.sync_note.setText('Satış iptal edilemedi; stok korunuyor')
            self._sale_selection_changed()
        self._run_job('cancel_sale',lambda:request('admin_inventory_cancel_sale',
                      product_id=pid,sale_id=sid,reason=reason.strip()),done,failed)

    def render(self,*_):
        rows=[x for x in (getattr(self.db,'inventory_products',[]) or [])
              if x.get('active',True) and x.get('in_inventory',True)]
        term=self.search.text().casefold().strip()
        if term:
            rows=[p for p in rows if term in (' '.join([
                str(p.get('title') or ''),str(p.get('sku') or ''),str(p.get('category') or ''),
                ' '.join(p.get('tags') or [])])).casefold()]
        cat=self.category.currentText()
        if cat!='Tüm kategoriler':rows=[p for p in rows if str(p.get('category') or 'Genel')==cat]
        scope=self.scope.currentIndex()
        if scope==1:rows=[p for p in rows if int(p.get('quantity') or 0)>0]
        elif scope==2:rows=[p for p in rows if self.sales_counts.get(str(p['id']),0)>0]
        sort=self.sort.currentIndex()
        if sort==0:rows.sort(key=lambda p:(-self.sales_counts.get(str(p['id']),0),-int(p.get('quantity') or 0),str(p.get('title') or '')))
        if sort==1:rows.sort(key=lambda p:str(p.get('title') or '').casefold())
        if sort==2:rows.sort(key=lambda p:-int(p.get('quantity') or 0))
        if sort==3:rows.sort(key=lambda p:-self.sales_amounts.get(str(p['id']),0))
        while self.flow.count():
            item=self.flow.takeAt(0)
            if item.widget():item.widget().deleteLater()
        if not rows:
            empty=QLabel('Envanter henüz boş. Önce Envanter → Genel Ürünler bölümünden ürün kartı oluşturup Alım partisi ekle seçeneğini kullanabilirsin.')
            empty.setWordWrap(True);empty.setMinimumHeight(170)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.flow.addWidget(empty)
        else:
            scores=[math.log1p(int(p.get('quantity') or 0)+2*self.sales_counts.get(str(p['id']),0)) for p in rows]
            maximum=max(scores or [1]);minimum=min(scores or [0]);span=max(0.1,maximum-minimum)
            for p,score in zip(rows,scores):
                level=round((score-minimum)/span*2) if len(rows)>1 else 1
                level=max(0,min(2,level))
                card=ProductCard(p,self.sales_counts.get(str(p['id']),0),level,
                    self.owner,self.sale,self.edit_product,self.show_details,self._picture)
                self.flow.addWidget(card)
        self.stage.updateGeometry()
