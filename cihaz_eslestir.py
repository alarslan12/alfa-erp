"""Admin-issued one-time pairing code, no staff email or password."""
import sys,os,socket,subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLabel,QLineEdit,QPushButton,QMessageBox
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
