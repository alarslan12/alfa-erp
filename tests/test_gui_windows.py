"""Windows GUI smoke checks against the Firebase desktop edition."""
import os, sys, tempfile, unittest
from unittest.mock import patch

class OfflineWorkstation:
    paired=False
    token=None
    uid=None

@unittest.skipUnless(sys.platform=='win32','Native GUI checks run on Windows CI')
class WindowsGuiTests(unittest.TestCase):
    def test_staff_edition_opens_without_network_or_login(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_firebase_staff_') as data:
            os.environ['ALFA_ERP_DATA_DIR']=data
            from PySide6.QtWidgets import QApplication
            from main import AlfaMain
            app=QApplication.instance() or QApplication(['alfa-staff-ci'])
            with patch('main.OWNER_EDITION',False), \
                 patch('main.Workstation',OfflineWorkstation):
                win=AlfaMain(admin_cloud=None)
                try:
                    self.assertEqual(win.stack.count(),5)
                    self.assertGreater(len(win.db.katalog),0)
                    self.assertEqual(win.inventory_view.count(),2)
                    self.assertTrue(win.db.cloud_required)
                    self.assertFalse(win.device.paired)
                    win.navigate(3)
                    app.processEvents()
                    self.assertEqual(win.stack.currentIndex(),3)
                finally:
                    win.close()
                    app.processEvents()

    def test_owner_edition_opens_without_backend_calls(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_firebase_owner_') as data:
            os.environ['ALFA_ERP_DATA_DIR']=data
            from PySide6.QtWidgets import QApplication
            from main import AlfaMain
            app=QApplication.instance() or QApplication(['alfa-owner-ci'])
            with patch('main.OWNER_EDITION',True), \
                 patch('main.Workstation',OfflineWorkstation):
                win=AlfaMain(admin_cloud=None)
                try:
                    self.assertEqual(win.stack.count(),5)
                    self.assertIsNotNone(win.settings_page)
                    self.assertTrue(callable(win.db.owner_admin_request))
                    app.processEvents()
                finally:
                    win.close()
                    app.processEvents()

if __name__=='__main__':
    unittest.main()
