"""Sipariş tamamlama sırasında güvenli, imleç kaydırmayan kargo gideri formu."""
from decimal import Decimal, InvalidOperation
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QDialogButtonBox,QMessageBox,
    QFrame
)
from widgets import text


class ShippingCostDialog(QDialog):
    def __init__(self,order,category,parent=None):
        super().__init__(parent)
        self.setWindowTitle('ALFA ERP · Kargo gideri')
        self.setObjectName('ShippingCostDialog')
        self.setModal(True)
        self.setFixedWidth(410)
        self.value=None
        root=QVBoxLayout(self);root.setContentsMargins(20,20,20,18);root.setSpacing(12)
        caption='Telafi siparişi' if category=='telafi' else 'Normal açık adres siparişi'
        root.addWidget(text('▣  KARGO GİDERİNİ KAYDET','SettingsHeading'))
        root.addWidget(text(f"Sipariş #{order.get('id')} · {caption}",'Muted'))
        root.addWidget(text('Siparişi tamamlamadan önce gerçekleşen kargo ücretini gir.','SettingsHint',wrap=True))
        frame=QFrame();frame.setObjectName('OrderEditRevenueBox')
        row=QHBoxLayout(frame);row.setContentsMargins(10,6,10,6);row.setSpacing(5)
        self.amount=QLineEdit()
        self.amount.setObjectName('OrderEditRevenueInput')
        self.amount.setPlaceholderText('0,00')
        self.amount.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.amount.setText(f"{float(order.get('kargo_ucreti',0) or 0):.2f}".replace('.',','))
        row.addWidget(self.amount,1)
        row.addWidget(text('TL','OrderEditCurrencyLabel'))
        root.addWidget(frame)
        root.addWidget(text('0 TL geçerli bir değerdir. Telafi ve açık adres giderleri analitikte ayrı hesaplanır.',
                            'SettingsHint',wrap=True))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Kargo tutarını kaydet')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('İptal')
        buttons.accepted.connect(self.accept_value)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.amount.selectAll()

    def accept_value(self):
        raw=self.amount.text().strip().replace(' ', '').replace('₺','')
        if not raw:
            QMessageBox.warning(self,'Kargo ücreti','Bir değer gir veya 0 yaz.')
            return
        try:
            if ',' in raw and '.' in raw:
                normalized=raw.replace('.','').replace(',','.') if raw.rfind(',')>raw.rfind('.') else raw.replace(',','')
            else:
                normalized=raw.replace(',','.')
            value=Decimal(normalized)
        except (InvalidOperation,ValueError):
            QMessageBox.warning(self,'Kargo ücreti','Geçerli bir sayı gir. Örnek: 85,50')
            return
        if not value.is_finite() or value<0 or value>10_000_000:
            QMessageBox.warning(self,'Kargo ücreti','Kargo tutarı 0 ile 10.000.000 TL arasında olmalı.')
            return
        self.value=float(round(value,2))
        self.accept()


def request_shipping_cost(parent,order,category):
    dialog=ShippingCostDialog(order,category,parent)
    return dialog.value if dialog.exec()==QDialog.DialogCode.Accepted else None
