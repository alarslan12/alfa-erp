"""Order intake and Gardrops net proceeds helpers."""
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QMessageBox, QLabel

def net_revenue(amount, platform):
    value=Decimal(str(amount).replace(",","."))
    if not value.is_finite() or value < 0:raise ValueError("Geçersiz tutar")
    if str(platform).casefold().strip()=="gardrops":
        return int((value*Decimal("0.90")).to_integral_value(rounding=ROUND_CEILING))
    return float(value)

class BuyerDetailsDialog(QDialog):
    def __init__(self,parent=None,existing=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni sipariş · Alıcı ve teslimat bilgileri")
        self.setMinimumWidth(480)
        data=existing or {}
        root=QVBoxLayout(self)
        root.addWidget(QLabel("Gönderinin Kargonomi barkodu için alıcı bilgilerini girin."))
        form=QFormLayout();self.fields={}
        for key,label,example in [
            ("alici_adi","Ad Soyad","Ad ve soyad"),
            ("telefon","Telefon","5XXXXXXXXX · 10 hane"),
            ("adres","Açık adres","Mahalle, sokak, bina, daire"),
            ("il","İl","Kargonomi il seçimi"),
            ("ilce","İlçe","Kargonomi ilçe seçimi")]:
            inp=QLineEdit(str(data.get(key) or ""))
            inp.setPlaceholderText(example);self.fields[key]=inp;form.addRow(label,inp)
        root.addLayout(form)
        root.addWidget(QLabel("İl ve ilçe adları gönderi sırasında Kargonomi ile otomatik eşleştirilir."))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Alıcı bilgilerini kaydet")
        buttons.accepted.connect(self.validate);buttons.rejected.connect(self.reject);root.addWidget(buttons)
        self.values=None
    def validate(self):
        value={k:w.text().strip() for k,w in self.fields.items()}
        digits="".join(c for c in value["telefon"] if c.isdigit())
        if len(digits)==11 and digits.startswith("0"):digits=digits[1:]
        if len(value["alici_adi"].split())<2 or len(value["alici_adi"])<5:
            QMessageBox.warning(self,"Alıcı","Ad ve soyadı girin.");return
        if len(digits)!=10 or not digits.startswith("5"):
            QMessageBox.warning(self,"Telefon","Telefon 5XXXXXXXXX biçiminde olmalı.");return
        if len(value["adres"])<10:
            QMessageBox.warning(self,"Adres","En az 10 karakterlik açık adres gerekli.");return
        if not value["il"] or not value["ilce"]:
            QMessageBox.warning(self,"İl/ilçe","İl ve ilçeyi belirtin.");return
        value["telefon"]=digits;self.values=value;self.accept()

def request_buyer_details(parent,previous=None):
    dialog=BuyerDetailsDialog(parent,previous)
    return dialog.values if dialog.exec()==QDialog.DialogCode.Accepted else None
