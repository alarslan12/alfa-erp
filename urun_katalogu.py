"""Shared general product catalogue, separate from the printed-book ordering catalogue.

Product master records live in the shared Firebase Realtime Database. Only products explicitly
assigned to inventory appear in the stock/sales panel. Staff can browse the
general catalogue; only an authenticated owner can make modifications.
"""
import base64
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (
    QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QMessageBox,QDialog
)
from ekran_envanter import ProductDialog,InventoryJob


class GeneralProductCatalog(QWidget):
    def __init__(self,db,parent=None):
        super().__init__(parent)
        self.db=db;self.jobs=set()
        self.setObjectName('GeneralProductCatalog')
        root=QVBoxLayout(self);root.setContentsMargins(10,8,10,10);root.setSpacing(12)
        header=QHBoxLayout()
        title=QLabel('GENEL ÜRÜN KATALOĞU')
        title.setObjectName('GeneralCatalogTitle');header.addWidget(title)
        header.addStretch()
        self.new_button=QPushButton('＋ Yeni ürün kartı')
        self.new_button.setObjectName('GeneralCatalogAction')
        self.new_button.clicked.connect(lambda:self.edit_product(None))
        header.addWidget(self.new_button)
        root.addLayout(header)
        info=QLabel('Ürün önce burada kaydedilir. Alım yapmak için Envanter → Stok ve Envanter → Alım partisi ekle yolunu kullan.')
        info.setWordWrap(True);info.setObjectName('GeneralCatalogHint');root.addWidget(info)
        row=QHBoxLayout()
        self.search=QLineEdit();self.search.setPlaceholderText('Ürün adı, kodu, kategori veya etikette ara…')
        self.search.textChanged.connect(self.render)
        row.addWidget(self.search,1)
        self.edit_button=QPushButton('Seçili ürünü düzenle')
        self.edit_button.setObjectName('GeneralCatalogAction')
        self.edit_button.clicked.connect(self.edit_selected)
        row.addWidget(self.edit_button)
        root.addLayout(row)
        self.table=QTableWidget(0,5)
        self.table.setObjectName('GeneralCatalogTable')
        self.table.setHorizontalHeaderLabels(['Ürün kodu','Ürün adı','Kategori','Mevcut stok','Envanter'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True);self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(43)
        head=self.table.horizontalHeader()
        head.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        head.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(lambda _:self.edit_selected())
        root.addWidget(self.table,1)
        self.counter=QLabel('')
        self.counter.setObjectName('GeneralCatalogHint');root.addWidget(self.counter)
        self.refresh()

    @property
    def can_edit(self):
        return callable(getattr(self.db,'owner_admin_request',None))

    def refresh(self):
        self.new_button.setVisible(self.can_edit)
        self.edit_button.setVisible(self.can_edit)
        self.apply_theme()
        self.render()

    def render(self,*_):
        products=[p for p in (getattr(self.db,'inventory_products',[]) or [])
                  if p.get('active',True)]
        products.sort(key=lambda p:(str(p.get('title') or '').casefold(),
                                    str(p.get('sku') or '').casefold()))
        term=self.search.text().strip().casefold()
        if term:
            products=[p for p in products if term in (' '.join((
                str(p.get('title') or ''),str(p.get('sku') or ''),
                str(p.get('category') or ''),' '.join(p.get('tags') or [])))).casefold()]
        selected=self.selected_id()
        self.table.blockSignals(True)
        self.table.setRowCount(len(products))
        for n,p in enumerate(products):
            values=[
                str(p.get('sku') or ''),str(p.get('title') or ''),
                str(p.get('category') or 'Genel'),
                f"{int(p.get('quantity') or 0):,} adet",
                'Stokta' if p.get('in_inventory',True) else 'Henüz eklenmedi'
            ]
            for col,val in enumerate(values):
                item=QTableWidgetItem(val)
                if col==0:item.setData(Qt.ItemDataRole.UserRole,str(p.get('id') or ''))
                self.table.setItem(n,col,item)
                if col==0 and str(p.get('id'))==selected:
                    self.table.selectRow(n)
        self.table.blockSignals(False)
        self.counter.setText(f'{len(products)} ürün · katalog tüm eşleşmiş bilgisayarlarda ortaktır.')

    def selected_id(self):
        row=self.table.currentRow()
        item=self.table.item(row,0) if row>=0 else None
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else ''

    def edit_selected(self):
        target=self.selected_id()
        product=next((p for p in self.db.inventory_products
                      if str(p.get('id'))==target),None)
        if not product:
            QMessageBox.information(self,'Ürün kataloğu','Önce bir ürün seçin.')
            return
        self.edit_product(product)

    def edit_product(self,product):
        request=getattr(self.db,'owner_admin_request',None)
        if not callable(request):
            QMessageBox.information(self,'Ürün kataloğu',
                'Ürün kartını düzenlemek için yönetici oturumu gereklidir.')
            return
        form=ProductDialog(product,self,catalog_only=True)
        if form.exec()!=QDialog.DialogCode.Accepted:return
        payload=form.value()
        if product is None:
            payload.update(in_inventory=False,quantity=0,cost_price=0)
        else:
            payload['in_inventory']=bool(product.get('in_inventory',True))
        image=form.image_bytes
        def save():
            if image:
                response=request('admin_inventory_image',mime='image/jpeg',
                    image_base64=base64.b64encode(image).decode('ascii'))
                payload['image_url']=response['url']
            return request('admin_inventory_upsert',product=payload)
        job=InventoryJob('general_catalog_upsert',save,self)
        self.jobs.add(job)
        def success(_result):
            self.jobs.discard(job)
            self.counter.setText('Ürün kaydedildi; bulut kataloğu yenileniyor…')
            live=getattr(self.window(),'live',None)
            if live is not None:
                live.force_pull=True
                QTimer.singleShot(250,live.pull)
        def failure(message):
            self.jobs.discard(job)
            QMessageBox.warning(self,'Ürün kaydedilemedi',message)
        job.success.connect(success);job.error.connect(failure)
        job.finished.connect(job.deleteLater);job.start()

    def apply_theme(self):
        name=QApplication.instance().property('alfa_theme') or 'koyu'
        palettes={
            'koyu':('#10243a','#1b3655','#f4f9ff','#b9d3eb','#4f7da7','#1a73b8'),
            'acik':('#f6f1e8','#fffaf2','#243a51','#63788c','#cfbea7','#e7d9c3'),
            'kontrast':('#070b10','#152b44','#ffffff','#e6f5ff','#91adcb','#284762')
        }
        bg,card,fg,muted,border,accent=palettes.get(name,palettes['koyu'])
        self.setStyleSheet(f"""
          QWidget#GeneralProductCatalog {{
            background:{bg};color:{fg};
          }}
          QLabel#GeneralCatalogTitle {{
            color:{fg};font-weight:900;font-size:16px;
          }}
          QLabel#GeneralCatalogHint {{color:{muted};font-size:12px;}}
          QLineEdit {{
            background:{card};color:{fg};border:1px solid {border};
            padding:9px;border-radius:8px;
          }}
          QPushButton#GeneralCatalogAction {{
            background:{accent};color:{fg};border:1px solid {border};
            border-radius:9px;padding:10px;font-weight:800;
          }}
          QTableWidget#GeneralCatalogTable {{
            background:{card};color:{fg};alternate-background-color:{bg};
            selection-background-color:{accent};selection-color:{fg};
            gridline-color:{border};border:1px solid {border};border-radius:9px;
          }}
          QHeaderView::section {{
            background:{accent};color:{fg};font-weight:800;
            padding:9px;border:0;border-bottom:1px solid {border};
          }}
        """)
