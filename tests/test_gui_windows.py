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
                    # Exercise the real analytics widget after a successful
                    # PIN gate, including viewport resizing and report rebuild.
                    win._analytics_unlocked=True
                    win.navigate(2)
                    app.processEvents()
                    win.analytics.resize(1075,850)
                    app.processEvents()
                    win.analytics.refresh()
                    app.processEvents()
                    self.assertEqual(win.stack.currentIndex(),2)
                finally:
                    win.close()
                    app.processEvents()

    def test_order_tabs_detach_and_return_without_losing_page(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_tab_ui_') as data:
            os.environ['ALFA_ERP_DATA_DIR']=data
            from pathlib import Path
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QPoint, Qt
            from database import ERPDatabase
            from widgets import Covers
            from editor_siparis import SiparisTakipSekmeleri
            root=Path(__file__).resolve().parents[1]
            app=QApplication.instance() or QApplication(['alfa-tab-ci'])
            db=ERPDatabase(root/'KİTAPS.xlsx',data_dir=data)
            code=next(iter(db.katalog))
            created=db.yeni_siparis_olustur(
                {'kod':'test-001','platform':'Manuel','ciro':50,'siparis_turu':''},
                [{'kod':code,'tur':'SB','adet':2,'hazir':0,'koli':0}])
            hub=SiparisTakipSekmeleri(db,Covers(db,root),lambda:None)
            try:
                hub.add_order(created['id'])
                hub.show()
                app.processEvents()
                self.assertEqual(hub.tabs.count(),1)
                page=hub.tabs.widget(0)
                self.assertIsNotNone(page)
                hub.detach_order(0,QPoint(30,30))
                app.processEvents()
                self.assertEqual(hub.tabs.count(),0)
                self.assertIn(str(created['id']),hub.detached)
                hub.reattach_order(created['id'])
                app.processEvents()
                self.assertEqual(hub.tabs.count(),1)
                self.assertIs(hub.tabs.widget(0),page)
                self.assertFalse(hub.detached)
            finally:
                hub.close()
                app.processEvents()

    def test_order_track_filter_chooses_unboxed_books(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_unboxed_') as data:
            os.environ['ALFA_ERP_DATA_DIR']=data
            from pathlib import Path
            from PySide6.QtWidgets import QApplication
            from database import ERPDatabase
            from widgets import Covers
            from editor_siparis import SiparisEditor
            root=Path(__file__).resolve().parents[1]
            app=QApplication.instance() or QApplication(['alfa-filter-ci'])
            db=ERPDatabase(root/'KİTAPS.xlsx',data_dir=data)
            code=next(iter(db.katalog))
            order=db.yeni_siparis_olustur(
                {'kod':'test-002','platform':'Manuel','ciro':50,'siparis_turu':''},
                [{'kod':code,'tur':'SB','adet':1,'hazir':0,'koli':0}])
            db.siparis_durumunu_degistir(order,'aktif')
            editor=SiparisEditor(db,Covers(db,root),order['id'],lambda:None,
                                 mode='track',embedded=True)
            try:
                self.assertEqual(editor._visible_track_codes(),(code,))
                editor.only_unboxed.setChecked(True)
                app.processEvents()
                self.assertEqual(editor._visible_track_codes(),(code,))
                editor.only_unprepared.setChecked(True)
                app.processEvents()
                self.assertFalse(editor.only_unboxed.isChecked())
                self.assertTrue(editor.only_unprepared.isChecked())
            finally:
                editor.close()
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
