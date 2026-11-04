"""ALFA ERP staff-only Windows entry point for native Setup.exe builds."""
import sys,traceback
from PySide6.QtWidgets import QApplication,QMessageBox
from auto_eslestir import main as enroll
from main import start as start_erp

def main():
    try:
        enroll(install_startup=False)
    except Exception as exc:
        app=QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None,'ALFA ERP · Kurulum / Cihaz Yetkisi',
            'Cihaz eşleştirmesi başarısız oldu. İnternet bağlantısını ve kurulum biletini kontrol edin.\n\n'+str(exc)[:400])
        return 1
    return start_erp()

if __name__=='__main__':
    if '--self-test' in sys.argv:
        from main import release_smoke_test
        sys.exit(release_smoke_test())
    sys.exit(main())
