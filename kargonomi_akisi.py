"""Explicit two-phase Kargonomi shipment and Yeni Barkod workflow."""
import base64
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QVBoxLayout
)
from kargonomi import (
    ApiWorker, KargonomiClient, CONFIG_DIR, saved_token, warehouse_id
)


def _normalize_place(value):
    import unicodedata
    value=str(value or "").strip().casefold().replace("ı","i")
    return "".join(c for c in unicodedata.normalize("NFD",value) if not unicodedata.combining(c)).replace(" ","")

def _location_records(response):
    if isinstance(response,list):
        return [r for r in response if isinstance(r,dict)]
    if isinstance(response,dict):
        for field in ("data","states","cities","results","items"):
            if field in response:
                return _location_records(response[field])
    return []

def _location_id(response, city_name):
    target=_normalize_place(city_name)
    for entry in _location_records(response):
        for label in ("name","state_name","city_name","title"):
            if _normalize_place(entry.get(label))==target:
                try:return int(entry["id"])
                except (KeyError,ValueError,TypeError):continue
    raise ValueError(f"Kargonomi il/ilçe eşleştirmesi bulunamadı: {city_name}. Adı kontrol edin.")

def shipment_identifier(response):
    if not isinstance(response, dict):
        return None
    for candidate in (
        response.get("shipment"), response.get("data"), response
    ):
        if isinstance(candidate, dict) and str(candidate.get("id","")).isdigit():
            return int(candidate["id"])
    return None


def decode_barcode(response):
    """Decode documented JSON base64 PDF, accepting common response wrappers."""
    items=[response]
    for _ in range(3):
        next_items=[]
        for value in items:
            if isinstance(value, dict):
                for key in ("barcode","pdf","data","content","file","result"):
                    if key in value:
                        next_items.append(value[key])
            elif isinstance(value, str):
                try:
                    payload=base64.b64decode(value.split(",")[-1],validate=True)
                    if payload.startswith(b"%PDF"):
                        return payload
                except (ValueError,base64.binascii.Error):
                    pass
        items=next_items
    raise ValueError("Kargonomi yanıtında geçerli PDF barkod bulunamadı.")


