"""One-time Firebase RTDB device activation, with no recurring login screen."""
from __future__ import annotations
import socket
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QPushButton,
                               QApplication,QInputDialog,QMessageBox)
from alfa_rtdb import Workstation,DeviceError

class Task(QThread):
    done=Signal(object)
    failed=Signal(str)
    def __init__(self,fn,parent=None):
        super().__init__(parent)
        self.fn=fn
    def run(self):
        try:self.done.emit(self.fn())
        except Exception as exc:self.failed.emit(str(exc)[:260])


class PairDialog(QDialog):
    """First device registration, then trusted admin approval of the UID."""
    def __init__(self,client=None,owner=False,parent=None):
        super().__init__(parent)
        self.client=client or Workstation()
        self.owner=bool(owner)
        self._task=None
        self._workers=[]
        self._accept_pending=False
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
        if owner:
            self.approve=QPushButton("Bekleyen personel cihazını onayla")
            self.approve.clicked.connect(self.approve_staff)
            layout.addWidget(self.approve)
        close=QPushButton("Kapat")
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        if self.client.paired:
            self.check_approval()

    def _work(self,fn,done):
        if self._task and self._task.isRunning():return
        worker=Task(fn,self)
        self._task=worker
        # Keep an explicit strong reference until QThread is completely stopped.
        # Closing a dialog while its QThread is still running can abort Qt.
        self._workers.append(worker)
        self.create.setEnabled(False)
        self.check.setEnabled(False)
        worker.done.connect(done)
        worker.failed.connect(lambda message:self.status.setText(message))
        def finish():
            # The 'finished' signal can fire during Qt thread teardown.
            # wait() is immediate or near-immediate here, and guarantees that
            # destroying the dialog cannot destroy a still-running QThread.
            worker.wait()
            if self._task is worker:
                self._task=None
            self.create.setEnabled(True)
            self.check.setEnabled(True)
            if self._accept_pending:
                self._accept_pending=False
                QTimer.singleShot(0,self.accept)
            try:self._workers.remove(worker)
            except ValueError:pass
        worker.finished.connect(finish)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def reject(self):
        if any(worker.isRunning() for worker in self._workers):
            self.status.setText("Cihaz işlemi tamamlanıyor. Lütfen pencereyi henüz kapatmayın.")
            return
        super().reject()

    def register(self):
        def run():
            self.client.enroll_anonymous(socket.gethostname())
            return self.client.uid
        def done(uid):
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
            if record and record.get("active") is True and role in ("owner","staff"):
                if self.owner and role!="owner":
                    self.status.setText("Bu cihaz personel rolünde; Yönetici kurulumu açılamaz.")
                    return
                self.status.setText("Onaylandı. ALFA ERP bulut bağlantısı açılıyor.")
                self._accept_pending=True
            else:
                self.status.setText(
                    "Henüz onay yok. Cihaz UID: "+str(self.client.uid)+
                    "\nİlk yönetici yetkilendirmesi Google Cloud Shell yönetici aracıyla yapılır.")
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
