"""Admin-issued one-time pairing code, no staff email or password."""
import sys,os,socket,subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLabel,QLineEdit,QPushButton,QMessageBox,QDialog
from alfa_cihaz import api,save_token,get_token,DeviceError
ROOT=Path(__file__).resolve().parent
def pythonw():
    p=ROOT/'.venv'/'Scripts'/'pythonw.exe'
    if p.exists():return p
    alt=Path(sys.executable).with_name('pythonw.exe')
    return alt if alt.exists() else Path(sys.executable)
def enable_startup():
    """Kullanıcı oturumu başladığında tray agent çalıştır; admin hakkı gerekmez."""
    if os.name!='nt':raise DeviceError('Bildirim başlangıcı Windows gerektirir.')
    folder=Path(os.environ['APPDATA'])/'Microsoft'/'Windows'/'Start Menu'/'Programs'/'Startup'
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/'ALFA ERP Bildirim.lnk'
    ps=lambda value: str(value).replace("'","''")
    script=("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('"+ps(target)+"');"+
            "$s.TargetPath='"+ps(pythonw())+"';"+
            "$s.Arguments='\""+str(ROOT/'bildirim_servisi.py').replace("'","''")+"\"';"+
            "$s.WorkingDirectory='"+ps(ROOT)+"';$s.Description='ALFA ERP Bildirim Servisi';$s.Save()")
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],check=True,
                   creationflags=0x08000000)
    subprocess.Popen([str(pythonw()),str(ROOT/'bildirim_servisi.py')],creationflags=0x08000000)
class PairDialog(QDialog):
    """Pair a freshly installed generic staff app without rebuilding Setup.exe."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('ALFA ERP · İlk cihaz eşleştirmesi')
        self.setMinimumWidth(460)
        self.setModal(True)
        col=QVBoxLayout(self);col.setSpacing(11)
        introduction=QLabel(
            'Bu bilgisayar henüz bulut sistemine eşleştirilmemiş.\\n'
            'Yönetici uygulamasında Ayarlar → Bilgisayarlar → Yeni cihaz kodu '
            'seçeneğinden tek kullanımlık kod oluşturup buraya girin.')
        introduction.setWordWrap(True);col.addWidget(introduction)
        col.addWidget(QLabel('Bilgisayar adı'))
        self.computer=QLineEdit(socket.gethostname()[:120])
        col.addWidget(self.computer)
        col.addWidget(QLabel('Tek kullanımlık 48 karakterli cihaz kodu'))
        self.code=QLineEdit()
        self.code.setPlaceholderText('Yöneticiden alınan tek kullanımlık kod')
        col.addWidget(self.code)
        self.message=QLabel('')
        self.message.setWordWrap(True);col.addWidget(self.message)
        row=QVBoxLayout()
        self.confirm=QPushButton('Bu bilgisayarı eşleştir ve ALFA ERP\'yi aç')
        self.confirm.clicked.connect(self.pair_now)
        row.addWidget(self.confirm)
        cancel=QPushButton('Vazgeç')
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel);col.addLayout(row)

    def pair_now(self):
        code=self.code.text().strip().replace(' ','').upper()
        if len(code)!=48 or any(c not in '0123456789ABCDEF' for c in code):
            self.message.setText('Lütfen yöneticinin oluşturduğu 48 karakterli kodu girin.')
            return
        self.confirm.setEnabled(False)
        try:
            reply=api('pair',code=code,device_name=self.computer.text().strip()[:120])
            save_token(reply['device_token'])
            self.code.clear()
            self.accept()
        except Exception as exc:
            self.message.setText('Cihaz eşleştirilemedi: '+str(exc)[:200])
        finally:
            self.confirm.setEnabled(True)

class Pair(QWidget):
    def __init__(self):
        super().__init__();self.resize(480,260);self.setWindowTitle('ALFA ERP · Cihaz Eşleştirme')
        lay=QVBoxLayout(self);lay.addWidget(QLabel('Yönetici Paneli ile oluşturulan kodu girin. Personel parolası gerekmiyor.'))
        self.name=QLineEdit(socket.gethostname()[:120]);self.code=QLineEdit()
        self.code.setPlaceholderText('48 karakterlik tek kullanımlık kod')
        lay.addWidget(QLabel('Bilgisayar adı'));lay.addWidget(self.name)
        lay.addWidget(QLabel('Eşleştirme kodu'));lay.addWidget(self.code)
        lay.addWidget(QLabel('Cihaz önceden eşleşmiş.' if get_token() else 'Cihaz eşleştirilmemiş.'))
        btn=QPushButton('Cihazı eşleştir ve bildirimleri aç');btn.clicked.connect(self.run_pair);lay.addWidget(btn)
    def run_pair(self):
        try:
            value=api('pair',code=self.code.text().strip(),device_name=self.name.text().strip())
            save_token(value['device_token']);enable_startup()
            QMessageBox.information(self,'Tamamlandı','Cihaz kaydedildi. Windows bildirimleri açıldı. ERP’yi yeniden başlatın.')
            self.close()
        except Exception as exc:QMessageBox.warning(self,'Cihaz eşleştirme',str(exc))
def main():
    app=QApplication(sys.argv);win=Pair();win.show();return app.exec()
if __name__=='__main__':sys.exit(main())