class ShipmentCompletionDialog(QDialog):
    """Does not mark an ERP order completed before its barcode is available."""
    def __init__(self, database, order, parent=None):
        super().__init__(parent)
        self.db=database
        self.order=order
        self.worker=None
        self.setWindowTitle(f"Sipariş #{order['id']} · Kargonomi / Yeni Barkod")
        self.setMinimumWidth(535)
        self.resize(600,360)
        self.setModal(True)
        root=QVBoxLayout(self)
        root.addWidget(QLabel(
            "Sipariş tamamlanmadan önce desiyi girin, kargo teklifini onaylayın ve Yeni Barkod alın."
        ))
        form=QFormLayout()
        self.desi=QDoubleSpinBox()
        self.desi.setRange(0.1,1000)
        self.desi.setDecimals(2)
        self.desi.setSingleStep(0.5)
        self.desi.setValue(float(order.get("kargonomi_desi") or 1))
        self.desi.setSuffix(" desi")
        self.desi.setEnabled(not bool(order.get("kargonomi_shipment_id")))
        form.addRow("Paket desi",self.desi)
        self.provider=QComboBox()
        self.provider.addItem("Önce fiyatları getiriniz",None)
        form.addRow("Kargo firması",self.provider)
        root.addLayout(form)
        self.status=QLabel("Hazır. Kargonomi anahtarı ve depo ayarları bir kez kaydedilmelidir.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        row=QHBoxLayout()
        self.offer=QPushButton("Kargo tekliflerini getir")
        self.offer.clicked.connect(self.prepare)
        row.addWidget(self.offer)
        self.barcode=QPushButton("Yeni Barkod")
        self.barcode.clicked.connect(self.make_barcode)
        row.addWidget(self.barcode)
        self.cancel=QPushButton("Vazgeç")
        self.cancel.clicked.connect(self.reject)
        row.addWidget(self.cancel)
        root.addLayout(row)
        self.barcode.setEnabled(bool(order.get("kargonomi_onaylandi")))

    def client(self):
        token=saved_token()
        if not token:
            raise ValueError("Kargonomi API anahtarı yok. ERP üst menüsü → Kargonomi → Bağlantı bilgilerini bir kez kaydet.")
        if not warehouse_id():
            raise ValueError("Kargonomi gönderici depo ID ayarlı değil. Kargonomi menüsünden bir kez kaydedin.")
        return KargonomiClient(token)

    def launch(self, task, on_success):
        if self.worker and self.worker.isRunning():
            current=self.worker
            current.finished.connect(lambda: self.launch(task,on_success))
            return
        try:
            client=self.client()
        except Exception as exc:
            QMessageBox.warning(self,"Kargonomi",str(exc))
            return
        self.offer.setEnabled(False)
        self.barcode.setEnabled(False)
        self.cancel.setEnabled(False)
        self.status.setText("Kargonomi işlemi sürüyor…")
        self.worker=ApiWorker(lambda:task(client),self)
        def done(data):
            self.offer.setEnabled(True)
            self.cancel.setEnabled(True)
            self.barcode.setEnabled(bool(self.order.get("kargonomi_onaylandi")))
            try:on_success(data)
            except Exception as exc:
                self.status.setText("İşlem durdu: "+str(exc))
                QMessageBox.warning(self,"Kargonomi",str(exc))
        def fail(message):
            self.offer.setEnabled(True)
            self.cancel.setEnabled(True)
            self.barcode.setEnabled(bool(self.order.get("kargonomi_onaylandi")))
            self.status.setText(message+" · Sipariş tamamlanmadı.")
        self.worker.done.connect(done)
        self.worker.failed.connect(fail)
        self.worker.start()

    def prepare(self):
        required=("alici_adi","telefon","adres","il","ilce")
        if any(not str(self.order.get(k) or "").strip() for k in required):
            QMessageBox.warning(self,"Eksik alıcı bilgisi",
                "Siparişin ad-soyad, telefon, açık adres, il veya ilçe alanları eksik.")
            return
        if self.order.get("kargonomi_onaylandi"):
            self.status.setText("Gönderi daha önce onaylandı; Yeni Barkod düğmesini kullanın.")
            self.barcode.setEnabled(True)
            return
        existing_id=self.order.get("kargonomi_shipment_id")
        if existing_id:
            self.fetch_prices(int(existing_id))
            return
        desi=float(self.desi.value())
        if QMessageBox.question(
            self,"Kargonomi gönderisi oluştur",
            f"#{self.order['id']} için {desi:g} desilik gönderi Kargonomi'ye kaydedilecek. Devam edilsin mi?"
        ) != QMessageBox.StandardButton.Yes:
            return
        def create_with_location(api):
            state_id=int(self.order.get("alici_il_id") or 0) or _location_id(api.states(),self.order["il"])
            city_id=int(self.order.get("alici_ilce_id") or 0) or _location_id(api.cities(state_id),self.order["ilce"])
            shipment={
                "warehouse_id":warehouse_id(),
                "buyer_name":str(self.order["alici_adi"]),
                "buyer_phone":str(self.order["telefon"]),
                "buyer_address":str(self.order["adres"]),
                "buyer_state_id":state_id,
                "buyer_city_id":city_id,
                "packages":[{"desi":desi,"content":"Kitap"}]
            }
            response=api.create(shipment)
            return {"response":response,"state_id":state_id,"city_id":city_id}
        self.launch(create_with_location,lambda result:self.created(result,desi))

    def created(self, result, desi):
        response=result["response"]
        sid=shipment_identifier(response)
        if not sid:
            raise ValueError("API gönderiyi oluşturmuş olabilir ama ID yanıtı okunamadı. Yeniden denemeden önce Kargonomi panelinden kontrol edin.")
        self.order["alici_il_id"]=result["state_id"]
        self.order["alici_ilce_id"]=result["city_id"]
        self.order["kargonomi_shipment_id"]=sid
        self.order["kargonomi_desi"]=desi
        self.db.siparisleri_kaydet()
        self.status.setText(f"Gönderi taslağı #{sid} kaydedildi. Fiyat teklifleri alınıyor…")
        self.fetch_prices(sid)

    def fetch_prices(self,sid):
        self.launch(lambda api:api.prices(sid),self.prices_received)

    def prices_received(self,response):
        options=response.get("shipping_provider_with_price",[]) if isinstance(response,dict) else []
        self.provider.clear()
        for entry in options:
            if not isinstance(entry,dict):continue
            try: pid=int(entry["id"])
            except (ValueError,KeyError,TypeError):continue
            self.provider.addItem(
                f"{entry.get('name','Firma')} · {entry.get('price') or 'otomatik'}",pid
            )
        if not any(self.provider.itemData(i)==-1 for i in range(self.provider.count())):
            self.provider.addItem("Otomatik · en uygun teklif", -1)
        if not self.provider.count():
            raise ValueError("Kargonomi fiyat teklifi dönmedi.")
        for index in range(self.provider.count()):
            if self.provider.itemData(index)==-1:
                self.provider.setCurrentIndex(index)
                break
        self.barcode.setEnabled(True)
        self.status.setText("Kargo firmasını seçip Yeni Barkod düğmesine basın. Onay ücret doğurabilir.")

    def make_barcode(self):
        sid=self.order.get("kargonomi_shipment_id")
        if not sid:
            QMessageBox.warning(self,"Kargonomi","Önce kargo tekliflerini alın.")
            return
        if self.order.get("kargonomi_onaylandi"):
            self.launch(lambda api:api.barcode(sid),self.barcode_received)
            return
        pid=self.provider.currentData()
        if pid is None:
            QMessageBox.warning(self,"Kargonomi","Kargo firması seçiniz.")
            return
        if QMessageBox.question(self,"Kargo bedeli onayı",
            "Seçtiğiniz kargo firmasının teklifini kabul etmek ve gerçek kargo gönderisini oluşturmak istiyor musunuz?"
        )!=QMessageBox.StandardButton.Yes:
            return
        self.launch(lambda api:api.confirm(sid,pid),self.confirmed)

    def confirmed(self,response):
        self.order["kargonomi_onaylandi"]=True
        self.order["kargonomi_firma_id"]=int(self.provider.currentData())
        self.db.siparisleri_kaydet()
        self.status.setText("Gönderi onaylandı. Yeni Barkod hazırlanıyor…")
        self.launch(lambda api:api.barcode(self.order["kargonomi_shipment_id"]),self.barcode_received)

    def barcode_received(self,response):
        pdf=decode_barcode(response)
        target=CONFIG_DIR/"KargonomiBarcodes"/f"Yeni_Barkod_{self.order['id']}.pdf"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(pdf)
        self.order["kargonomi_barkod_yolu"]=str(target)
        self.db.siparisleri_kaydet()
        self.status.setText("Yeni Barkod PDF hazır. Sipariş tamamlanabilir.")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        if self.worker and self.worker.isRunning():
            self.worker.finished.connect(self.accept)
        else:
            self.accept()

    def reject(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self,"Kargonomi","Ağ işlemi tamamlanmadan pencere kapatılamaz.")
            return
        super().reject()

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            event.ignore()
            return
        super().closeEvent(event)


def request_kargonomi_completion(parent,database,order):
    dialog=ShipmentCompletionDialog(database,order,parent)
    return dialog.exec()==QDialog.DialogCode.Accepted
