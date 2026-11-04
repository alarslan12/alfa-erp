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
    QSizePolicy, QFormLayout, QStackedWidget, QProgressBar, QCompleter
)


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
        fields.append(('Satış fiyatı',self.price))
        if not self.catalog_only:
            fields.append(('Birim maliyet',self.cost))
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


class ProductCard(QFrame):
    def __init__(self,product,sales,largeness,owner,on_sale,on_edit,on_details,on_cover):
        super().__init__()
        self.product=product;self.setObjectName('InventoryCard')
        width,height=((215,286),(263,328),(311,375))[largeness]
        self.setFixedSize(width,height)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        box=QVBoxLayout(self);box.setContentsMargins(13,13,13,13);box.setSpacing(5)
        line=QHBoxLayout()
        category=QLabel(str(product.get('category') or 'Genel')[:30]);category.setObjectName('InventoryCategory')
        line.addWidget(category,1)
        stock=int(product.get('quantity') or 0)
        qty=QLabel(f'{stock} adet');qty.setObjectName('InventoryQty')
        line.addWidget(qty);box.addLayout(line)
        picture=QLabel('📦');picture.setObjectName('InventoryPicture')
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter);picture.setFixedHeight({0:105,1:135,2:166}[largeness])
        picture.setMinimumWidth(100)
        box.addWidget(picture)
        if product.get('image_url'):on_cover(picture,str(product['image_url']))
        name=QLabel(str(product.get('title') or 'İsimsiz ürün'))
        name.setObjectName('InventoryName');name.setWordWrap(True)
        name.setMaximumHeight(46);box.addWidget(name)
        tags=', '.join(str(x) for x in (product.get('tags') or [])[:3])
        meta=QLabel(tags or str(product.get('sku') or ''))
        meta.setObjectName('InventoryMeta');meta.setWordWrap(True);meta.setMaximumHeight(33)
        box.addWidget(meta)
        box.addStretch(1)
        price=QHBoxLayout();cost=QLabel(f"{float(product.get('sale_price') or 0):,.2f} TL")
        cost.setObjectName('InventoryPrice');price.addWidget(cost);price.addStretch()
        if sales:price.addWidget(QLabel(f"{sales} satış"))
        box.addLayout(price)
        controls=QHBoxLayout();controls.setSpacing(5)
        detail=QPushButton('Detay');detail.clicked.connect(lambda:on_details(product))
        controls.addWidget(detail,1)
        sell=QPushButton('Satış');sell.setEnabled(stock>0);sell.setAccessibleName('Ürün satışı kaydet')
        sell.clicked.connect(lambda:on_sale(product));controls.addWidget(sell,1)
        if owner:
            edit=QPushButton('Düzenle');edit.clicked.connect(lambda:on_edit(product));controls.addWidget(edit,1)
        box.addLayout(controls)


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
        self.db=db;self.jobs=set();self.last_signature=None
        self.network=QNetworkAccessManager(self)
        self.image_cache={};self.pending_images={}
        self.setObjectName('InventoryRoot')
        main=QVBoxLayout(self);main.setContentsMargins(15,12,15,12);main.setSpacing(11)
        title=QHBoxLayout()
        heading=QLabel('Ürünler & Envanter');heading.setObjectName('PageTitle');title.addWidget(heading)
        title.addStretch()
        self.sync_note=QLabel('Supabase · ortak ürün kataloğu');self.sync_note.setObjectName('Muted')
        title.addWidget(self.sync_note)
        self.add_button=QPushButton('＋  Katalogdan envantere ekle');self.add_button.setObjectName('Accent')
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

    def _run_job(self,action,fn,success):
        job=InventoryJob(action,fn,self)
        self.jobs.add(job)
        def done(value):
            self.jobs.discard(job)
            success(value)
        def failed(message):
            self.jobs.discard(job)
            QMessageBox.warning(self,'Envanter',message)
        job.success.connect(done);job.error.connect(failed)
        job.finished.connect(job.deleteLater);job.start()

    def show_details(self,product):
        dialog=QDialog(self)
        dialog.setWindowTitle('Ürün detayları · '+str(product.get('title') or 'Ürün'))
        dialog.resize(490,535)
        layout=QVBoxLayout(dialog)
        name=QLabel(str(product.get('title') or 'Ürün'))
        name.setObjectName('PageTitle');name.setWordWrap(True);layout.addWidget(name)
        info=QLabel(f"Kod: {product.get('sku','')}  •  Kategori: {product.get('category','Genel')}  •  "
                    f"{int(product.get('quantity') or 0)} adet")
        info.setWordWrap(True);layout.addWidget(info)
        image=QLabel('📦')
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setFixedHeight(180)
        image.setObjectName('InventoryPicture')
        layout.addWidget(image)
        if product.get('image_url'):self._picture(image,str(product['image_url']))
        layout.addWidget(QLabel(f"Satış fiyatı: {float(product.get('sale_price') or 0):,.2f} TL"))
        tags=QLabel('Etiketler: '+(', '.join(product.get('tags') or []) or '—'))
        tags.setWordWrap(True);layout.addWidget(tags)
        scroll=QTextEdit();scroll.setReadOnly(True)
        attrs=product.get('attributes') or {}
        content=str(product.get('description') or '')
        if attrs:content+='\n\nÖZELLİKLER\n'+'\n'.join(f'{key}: {value}' for key,value in attrs.items())
        scroll.setPlainText(content or 'Açıklama eklenmemiş.');layout.addWidget(scroll,1)
        close=QPushButton('Kapat');close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def add_from_catalog(self):
        """Select a master product, then set total stock and prices separately."""
        if not self.owner:
            return
        request=self._admin_request()
        if request is None:
            QMessageBox.warning(self,'Envanter','Yönetici oturumu bulunamadı.')
            return
        products=sorted((p for p in self.db.inventory_products if p.get('active',True)),
                        key=lambda p:str(p.get('title') or '').casefold())
        if not products:
            QMessageBox.information(self,'Envanter',
                'Genel ürün kataloğu boş. Önce Katalog → Genel Ürünler sekmesinde ürün oluştur.')
            return
        dialog=QDialog(self)
        dialog.setWindowTitle('Genel katalogdan envantere ürün ekle')
        dialog.resize(570,310)
        layout=QVBoxLayout(dialog)
        hint=QLabel('Ürün seç, toplam stok adedini ve fiyatını belirle. '
            'Mevcut ürünü seçersen yeni değerlerle güncellenir.')
        hint.setWordWrap(True);layout.addWidget(hint)
        form=QFormLayout()
        product_select=QComboBox()
        product_select.setEditable(True)
        for p in products:
            label=f"{p.get('sku','')} · {p.get('title','')}"
            if p.get('in_inventory',True):
                label+='   (envanterde)'
            product_select.addItem(label,str(p.get('id')))
        product_select.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer=product_select.completer()
        if completer is not None:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        total=QSpinBox();total.setRange(0,10000000)
        price=QDoubleSpinBox();price.setRange(0,999999999)
        price.setDecimals(2);price.setSuffix(' TL')
        cost=QDoubleSpinBox();cost.setRange(0,999999999)
        cost.setDecimals(2);cost.setSuffix(' TL')
        def update_fields(index):
            if index<0 or index>=len(products):return
            p=products[index]
            total.setValue(int(p.get('quantity') or 0))
            price.setValue(float(p.get('sale_price') or 0))
            cost.setValue(float(p.get('cost_price') or 0))
        product_select.currentIndexChanged.connect(update_fields)
        form.addRow('Genel katalog ürünü',product_select)
        form.addRow('Yeni toplam stok',total)
        form.addRow('Satış fiyatı',price)
        form.addRow('Birim maliyet',cost)
        layout.addLayout(form)
        buttons=QHBoxLayout();buttons.addStretch()
        cancel=QPushButton('Vazgeç');cancel.clicked.connect(dialog.reject)
        save=QPushButton('Envantere kaydet');save.setObjectName('Accent')
        save.clicked.connect(dialog.accept)
        buttons.addWidget(cancel);buttons.addWidget(save);layout.addLayout(buttons)
        update_fields(0)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        index=product_select.currentIndex()
        if (index<0 or index>=len(products) or
            product_select.currentText().strip()!=product_select.itemText(index).strip()):
            QMessageBox.warning(self,'Envanter',
                'Yanlış ürüne stok kaydetmemek için açılır listeden bir ürün seçmelisiniz.')
            return
        product=products[index]
        payload={**product,'id':product['id'],'quantity':total.value(),
                 'sale_price':price.value(),'cost_price':cost.value(),
                 'in_inventory':True}
        self.sync_note.setText('Ürün envantere kaydediliyor…')
        def success(_):
            self.sync_note.setText('Envanter güncellendi · diğer bilgisayarlarla eşitleniyor')
            self._parent_sync()
        self._run_job('inventory_catalog_assign',
            lambda:request('admin_inventory_upsert',product=payload),success)

    def edit_product(self,product):
        if not self.owner:
            return
        request=self._admin_request()
        if request is None:
            QMessageBox.information(self,'Yönetim girişi',
                'Ürün kataloğunu düzenlemek için üstteki Yönetim düğmesine basıp yönetici girişi yapın.\n'
                'Sonra bu sekmeye dönerek ürün ekleyebilirsiniz.')
            return
        editor=ProductDialog(product,self)
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
        if int(product.get('quantity') or 0)<=0:return
        dialog=QDialog(self);dialog.setWindowTitle('Satış kaydı')
        lay=QVBoxLayout(dialog)
        lay.addWidget(QLabel(str(product['title'])))
        qty=QSpinBox();qty.setRange(1,int(product.get('quantity') or 1))
        amount=QDoubleSpinBox();amount.setRange(0,999999999)
        amount.setDecimals(2);amount.setValue(float(product.get('sale_price') or 0));amount.setSuffix(' TL')
        form=QFormLayout();form.addRow('Satılan adet',qty);form.addRow('Birim satış fiyatı',amount);lay.addLayout(form)
        actions=QHBoxLayout();cancel=QPushButton('Vazgeç');cancel.clicked.connect(dialog.reject)
        submit=QPushButton('Satışı kaydet');submit.setObjectName('Accent');submit.clicked.connect(dialog.accept)
        actions.addWidget(cancel);actions.addWidget(submit);lay.addLayout(actions)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        device=getattr(self.window(),'device',None)
        if device is None or not device.paired:
            QMessageBox.warning(self,'Bulut','Cihaz buluta eşleştirilmemiş.');return
        self.sync_note.setText('Satış buluta işleniyor…')
        def success(_):
            self.sync_note.setText('Satış kaydedildi · eşitleniyor')
            self._parent_sync()
        self._run_job('sale',lambda:device.inventory_sale(product['id'],qty.value(),amount.value()),success)

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
            colors=('#1c2838','#23384c','#486079','#eef5fc','#b9c9d7','#89d6cd','#203947')
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
        ''')

    def refresh(self):
        rows=getattr(self.db,'inventory_products',[]) or []
        sales=getattr(self.db,'inventory_sales',[]) or []
        counts=defaultdict(int);money=0.0;cost=0.0
        for sale in sales:
            n=int(sale.get('quantity') or 0)
            counts[str(sale.get('product_id'))]+=n
            money+=n*float(sale.get('sale_price') or 0)
            cost+=n*float(sale.get('cost_price') or 0)
        self.sales_counts=dict(counts)
        self.sales_amounts=defaultdict(float)
        for sale in sales:
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
        self.update_analytics(active,sales)

    def update_analytics(self,products,sales):
        today=date.today();start=today-timedelta(days=29)
        days={start+timedelta(days=i):0.0 for i in range(30)}
        gross=0.0;profit=0.0;counts=defaultdict(int)
        for sale in sales:
            n=int(sale.get('quantity') or 0)
            amount=n*float(sale.get('sale_price') or 0)
            gross+=amount
            profit+=n*(float(sale.get('sale_price') or 0)-float(sale.get('cost_price') or 0))
            counts[str(sale.get('product_id'))]+=n
            try:dt=date.fromisoformat(str(sale.get('created_at') or '')[:10])
            except ValueError:continue
            if dt in days:days[dt]+=amount
        self.bars.set_data([(day.isoformat(),amount) for day,amount in days.items()])
        self.sales_stats.setText(
            f'Toplam {sum(counts.values()):,} adet satış   •   Ciro: {gross:,.2f} TL'
            f'   •   Brüt fark: {profit:,.2f} TL   •   Ürün çeşidi: {len(products):,}')
        while self.top_products.count():
            entry=self.top_products.takeAt(0)
            if entry.widget():entry.widget().deleteLater()
        product_by_id={str(x['id']):x for x in products}
        ranking=sorted(counts.items(),key=lambda x:-x[1])[:9]
        if not ranking:
            self.top_products.addWidget(QLabel('Henüz satış kaydı yok.'))
            return
        largest=max(counts.values())
        for product_id,n in ranking:
            p=product_by_id.get(product_id)
            if not p:continue
            line=QHBoxLayout()
            name=QLabel(str(p.get('title') or 'Ürün'))
            name.setMinimumWidth(180);name.setMaximumWidth(300);line.addWidget(name)
            bar=QProgressBar();bar.setRange(0,largest)
            bar.setValue(n);bar.setFormat(f'{n} adet')
            line.addWidget(bar,1)
            wrapper=QWidget();wrapper.setLayout(line)
            self.top_products.addWidget(wrapper)

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
            empty=QLabel('Envanter henüz boş. Yönetici olarak Katalog → Genel Ürünler bölümünden ürün oluşturup burada Katalogdan envantere ekle seçeneğini kullanabilirsin.')
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
