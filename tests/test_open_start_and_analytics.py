"""Firebase startup and analytics checks without a live connection."""
import inspect, os, unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication


class StartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication(['alfa-splash-ci'])

    def test_splash_reports_only_checks_performed(self):
        from ekran_baslangic import StartupSplash
        splash=StartupSplash(owner=False,version='1.1.2')
        splash.show()
        self.app.processEvents()
        self.assertEqual(splash.progress.value(),0)
        splash.update_step('storage','Disk available')
        splash.update_step('device','Awaiting Firebase approval',warning=True)
        self.assertEqual(splash.progress.value(),2)
        self.assertEqual(splash._labels['device'][0].text(),'!')
        splash.close()

    def test_startup_is_nonblocking_and_uses_firebase(self):
        import main
        from ekran_baslangic import launch_with_splash
        source=inspect.getsource(main.start)
        self.assertIn('launch_with_splash',source)
        self.assertIn('AlfaMain(admin_cloud=None)',source)
        launch=inspect.getsource(launch_with_splash)
        self.assertIn('cloud_timeout',launch)
        self.assertIn('QTimer.singleShot(6000',launch)
        self.assertNotIn('Supabase',launch)

    def test_analytics_staff_is_ui_gate_not_server_authorization(self):
        from analytics_access import AnalyticsGate
        gate=AnalyticsGate(owner=False)
        self.assertIsNone(gate.set_button)
        self.assertEqual(gate.mode,'verify')
        gate.close()
        owner=AnalyticsGate(owner=True)
        self.assertIsNotNone(owner.set_button)
        owner.switch_mode()
        self.assertEqual(owner.mode,'set')
        owner.close()

    def test_cloud_activation_uses_firebase_device_pairing(self):
        from main import AlfaMain
        source=inspect.getsource(AlfaMain.connect_cloud)
        self.assertIn('firebase_pair_ui',source)
        self.assertIn('self.device',source)
        self.assertNotIn('AdminLogin',source)


if __name__=='__main__':
    unittest.main()
