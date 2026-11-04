"""Owner login: nonblocking Supabase Auth + RLS-scoped admin verification.

Auth is separate from device pairing. An inaccessible Edge Function must
never lock the login dialog or cause valid passwords to be rejected.
"""
import socket
from PySide6.QtCore import QThread,Signal
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QLineEdit,QPushButton

from alfa_bulut import AlfaCloud
from alfa_cihaz import Workstation,api,save_token,get_token


def admin_request(cloud,action,timeout=None,**kwargs):
    """Allow an already activated owner computer without repeated user login.

    Owner-device roles are verified server-side for EACH admin action. Ordinary
    staff tokens cannot access these actions; no service key is shipped.
    """
    if timeout is None:
        timeout=90 if action=='admin_catalog' else 25
    if cloud is None:
        token=get_token()
        if not token:
            raise RuntimeError(
                'Yönetici bilgisayarını bir defa yetkilendirin: '
                'üst çubuktaki Buluta bağla düğmesini kullanın.')
        return api(action,token=token,timeout=timeout,**kwargs)
    cloud._renew_if_needed()
    if not cloud.logged_in:
        raise RuntimeError('Yönetici oturumu kapandı. Yeniden giriş yapın.')
    return api(action,admin_jwt=cloud._session['access_token'],
               timeout=timeout,**kwargs)


def pair_owner_device(cloud,timeout=10):
    """Non-GUI enrollment, invoked only in a background worker.

    The code is minted server-side for this authenticated admin, used once,
    and never persisted. The paired device token is DPAPI-encrypted locally.
    """
    code=admin_request(cloud,'admin_owner_code',timeout=timeout)['code']
    paired=api('pair',code=code,device_name=socket.gethostname()[:120],
               timeout=timeout)
    save_token(paired['device_token'])
    return paired['device_token']


class AdminWorkstation(Workstation):
    def __init__(self,cloud,token):
        super().__init__(token)
        self.cloud=cloud

    def commit(self,edits):
        return admin_request(self.cloud,'admin_import',edits=edits)['results']


class LoginWorker(QThread):
    done=Signal(object)
    failed=Signal(str)

    def __init__(self,email,password,parent=None):
        super().__init__(parent)
        self.email=email
        self.password=password

    def run(self):
        try:
            cloud=AlfaCloud()
            cloud.sign_in(self.email,self.password)
            role=cloud.verify_owner_access()
            if not role.get('access') or role.get('role')!='admin':
                raise RuntimeError('Bu hesap ALFA ERP yöneticisi değil.')
            # This is a one-time, explicitly requested OWNER activation.
            # Do not reuse an older staff-role token as if it were an owner.
            pair_owner_device(cloud,timeout=12)
            self.done.emit(cloud)
        except Exception as exc:
            self.failed.emit(str(exc)[:320])
        finally:
            self.password=''


class CheckWorker(QThread):
    done=Signal()
    failed=Signal(str)

    def run(self):
        try:
            AlfaCloud().health()
            self.done.emit()
        except Exception as exc:
            self.failed.emit(str(exc)[:320])


class AdminLogin(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.cloud=None
        self._login_worker=None
        self._check_worker=None
        self.setWindowTitle('ALFA ERP · Yönetici Girişi')
        self.setMinimumWidth(390)
        col=QVBoxLayout(self);col.setSpacing(12)
        col.addWidget(QLabel('ALFA ERP  /  YÖNETİCİ'))
        col.addWidget(QLabel('Yönetici hesabınla giriş yap; normal ERP açılacak.'))
        self.email=QLineEdit();self.email.setPlaceholderText('E-posta adresi')
        self.password=QLineEdit();self.password.setPlaceholderText('Şifre')
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        col.addWidget(self.email);col.addWidget(self.password)
        self.message=QLabel('');self.message.setWordWrap(True);col.addWidget(self.message)
        self.button=QPushButton('Yönetici olarak aç')
        self.button.clicked.connect(self.authenticate)
        col.addWidget(self.button);self.password.returnPressed.connect(self.authenticate)
        self.diagnostic_button=QPushButton('Supabase bağlantısını kontrol et')
        self.diagnostic_button.clicked.connect(self.check_connection)
        col.addWidget(self.diagnostic_button)

    def _set_busy(self,busy):
        self.button.setEnabled(not busy)
        self.diagnostic_button.setEnabled(not busy)

    def authenticate(self):
        if self._login_worker is not None and self._login_worker.isRunning():
            return
        email=self.email.text().strip()
        password=self.password.text()
        if not email or not password:
            self.message.setText('E-posta ve şifre gerekli.')
            return
        self._set_busy(True)
        self.message.setText('Hesap doğrulanıyor… Pencere kullanılabilir durumda.')
        worker=LoginWorker(email,password,self)
        self._login_worker=worker
        self.password.clear()

        # IMPORTANT: never accept/close the parent dialog on worker.done:
        # that signal fires before QThread.run has returned. Destroying a
        # parent-owned running QThread can terminate the entire application.
        pending={'cloud':None,'error':None}

        def success(cloud):
            pending['cloud']=cloud

        def failure(message):
            pending['error']=message

        def finished():
            self._login_worker=None
            self._set_busy(False)
            if pending['error']:
                self.message.setText('Giriş başarısız: '+pending['error'])
                self.password.setFocus()
            elif pending['cloud'] is not None:
                self.cloud=pending['cloud']
                self.message.setText('')
                self.accept()
            else:
                self.message.setText('Giriş tamamlanmadı. Yeniden deneyin.')

        worker.done.connect(success)
        worker.failed.connect(failure)
        worker.finished.connect(finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def check_connection(self):
        if self._check_worker is not None and self._check_worker.isRunning():
            return
        self._set_busy(True)
        self.message.setText('Supabase HTTPS erişimi kontrol ediliyor…')
        worker=CheckWorker(self)
        self._check_worker=worker

        def success():
            self._set_busy(False)
            self.message.setText('Supabase Auth sunucusuna HTTPS bağlantısı başarılı.')

        def failure(message):
            self._set_busy(False)
            self.message.setText('Bağlantı tanısı: '+message)

        worker.done.connect(success)
        worker.failed.connect(failure)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def reject(self):
        if ((self._login_worker is not None and self._login_worker.isRunning()) or
            (self._check_worker is not None and self._check_worker.isRunning())):
            self.message.setText('Ağ kontrolü tamamlanıyor…')
            return
        super().reject()
