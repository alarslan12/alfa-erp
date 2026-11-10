"""Kargonomi REST integration. Token stays in memory, never in repository or logs."""
import base64
import json
import os
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import keyring

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QPlainTextEdit, QVBoxLayout, QWidget
)

BASE = "https://app.kargonomi.com.tr/api/v1"
CREDENTIAL_SERVICE="ALFACOPYCENTER.Kargonomi"
CREDENTIAL_USER="api-token"
CONFIG_DIR=Path(os.environ.get("ALFA_ERP_DATA_DIR") or
    Path(os.environ.get("LOCALAPPDATA",str(Path.home()))) / "AlfaERP")
CONFIG_FILE=CONFIG_DIR / "kargonomi_settings.json"

def saved_token():
    env=os.getenv("KARGONOMI_API_TOKEN","").strip()
    if env:return env
    try:return keyring.get_password(CREDENTIAL_SERVICE,CREDENTIAL_USER) or ""
    except Exception:return ""

def save_token(value):
    if not value.strip():raise ValueError("Boş API anahtarı kaydedilemez.")
    keyring.set_password(CREDENTIAL_SERVICE,CREDENTIAL_USER,value.strip())

def warehouse_id():
    env=os.getenv("KARGONOMI_WAREHOUSE_ID","")
    if env.isdecimal() and int(env)>0:return int(env)
    try:
        data=json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return int(data.get("warehouse_id") or 0)
    except (OSError,ValueError,TypeError):return 0

