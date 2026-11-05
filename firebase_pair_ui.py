"""One-time Firebase RTDB device activation, with no recurring login screen."""
from __future__ import annotations
import socket
from PySide6.QtCore import QThread, Qt, Slot
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QPushButton,
                               QApplication,QInputDialog,QMessageBox)
from alfa_rtdb import Workstation,DeviceError

class Task(QThread):
    """The background function stores its result; only GUI-owned slots touch Qt."""
    def __init__(self,fn,parent=None):
        super().__init__(parent)
        self.fn=fn
        self.result=None
        self.failure=None
    def run(self):
        try:self.result=self.fn()
        except Exception as exc:self.failure=str(exc)[:260]


class PairDialog(QDialog):
    """First device registration, then trusted admin approval of the UID."""
    def __init__(self,client=None,owner=False,parent=None):
        super().__init__(parent)
        self.client=client or Workstation()
        self.owner=bool(owner)
        self._task=None
        self._workers=[]
        self._verified=False
        self._task_done=None
        self.setWindowTitle("ALFA ERP · Firebase cihaz bağlantısı")
        self.setMinimumWidth(540)
        layout=QVBoxLayout(self)
        intro=QLabel(
            "Firebase hesabı için parola girmen gerekmiyor.\n"
            "Bu bilgisayar ilk kullanımda benzersiz bir kimlik alır. "
            "Yönetici cihazı onayladıktan sonra bulut siparişleri açılır.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.identity=QLabel("Cihaz kimliği: " + (self.client.uid or "henüz oluşturulmadı"))
        self.identity.setWordWrap(True)
        self.identity.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.identity)
        self.status=QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.create=QPushButton("Cihazı kaydet / kimliği göster")
        self.create.clicked.connect(self.register)
        layout.addWidget(self.create)
        self.check=QPushButton("Yönetici onayını kontrol et")
        self.check.clicked.connect(self.check_approval)
        layout.addWidget(self.check)
        self.activate=QPushButton("Bağlantıyı başlat")
        self.activate.setEnabled(False)
        self.activate.clicked.connect(self.start_approved_connection)
        layout.addWidget(self.activate)
        if owner:
            self.approve=QPushButton("Bekleyen personel cihazını onayla")
            self.approve.clicked.connect(self.approve_staff)
            layout.addWidget(self.approve)
        close=QPushButton("Kapat")
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        if self.client.paired:
            self.status.setText(
                "Cihaz kimliği kaydedilmiş. Onay durumunu kontrol etmek için "
                "'Yönetici onayını kontrol et' düğmesine bas. "
                "Bağlantı penceresi kendiliğinden kapanmayacak.")

    def _work(self,fn,done):
        if self._task is not None:return
        worker=Task(fn,self)
        self._task=worker
        self._task_done=done
        self.create.setEnabled(False)
        self.check.setEnabled(False)
        self.activate.setEnabled(False)
        if self.owner:self.approve.setEnabled(False)
        # QObject slot with an explicitly queued connection: no UI changes
        # or dialog destruction on the network worker's thread.
        worker.finished.connect(self._work_completed,
                                Qt.ConnectionType.QueuedConnection)
        worker.start()

    @Slot()
    def _work_completed(self):
        worker=self._task
        if worker is None:return
        worker.wait()
        self._task=None
        done=self._task_done
        self._task_done=None
        self.create.setEnabled(True)
        self.check.setEnabled(True)
        if self.owner:self.approve.setEnabled(True)
        failure,result=worker.failure,worker.result
        worker.deleteLater()
        if failure is not None:
            self.status.setText(failure)
        elif done is not None:
            try:done(result)
            except Exception as exc:self.status.setText("Cihaz işlemi: "+str(exc)[:190])
        self.activate.setEnabled(self._verified)

    def start_approved_connection(self):
        if self._task is not None:return
        if not self._verified:
            self.status.setText("Önce cihaz onayını kontrol et.")
            return
        self.accept()

    def reject(self):
        if self._task is not None:
            self.status.setText("Cihaz işlemi tamamlanıyor. Pencereyi henüz kapatmayın.")
            return
        super().reject()

    def closeEvent(self,event):
        if self._task is not None:
            event.ignore()
            self.status.setText("Cihaz işlemi tamamlanıyor. Pencereyi henüz kapatmayın.")
            return
        super().closeEvent(event)

    def register(self):
        def run():
            self.client.enroll_anonymous(socket.gethostname())
            return self.client.uid
        def done(uid):
            self._verified=False
            self.activate.setEnabled(False)
            self.identity.setText("Cihaz kimliği: " + str(uid))
            self.status.setText(
                "Kimliği kopyalayabilirsin. Yönetici bu cihazı onaylayınca "
                "aşağıdaki kontrol düğmesine bas.")
        self._work(run,done)

    def check_approval(self):
        if not self.client.paired:
            self.status.setText("Önce cihaz kimliğini oluştur.")
            return
        def run():
            return self.client._get("members/"+self.client.uid)
        def done(record):
            role=str((record or {}).get("role") or "")
            self._verified=False
            if record and record.get("active") is True and role in ("owner","staff"):
                if self.owner and role!="owner":
                    self.status.setText("Bu cihaz personel rolünde; Yönetici kurulumu açılamaz.")
                    return
                self._verified=True
                self.status.setText(
                    "Cihaz onaylandı. Bulut eşitlemesini açmak için "
                    "'Bağlantıyı başlat' düğmesine bas.")
            else:
                self.status.setText(
                    "Henüz onay yok. Cihaz UID: "+str(self.client.uid)+
                    "\nYönetici uygulamasında bekleyen cihazı onayla; sonra tekrar kontrol et.")
        self._work(run,done)

    def approve_staff(self):
        if not self.client.paired:
            return
        def run():
            me=self.client._get("members/"+self.client.uid)
            if not me or me.get("role")!="owner" or not me.get("active"):
                raise DeviceError("Personel onayı için yönetici cihazı yetkisi gerekli.")
            requests=self.client._get("device_requests") or {}
            members=self.client._get("members") or {}
            return [(uid,data.get("name") or uid)
                    for uid,data in requests.items()
                    if isinstance(data,dict) and
                    not (members.get(uid) or {}).get("active")]
        def done(rows):
            if not rows:
                self.status.setText("Onay bekleyen cihaz bulunamadı.")
                return
            options=[name+"  ·  "+uid for uid,name in rows]
            selected,ok=QInputDialog.getItem(
                self,"Personel yetkilendir","Cihaz seç:",options,0,False)
            if not ok:return
            index=options.index(selected)
            target=rows[index][0]
            def approve():
                self.client._request("PUT","members/"+target,
                    {"active":True,"role":"staff","name":rows[index][1]})
                return target
            self._work(approve,lambda value:self.status.setText(
                "Personel onaylandı: "+value))
        self._work(run,done)
