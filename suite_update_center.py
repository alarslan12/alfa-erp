"""Suite update center for Print Center (shared GitHub v2 release channel)."""
import json
import os
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from guncelleme_arayuzu import UpdateDialog
from alfa_guncelleme import launch_update,UpdateError


def pending_erp_actions(data_directory):
    """Fail closed on unreadable queue; never discard data to update apps."""
    path=Path(data_directory)/'alfa_outbox.json'
    if not path.exists():
        return 0
    try:
        outbox=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(outbox,dict):
            return -1
        return sum(len(outbox.get(k) or []) for k in
                   ('edits','progress','status_events'))
    except (OSError,ValueError,TypeError):
        return -1


class PrintSuiteUpdateDialog(UpdateDialog):
    def __init__(self,parent=None):
        data=Path(os.environ.get('ALFA_ERP_DATA_DIR') or
                  Path(os.environ.get('LOCALAPPDATA') or Path.home())/'AlfaERP')
        super().__init__('2.0.21','print',data,parent)
        self.setWindowTitle('ALFACOPYCENTER Suite · Güncelleme Merkezi')
        self.message.setText('Print Center · Suite 2.0.21')

    def install_now(self):
        if not self.verified:
            return
        pending=pending_erp_actions(self.storage)
        if pending:
            detail=('Kuyruk dosyası okunamadı; veri kaybını önlemek için durduruldu.'
                    if pending<0 else '%d ERP işlemi Firebase eşitlemesi bekliyor.'%pending)
            QMessageBox.warning(self,'Suite güncellemesi',detail)
            return
        parent=self.parentWidget()
        yes=QMessageBox.question(self,'Suite güncellemesi',
            'Suite bileşenleri güncellenecek. Aktif baskıları tamamlayın ve açık '
            'ERP/Banner pencerelerini kaydedin. Kurulum sihirbazı açılacak; '
            'önceki seçilen bileşenler korunacak. Devam edilsin mi?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if yes!=QMessageBox.StandardButton.Yes:
            return
        try:
            launch_update(self.verified,self.storage,sys.executable,pending=0)
        except (UpdateError,OSError,RuntimeError) as exc:
            QMessageBox.warning(self,'Güncelleme başlatılamadı',str(exc))
            return
        self.accept()
        def close_current():
            if parent is not None and not parent.close():
                QMessageBox.warning(parent,'Güncelleme',
                                    'Print Center kapanamadı; kurulumu yeniden başlatın.')
                return
            QApplication.instance().quit()
        QTimer.singleShot(0,close_current)
