"""Kargonomi REST integration. Token stays in memory, never in repository or logs."""
import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QPlainTextEdit, QVBoxLayout, QWidget
)

BASE = "https://app.kargonomi.com.tr/api/v1"


class KargonomiClient:
    def __init__(self, token):
        if not str(token).strip():
            raise ValueError("Kargonomi API token gerekli.")
        self.token = str(token).strip()

    def request(self, method, endpoint, payload=None):
        if not endpoint.startswith("/") or "://" in endpoint:
            raise ValueError("Geçersiz API yolu.")
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = Request(
            BASE + endpoint, data=data, method=method,
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/json",
                     "Content-Type": "application/json"}
        )
        try:
            with urlopen(request, timeout=18) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except HTTPError as exc:
            # API may return buyer details or credentials in error payload; do not log body.
            raise RuntimeError(f"Kargonomi HTTP {exc.code}; alanları ve API yetkisini kontrol edin.") from None
        except (URLError, TimeoutError) as exc:
            raise RuntimeError("Kargonomi bağlantısı kurulamadı; ağ erişimini kontrol edin.") from None

    def shipments(self):
        return self.request("GET", "/shipments")

    def create(self, shipment):
        return self.request("POST", "/shipments", {"shipment": shipment})

    def detail(self, shipment_id):
        return self.request("GET", f"/shipments/{int(shipment_id)}")

    def prices(self, shipment_id):
        return self.request("GET", f"/shipment-price-comparison/{int(shipment_id)}")

    def confirm(self, shipment_id, provider_id):
        # Official API accepts form data for confirmation.
        body = urlencode({"shipment_id":int(shipment_id), "shipping_provider_id":int(provider_id)}).encode()
        request = Request(BASE + "/confirm-shipping-price", data=body,
                          headers={"Authorization":"Bearer " + self.token,
                                   "Accept":"application/json",
                                   "Content-Type":"application/x-www-form-urlencoded"},
                          method="POST")
        try:
            with urlopen(request, timeout=18) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Firma onayı başarısız: HTTP {exc.code}") from None
        except (URLError, TimeoutError):
            raise RuntimeError("Kargo firması onayında ağ hatası.") from None

    def barcode(self, shipment_id):
        return self.request("GET", f"/shipments/{int(shipment_id)}/barcode?format=pdf")


class ApiWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action=action

    def run(self):
        try:
            self.done.emit(self.action())
        except Exception as exc:
            self.failed.emit(str(exc))


