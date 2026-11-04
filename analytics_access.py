"""Server-verified Analytics PIN. No plaintext PIN or verifier in Windows setup.

Staff may verify the owner-defined PIN, but cannot create or modify it.
Wrong attempts are limited per enrolled device by Supabase Edge Function.
"""
from PySide6.QtCore import Qt,QThread,Signal
from PySide6.QtWidgets import (
    QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton
)
from alfa_cihaz import api,get_token


class PINWorker(QThread):
    succeeded=Signal()
    failed=Signal(str)
    def __init__(self,mode,pin,token,parent=None):
        super().__init__(parent)
        self.mode,self.pin,self.token=mode,pin,token
    def run(self):
        try:
            action='admin_analytics_pin_set' if self.mode=='set' else 'analytics_verify'
            result=api(action,token=self.token,pin=self.pin,timeout=16)
            if action=='analytics_verify' and not result.get('verified'):
                raise RuntimeError('Analitik PIN doğrulanamadı')
            self.succeeded.emit()
        except Exception as exc:
            self.failed.emit(str(exc)[:230])
        finally:
            self.pin=''


class AnalyticsGate(QDialog):
    """Only this section asks for a password; standard ERP opens without one."""
    def __init__(self,owner=False,parent=None):
        super().__init__(parent)
        self.owner=bool(owner)
        self.mode='verify'
        self._worker=None
        self.setWindowTitle('ALFA ERP · Analitik PIN')
        self.setMinimumWidth(410)
        root=QVBoxLayout(self)
        root.setSpacing(11)
        self.heading=QLabel('Analitik ekranına erişim')
        self.heading.setStyleSheet('font-weight:800;font-size:16px')
        root.addWidget(self.heading)
        self.hint=QLabel(
            'Yöneticinin belirlediği 6–12 haneli PIN kodunu girin. '
            'İşlem yalnızca eşleştirilmiş bilgisayarda doğrulanır.')
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)
        self.pin=QLineEdit()
        self.pin.setPlaceholderText('Analitik PIN')
        self.pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin.setMaxLength(12)
        self.pin.returnPressed.connect(self.submit)
        root.addWidget(self.pin)
        self.confirm=QLineEdit()
        self.confirm.setPlaceholderText('Yeni PIN tekrarı')
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm.setMaxLength(12)
        self.confirm.hide()
        root.addWidget(self.confirm)
        self.note=QLabel('')
        self.note.setWordWrap(True)
        root.addWidget(self.note)
        controls=QHBoxLayout()
        self.button=QPushButton('Analitik ekranını aç')
        self.button.clicked.connect(self.submit)
        controls.addWidget(self.button)
        cancel=QPushButton('Vazgeç')
        cancel.clicked.connect(self.reject)
        controls.addWidget(cancel)
        root.addLayout(controls)
        if self.owner:
            self.set_button=QPushButton('Yönetici: PIN oluştur veya değiştir')
            self.set_button.clicked.connect(self.switch_mode)
            root.addWidget(self.set_button)
        else:
            self.set_button=None

    def switch_mode(self):
        self.mode='set' if self.mode=='verify' else 'verify'
        setting=self.mode=='set'
        self.confirm.setVisible(setting)
        self.heading.setText('Analitik PIN belirle' if setting else 'Analitik ekranına erişim')
        self.button.setText('PIN kaydet ve Analitik aç' if setting else 'Analitik ekranını aç')
        self.note.clear()
        self.pin.clear()
        self.confirm.clear()
        self.pin.setFocus()

    def submit(self):
        if self._worker and self._worker.isRunning():
            return
        token=get_token()
        if not token:
            self.note.setText(
                'Bulut cihazı eşleştirilmemiş. Önce üst çubuktan Buluta bağla seçin.')
            return
        pin=self.pin.text().strip()
        if not pin.isascii() or not pin.isdigit() or not 6<=len(pin)<=12:
            self.note.setText('PIN yalnızca 6–12 rakam olmalıdır.')
            return
        if self.mode=='set' and pin!=self.confirm.text():
            self.note.setText('Yeni PIN ve tekrarı aynı olmalı.')
            return
        self.button.setEnabled(False)
        if self.set_button:self.set_button.setEnabled(False)
        self.note.setText('PIN güvenli sunucuda kontrol ediliyor…')
        worker=PINWorker(self.mode,pin,token,self)
        self._worker=worker
        self.pin.clear()
        self.confirm.clear()
        result={'ok':False,'error':None}
        worker.succeeded.connect(lambda:result.__setitem__('ok',True))
        worker.failed.connect(lambda error:result.__setitem__('error',error))
        def finished():
            self._worker=None
            self.button.setEnabled(True)
            if self.set_button:self.set_button.setEnabled(True)
            if result['ok']:
                self.accept()
            else:
                self.note.setText(str(result['error'] or 'PIN kontrolü tamamlanamadı'))
        worker.finished.connect(finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def reject(self):
        if self._worker and self._worker.isRunning():
            self.note.setText('PIN kontrolü tamamlanıyor…')
            return
        super().reject()
