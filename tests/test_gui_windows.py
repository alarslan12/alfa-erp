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
                # Navigation to Analytics must ask for a server PIN.
                # Mock the dialog explicitly: a real modal has no user in CI.
                for index in (0,1,3,4):
                    window.navigate(index)
                    app.processEvents()
                    self.assertEqual(window.stack.currentIndex(),index)
                from PySide6.QtWidgets import QDialog
                with patch('analytics_access.AnalyticsGate.exec',
                           return_value=QDialog.DialogCode.Rejected) as prompt:
                    window.navigate(2)
                    self.assertNotEqual(window.stack.currentIndex(),2)
                    prompt.assert_called_once()
                with patch('analytics_access.AnalyticsGate.exec',
                           return_value=QDialog.DialogCode.Accepted) as prompt:
                    window.navigate(2)
                    app.processEvents()
                    self.assertEqual(window.stack.currentIndex(),2)
                    self.assertTrue(window._analytics_unlocked)
                    prompt.assert_called_once()
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

    def test_general_product_catalog_and_stock_screen_are_separate(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_master_ci_') as temporary:
            os.environ['ALFA_ERP_DATA_DIR']=temporary
            from PySide6.QtWidgets import QApplication
            from main import AlfaMain
            app=QApplication.instance() or QApplication(['alfa-master-ci'])
            with patch('main.OWNER_EDITION',True), patch('main.Workstation',OfflineWorkstation):
                window=AlfaMain(admin_cloud=None)
            try:
                self.assertEqual(window.stack.count(),5)
                self.assertEqual(window.catalog_view.count(),2)
                window.db.owner_admin_request=lambda *_args,**_kwargs:{'id':'demo'}
                window.db.inventory_products=[
                    {'id':'catalog-only','sku':'A-001','title':'Ürün kataloğu kaydı',
                     'category':'Genel','active':True,'in_inventory':False,
                     'quantity':0,'sale_price':120,'cost_price':70,'tags':[]},
                    {'id':'in-stock','sku':'B-002','title':'Stoklu ürün',
                     'category':'Genel','active':True,'in_inventory':True,
                     'quantity':4,'sale_price':145,'cost_price':85,'tags':[]}]
                window.general_catalog.refresh()
                window.inventory.refresh()
                self.assertEqual(window.general_catalog.table.rowCount(),2)
                self.assertEqual(window.inventory.scope.itemText(0),'Tüm envanter')
                self.assertEqual(window.inventory.add_button.text(),
                                 '＋  Katalogdan envantere ekle')
                self.assertIn('1 ürün',window.inventory.summary.text())
                window.select_catalog(1)
                self.assertEqual(window.catalog_view.currentIndex(),1)
                self.assertTrue(window.catalog.toolbar.isHidden())
                window.select_catalog(0)
                self.assertEqual(window.catalog_view.currentIndex(),0)
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
