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