def save_warehouse_id(number):
    number=int(number)
    if number<=0:raise ValueError("Geçerli depo ID gerekli.")
    CONFIG_DIR.mkdir(parents=True,exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({"warehouse_id":number}),encoding="utf-8")



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
                if not raw:
                    return {}
                try:
                    return json.loads(raw.decode("utf-8"))
                except (ValueError,UnicodeDecodeError):
                    return raw.decode("utf-8",errors="replace")
        except HTTPError as exc:
            # API may return buyer details or credentials in error payload; do not log body.
            raise RuntimeError(f"Kargonomi HTTP {exc.code}; alanları ve API yetkisini kontrol edin.") from None
        except (URLError, TimeoutError) as exc:
            raise RuntimeError("Kargonomi bağlantısı kurulamadı; ağ erişimini kontrol edin.") from None

    def states(self):
        return self.request("GET", "/states/1")

    def cities(self, state_id):
        return self.request("GET", f"/cities/{int(state_id)}")

    def credit(self):
        return self.request("GET", "/user/credit")

    def shipments(self):
        return self.request("GET", "/shipments")

    def create(self, shipment):
        return self.request("POST", "/shipments", {"shipment": shipment})

    def detail(self, shipment_id):
        return self.request("GET", f"/shipments/{int(shipment_id)}")

    def prices(self, shipment_id):
        return self.request("GET", f"/shipment-price-comparison/{int(shipment_id)}")

    def confirm(self, shipment_id, provider_id):
        # Use multipart/form-data as documented by Kargonomi (--form).
        boundary="AlfaKargonomi"+uuid.uuid4().hex
        parts=[]
        for key,value in (("shipment_id",shipment_id),("shipping_provider_id",provider_id)):
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{int(value)}\r\n"
                .encode("utf-8")
            )
        body=b"".join(parts)+f"--{boundary}--\r\n".encode("utf-8")
        request=Request(BASE+"/confirm-shipping-price",data=body,
                        headers={"Authorization":"Bearer "+self.token,
                                 "Accept":"application/json",
                                 "Content-Type":f"multipart/form-data; boundary={boundary}"},
                        method="POST")
        try:
            with urlopen(request,timeout=18) as response:
                raw=response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except HTTPError as exc:
            raise RuntimeError(f"Kargo firması onayı başarısız: HTTP {exc.code}") from None
        except (URLError,TimeoutError):
            raise RuntimeError("Kargo firması onayında ağ hatası.") from None

    def cancel(self, shipment_id):
        return self.request("POST","/shipments/cancel",{"shipment_id":int(shipment_id)})

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
    """Kargonomi account setup and shipment lookup; order-specific shipping occurs in completion flow."""
    def __init__(self,database,parent=None):
        super().__init__(parent)
        self.db=database
        self.worker=None
        self.setWindowTitle("ALFA ERP · Kargonomi Yönetimi")
        self.resize(690,570)
        root=QVBoxLayout(self)
        root.addWidget(QLabel("Kargonomi bağlantısı · Bir defa ayarla, sonrasında otomatik kullan."))
        settings=QFormLayout()
        self.token=QLineEdit(saved_token())
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText("Kargonomi API Bearer Token")
        settings.addRow("API anahtarı",self.token)
        self.warehouse=QLineEdit(str(warehouse_id() or ""))
        self.warehouse.setPlaceholderText("Kargonomi gönderici depo ID")
        settings.addRow("Depo ID",self.warehouse)
        save=QPushButton("Bağlantıyı Windows kimlik kasasında sakla")
        save.clicked.connect(self.save_settings)
        settings.addRow("",save)
        root.addLayout(settings)
        root.addWidget(QLabel("Sipariş seçimi / mevcut gönderinin kontrolü"))
        self.orders=QComboBox()
        self.orders.addItem("Sipariş seçiniz",None)
        for order in database.siparisler:
            self.orders.addItem(f"#{order.get('id')} · {str(order.get('kod',''))[:55]}",order.get("id"))
        self.orders.currentIndexChanged.connect(self.select_order)
        root.addWidget(self.orders)
        row=QHBoxLayout()
        self.shipment_id=QLineEdit()
        self.shipment_id.setPlaceholderText("Kargonomi gönderi ID")
        row.addWidget(self.shipment_id)
        root.addLayout(row)
        actions=QHBoxLayout()
        self.actions=[]
        for name,callback in (
            ("Gönderiler",self.list_shipments),
            ("Gönderi detayı",self.get_detail),
            ("Fiyat teklifleri",self.get_prices),
            ("Bakiye",self.get_credit),
            ("Yeni Barkod PDF",self.get_barcode),
            ("İptal talebi",self.cancel_shipment),
        ):
            button=QPushButton(name)
            button.clicked.connect(callback)
            actions.addWidget(button)
            self.actions.append(button)
        root.addLayout(actions)
        self.output=QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText(
            "Sipariş tamamlamada desi sorulur, kargo teklifi seçilir ve Yeni Barkod otomatik açılır.\n"
            "Bu ekranda mevcut gönderileri takip edebilirsiniz.")
        root.addWidget(self.output)

    def save_settings(self):
        try:
            token=self.token.text().strip()
            if token:save_token(token)
            if self.warehouse.text().strip():save_warehouse_id(self.warehouse.text().strip())
            if not saved_token() or not warehouse_id():
                raise ValueError("API anahtarı ve depo ID gerekli.")
        except Exception as exc:
            QMessageBox.warning(self,"Kargonomi","Bağlantı kaydedilemedi: "+str(exc))
            return
        QMessageBox.information(self,"Kargonomi",
            "API anahtarı Windows kimlik kasasına, depo kimliği yerel ayarlara kalıcı kaydedildi. Tekrar girmen gerekmeyecek.")

    def select_order(self):
        sid=self.orders.currentData()
        order=next((o for o in self.db.siparisler if str(o.get("id"))==str(sid)),None)
        self.shipment_id.setText(str(order.get("kargonomi_shipment_id") or "") if order else "")

    def sid(self):
        value=self.shipment_id.text().strip()
        if not value.isdigit() or int(value)<=0:
            raise ValueError("Önce geçerli bir Kargonomi gönderi ID seçin.")
        return int(value)

    def client(self):
        token=self.token.text().strip() or saved_token()
        return KargonomiClient(token)

    def request(self,action,on_success=None):
        if self.worker is not None and self.worker.isRunning():
            return
        try:api=self.client()
        except ValueError as exc:
            QMessageBox.warning(self,"Kargonomi",str(exc))
            return
        for btn in self.actions:btn.setEnabled(False)
        self.output.setPlainText("Kargonomi yanıtı alınıyor…")
        self.worker=ApiWorker(lambda:action(api),self)
        def success(data):
            for btn in self.actions:btn.setEnabled(True)
            if on_success:
                try:on_success(data)
                except Exception as exc:
                    QMessageBox.warning(self,"Kargonomi",str(exc))
            self.output.setPlainText(json.dumps(data,ensure_ascii=False,indent=2)[:20000])
        def failed(message):
            for btn in self.actions:btn.setEnabled(True)
            self.output.setPlainText(message)
        self.worker.done.connect(success)
        self.worker.failed.connect(failed)
        self.worker.start()

    def list_shipments(self):
        self.request(lambda api:api.shipments())

    def get_detail(self):
        try:sid=self.sid()
        except ValueError as exc:QMessageBox.warning(self,"Kargonomi",str(exc));return
        self.request(lambda api:api.detail(sid))

    def get_prices(self):
        try:sid=self.sid()
        except ValueError as exc:QMessageBox.warning(self,"Kargonomi",str(exc));return
        self.request(lambda api:api.prices(sid))

    def get_credit(self):
        self.request(lambda api:api.credit())

    def get_barcode(self):
        try:sid=self.sid()
        except ValueError as exc:QMessageBox.warning(self,"Kargonomi",str(exc));return
        def save(data):
            from kargonomi_akisi import decode_barcode
            pdf=decode_barcode(data)
            target,_=QFileDialog.getSaveFileName(self,"Yeni Barkod PDF",
                    f"Yeni_Barkod_{sid}.pdf","PDF (*.pdf)")
            if target:Path(target).write_bytes(pdf)
        self.request(lambda api:api.barcode(sid),save)

    def cancel_shipment(self):
        try:sid=self.sid()
        except ValueError as exc:QMessageBox.warning(self,"Kargonomi",str(exc));return
        if QMessageBox.question(self,"Kargonomi · İptal talebi",
                f"#{sid} gönderisi için Kargonomi'ye iptal talebi gönderilsin mi?"
                )!=QMessageBox.StandardButton.Yes:return
        self.request(lambda api:api.cancel(sid))

    def closeEvent(self,event):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self,"Kargonomi","İşlem tamamlanmadan pencereyi kapatmayın.")
            event.ignore()
            return
        super().closeEvent(event)
