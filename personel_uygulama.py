"""Compatibility entry point for the staff-only native ERP build.

The current installer builds main.py directly and uses device authorization;
the obsolete auto_enroll/setup-ticket module is no longer required.
"""
import sys
from PySide6.QtWidgets import QApplication,QMessageBox
import main as erp


def main():
    # A source/installation directory with an owner edition flag must never
    # be mistaken for a staff installation or use the owner's identity.
    if erp.OWNER_EDITION:
        app=QApplication.instance() or QApplication(sys.argv)
        QMessageBox.warning(None,'ALFA ERP Personel',
            'Bu klasör Yönetici sürümüne ait. Personel uygulamasını ortak Suite kurulumundan açın.')
        return 1
    if '--self-test' in sys.argv:
        return erp.release_smoke_test()
    return erp.start()


if __name__=='__main__':
    sys.exit(main())