class KargonomiDialog(QDialog):
    """Standalone shipping tool; source orders remain unchanged until confirmed."""
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.db=database
        self.setWindowTitle("Kargonomi · Kargo Yönetimi")
        self.resize(660,780)
        self.setMinimumWidth(550)
        self.worker=None
        self.current_shipment=None
        self.providers=[]
        self.fields={}
        root=QVBoxLayout(self)
        root.addWidget(QLabel("Kargonomi API · Onay verilmedikçe sipariş gönderilmez."))
        form=QFormLayout()
        self.token=QLineEdit(os.getenv("KARGONOMI_API_TOKEN",""))
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText("Bearer API token · sadece bu oturumda tutulur")
        form.addRow("API Token",self.token)
        self.order_select=QComboBox()
        self.order_select.addItem("Sipariş seçiniz (isteğe bağlı)",None)
        for order in database.siparisler:
            self.order_select.addItem(f"#{order.get('id')} · {str(order.get('kod',''))[:65]}",order.get("id"))
        self.order_select.currentIndexChanged.connect(self.select_order)
        form.addRow("ERP siparişi",self.order_select)
        self.shipment_id=QLineEdit()
        self.shipment_id.setPlaceholderText("Gönderi oluşturulduktan sonra otomatik dolar")
        form.addRow("Kargonomi gönderi ID",self.shipment_id)
        for key,label,placeholder in [
            ("warehouse_id","Gönderici depo ID","Kargonomi panelindeki depo ID"),
            ("buyer_name","Alıcı adı","Ad Soyad"),
            ("buyer_phone","Alıcı telefon","5XXXXXXXXX"),
            ("buyer_email","Alıcı e-posta","İsteğe bağlı"),
            ("buyer_address","Alıcı adresi","Açık adres"),
            ("buyer_state_id","İl ID","Kargonomi il kimliği"),
            ("buyer_city_id","İlçe ID","Kargonomi ilçe kimliği"),
            ("desi","Paket desi","1"),
            ("content","Paket içeriği","Kitap")]:
            field=QLineEdit()
            field.setPlaceholderText(placeholder)
            self.fields[key]=field
            form.addRow(label,field)
        self.fields["desi"].setText("1")
        self.fields["content"].setText("Kitap")
        root.addLayout(form)
        actions=QHBoxLayout()
        self.actions=[]
        for label,callback in [
            ("Gönderi listesi",self.list_shipments),
            ("Taslak oluştur",self.create_shipment),
            ("Fiyatları getir",self.get_prices),
            ("Gönderiyi kontrol et",self.get_detail),
            ("Barkod PDF",self.get_barcode)]:
            btn=QPushButton(label);btn.clicked.connect(callback);actions.addWidget(btn);self.actions.append(btn)
        root.addLayout(actions)
        pricing=QHBoxLayout()
        self.provider=QComboBox()
        self.provider.addItem("Önce fiyatları getiriniz",None)
        pricing.addWidget(self.provider)
        self.confirm_button=QPushButton("Seçili firmayı onayla")
        self.confirm_button.clicked.connect(self.confirm_shipping)
        pricing.addWidget(self.confirm_button)
        root.addLayout(pricing)
        self.output=QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Kargonomi sonuçları burada gösterilir. Kişisel bilgiler içerebilir.")
        root.addWidget(self.output)

    def select_order(self):
        sid=self.order_select.currentData()
        order=next((o for o in self.db.siparisler if str(o.get("id"))==str(sid)),None)
        if not order:
            return
        # ERP 'kod' is sometimes a cargo code, sometimes a pasted address.
        # Never treat an ambiguous cargo code as a validated postal address.
        for field,key in [("buyer_name","alici_adi"),("buyer_phone","telefon"),
                          ("buyer_address","adres")]:
            if order.get(key):
                self.fields[field].setText(str(order[key]))

    def client(self):
        return KargonomiClient(self.token.text())

    def run_request(self, call, on_done=None):
        if self.worker is not None and self.worker.isRunning():
            return
        try:
            api=self.client()
        except ValueError as exc:
            QMessageBox.warning(self,"Kargonomi",str(exc));return
        for btn in self.actions+[self.confirm_button]:
            btn.setEnabled(False)
        self.output.setPlainText("Kargonomi ile bağlantı kuruluyor…")
        self.worker=ApiWorker(lambda:call(api),self)
        def success(data):
            for btn in self.actions+[self.confirm_button]:btn.setEnabled(True)
            if on_done:on_done(data)
            display=data if isinstance(data,dict) else {"result":data}
            # Do not display bearer secret.
            self.output.setPlainText(json.dumps(display,ensure_ascii=False,indent=2)[:18000])
        def failure(message):
            for btn in self.actions+[self.confirm_button]:btn.setEnabled(True)
            self.output.setPlainText(message)
        self.worker.done.connect(success)
        self.worker.failed.connect(failure)
        self.worker.start()

    def sid(self):
        value=self.shipment_id.text().strip()
        if not value.isdecimal() or int(value)<=0:
            raise ValueError("Geçerli gönderi ID giriniz.")
        return int(value)

    def create_shipment(self):
        data={key:field.text().strip() for key,field in self.fields.items()}
        required=("warehouse_id","buyer_name","buyer_phone","buyer_address",
                  "buyer_state_id","buyer_city_id","desi","content")
        if any(not data.get(k) for k in required):
            QMessageBox.warning(self,"Kargonomi","Depo, alıcı, telefon, adres, il/ilçe ID, desi ve içerik zorunludur.")
            return
        if not all(data[k].isdigit() for k in ("warehouse_id","buyer_state_id","buyer_city_id")):
            QMessageBox.warning(self,"Kargonomi","Depo, il ve ilçe ID sayısal olmalı.")
            return
        if QMessageBox.question(self,"Gönderi oluştur",
                "Alıcı ve depo bilgileri Kargonomi'ye gönderilerek taslak oluşturulacak. Onaylıyor musunuz?"
                )!=QMessageBox.StandardButton.Yes:
            return
        shipment={
            "warehouse_id":int(data["warehouse_id"]),
            "buyer_name":data["buyer_name"],"buyer_phone":data["buyer_phone"],
            "buyer_address":data["buyer_address"],
            "buyer_state_id":int(data["buyer_state_id"]),
            "buyer_city_id":int(data["buyer_city_id"]),
            "packages":[{"content":data["content"],"desi":data["desi"]}]
        }
        if data["buyer_email"]:shipment["buyer_email"]=data["buyer_email"]
        self.run_request(lambda api:api.create(shipment),self.created)

    def created(self,data):
        record=data.get("shipment") or data.get("data") or data
        if isinstance(record,dict) and record.get("id"):
            self.shipment_id.setText(str(record["id"]))

    def list_shipments(self):
        self.run_request(lambda api:api.shipments())

    def get_detail(self):
        try:sid=self.sid()
        except ValueError as exc:QMessageBox.warning(self,"Kargonomi",str(exc));return
        self.run_request(lambda api:api.detail(sid))

    def get_prices(self):
        try:sid=self.sid()
        except ValueError as exc:QMessageBox.warning(self,"Kargonomi",str(exc));return
        self.run_request(lambda api:api.prices(sid),self.show_providers)

    def show_providers(self,data):
        self.provider.clear()
        for provider in data.get("shipping_provider_with_price",[]):
            self.provider.addItem(
                f"{provider.get('name','Kargo')} · {provider.get('price') or 'Otomatik'}",
                provider.get("id"))
        if not self.provider.count():
            self.provider.addItem("Fiyat teklifi bulunamadı",None)

    def confirm_shipping(self):
        try:sid=self.sid()
        except ValueError as exc:QMessageBox.warning(self,"Kargonomi",str(exc));return
        provider_id=self.provider.currentData()
        if provider_id is None:
            QMessageBox.warning(self,"Kargonomi","Önce fiyat teklifini ve kargo firmasını seçiniz.");return
        if QMessageBox.question(self,"Kargo firması onayı",
                "Bu işlem gönderiyi işleme hazır hale getirir ve ücret doğurabilir. Onaylıyor musunuz?"
                )!=QMessageBox.StandardButton.Yes:
            return
        self.run_request(lambda api:api.confirm(sid,provider_id))

    def get_barcode(self):
        try:sid=self.sid()
        except ValueError as exc:QMessageBox.warning(self,"Kargonomi",str(exc));return
        def save(data):
            payload=data.get("barcode") or data.get("data") or data.get("pdf")
            if isinstance(payload,dict):
                payload=payload.get("barcode") or payload.get("content") or payload.get("pdf")
            if not isinstance(payload,str):
                QMessageBox.warning(self,"Kargonomi","Barkod PDF verisi yanıtta bulunamadı.");return
            try:
                pdf=base64.b64decode(payload.split(",")[-1],validate=True)
                if not pdf.startswith(b"%PDF"):
                    raise ValueError("PDF imzası yok")
            except Exception:
                QMessageBox.warning(self,"Kargonomi","Barkod yanıtı PDF formatında değil.");return
            target,_=QFileDialog.getSaveFileName(self,"Barkod PDF kaydet",f"Kargonomi_{sid}.pdf","PDF (*.pdf)")
            if target:Path(target).write_bytes(pdf)
        self.run_request(lambda api:api.barcode(sid),save)
