"""Owner login is Supabase Auth + workspace admin role, never a local hardcoded password."""
import socket
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QLineEdit,QPushButton
from alfa_bulut import AlfaCloud
from alfa_cihaz import Workstation,api,save_token,get_token


def admin_request(cloud,action,**kwargs):
    cloud._renew_if_needed()
    if not cloud.logged_in:raise RuntimeError('Yönetici oturumu kapandı. Yeniden giriş yapın.')
    return api(action,admin_jwt=cloud._session['access_token'],
               timeout=90 if action=='admin_catalog' else 25,**kwargs)


class AdminWorkstation(Workstation):
    def __init__(self,cloud,token):
        super().__init__(token);self.cloud=cloud
    def commit(self,edits):
        return admin_request(self.cloud,'admin_import',edits=edits)['results']


class AdminLogin(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.cloud=None
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

    def check_connection(self):
        self.diagnostic_button.setEnabled(False)
        try:
            AlfaCloud().health()
            self.message.setText(
                'Supabase Auth sunucusuna HTTPS bağlantısı başarılı. '
                'Yönetici hesabınla yeniden giriş yapabilirsin.')
        except Exception as exc:
            self.message.setText('Bağlantı tanısı: '+str(exc)[:260])
        finally:
            self.diagnostic_button.setEnabled(True)

    def authenticate(self):
        self.button.setEnabled(False)
        try:
            cloud=AlfaCloud()
            cloud.sign_in(self.email.text(),self.password.text())
            # One authenticated server request checks workspace admin role.
            # The old read_status() issued four separate table reads at login;
            # any transient timeout incorrectly looked like invalid credentials.
            status=admin_request(cloud,'admin_status')
            if not status.get('access') or status.get('role')!='admin':
                raise RuntimeError('Bu hesap ALFA ERP yöneticisi değil.')
            self.password.clear()
            if not get_token():
                # Owner uses a one-time device credential, saved with Windows DPAPI.
                code=admin_request(cloud,'admin_code')['code']
                paired=api('pair',code=code,device_name=socket.gethostname()[:120])
                save_token(paired['device_token'])
            self.cloud=cloud
            self.accept()
        except Exception as exc:
            self.message.setText('Giriş başarısız: '+str(exc)[:260])
        finally:
            self.button.setEnabled(True)
