"""Actual Windows PySide6 GUI smoke, offline, using an isolated empty data dir."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

class OfflineWorkstation:
    paired=False
    token=None

@unittest.skipUnless(sys.platform=='win32', 'Qt Windows smoke is run in GitHub Actions windows-2022')
class WindowsGuiTests(unittest.TestCase):
    def test_main_navigation_and_workflow_widgets(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_gui_ci_') as temporary:
            os.environ['ALFA_ERP_DATA_DIR']=temporary
            from PySide6.QtWidgets import QApplication
            from main import AlfaMain
            app=QApplication.instance() or QApplication(['alfa-ci'])
            with patch('main.Workstation',OfflineWorkstation):
                window=AlfaMain(admin_cloud=None)
            try:
                self.assertEqual(window.stack.count(),5)
                self.assertGreater(len(window.db.katalog),0)
                self.assertIsNotNone(window.orders)
                self.assertIsNotNone(window.inventory)
                self.assertIsNotNone(window.analytics)
                for index in (0,1,2,3,4):
                    window.navigate(index)
                    app.processEvents()
                    self.assertEqual(window.stack.currentIndex(),index)
            finally:
                window.close()
                app.processEvents()

    def test_owner_device_and_major_minor_log_follow_all_three_themes(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_owner_ui_ci_') as temporary:
            os.environ['ALFA_ERP_DATA_DIR']=temporary
            from PySide6.QtWidgets import QApplication,QTableWidget
            from main import AlfaMain
            from yonetici_gunluk import make_audit_entries
            app=QApplication.instance() or QApplication(['alfa-owner-ui-ci'])
            with patch('main.OWNER_EDITION',True), patch('main.Workstation',OfflineWorkstation):
                window=AlfaMain(admin_cloud=None)
            try:
                panel=window.settings_page
                self.assertEqual(len(panel.nav),5)
                self.assertIsInstance(panel.device_table,QTableWidget)
                self.assertEqual(panel.device_table.objectName(),'OwnerDeviceTable')
                fake={'device_activity':[
                    {'created_at':'2026-11-04T13:00:00Z','device_name':'Personel 1',
                     'action':'progress','order_ids':['x'],
                     'details':{'events':[{'book_code':'443','print_type':'SB',
                       'delta_ready':1,'delta_boxed':0}]}},
                    {'created_at':'2026-11-04T13:01:00Z','device_name':'Personel 2',
                     'action':'transition','order_ids':['y'],
                     'details':{'events':[{'from_status':'havuz','to_status':'aktif'}]}}
                ],'audit_events':[]}
                events=make_audit_entries(fake,[])
                self.assertEqual(len(events),2)
                self.assertEqual({e['level'] for e in events},{'major','minor'})
                panel.audit_feed.set_entries(fake,[])
                panel.audit_feed.set_filter('major')
                self.assertTrue(panel.audit_feed.filters['major'].isChecked())
                for theme,expected in (
                    ('acik','#fffaf3'),('kontrast','#91adcb'),('koyu','#1c3045')):
                    panel.set_theme(theme)
                    self.assertIn(expected,panel.styleSheet())
                    app.processEvents()
            finally:
                window.close()
                app.processEvents()

    def test_staff_edition_hides_admin_tools(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_staff_ci_') as temporary:
            os.environ['ALFA_ERP_DATA_DIR']=temporary
            from PySide6.QtWidgets import QApplication
            from main import AlfaMain
            app=QApplication.instance() or QApplication(['alfa-staff-ci'])
            with patch('main.OWNER_EDITION',False), patch('main.Workstation',OfflineWorkstation):
                window=AlfaMain(admin_cloud=None)
                try:
                    self.assertEqual(window.stack.count(),5)
                    self.assertEqual(len(window.settings_page.nav),2)
                    self.assertFalse(window._analytics_unlocked)
                    window.navigate(3)
                    app.processEvents()
                    self.assertEqual(window.stack.currentIndex(),3)
                finally:
                    window.close()
                    app.processEvents()

if __name__ == '__main__': unittest.main()
