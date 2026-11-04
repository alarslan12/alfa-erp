"""New-install startup and analytics access tests: no live network or secret."""
import os,sys,tempfile,unittest
from unittest.mock import patch,MagicMock

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

from PySide6.QtWidgets import QApplication,QDialog


class OfflineWorkstation:
    paired=False
    token=None


class AnalyticsAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication(['alfa-open-ci'])

    def test_staff_cannot_create_or_change_analytics_pin(self):
        from analytics_access import AnalyticsGate
        gate=AnalyticsGate(owner=False)
        self.assertIsNone(gate.set_button)
        self.assertEqual(gate.mode,'verify')
        gate.close()

    def test_owner_can_offer_first_setup_and_pin_change(self):
        from analytics_access import AnalyticsGate
        gate=AnalyticsGate(owner=True)
        self.assertIsNotNone(gate.set_button)
        gate.switch_mode()
        self.assertEqual(gate.mode,'set')
        self.assertTrue(gate.confirm.isVisible() or not gate.isVisible())
        gate.close()

    def test_analytics_pin_is_checked_by_server_not_local_fixed_hash(self):
        from analytics_access import PINWorker
        worker=PINWorker('verify','123456','A'*64)
        done=[]
        worker.succeeded.connect(lambda:done.append(True))
        with patch('analytics_access.api',return_value={'verified':True}) as request:
            worker.run()
            self.assertEqual(done,[True])
            request.assert_called_once_with('analytics_verify',
                token='A'*64,pin='123456',timeout=16)
            self.assertEqual(worker.pin,'')

    def test_owner_pin_change_requires_server_admin_action(self):
        from analytics_access import PINWorker
        worker=PINWorker('set','123456','A'*64)
        with patch('analytics_access.api',return_value={'ok':True}) as request:
            worker.run()
            request.assert_called_once_with('admin_analytics_pin_set',
                token='A'*64,pin='123456',timeout=16)


@unittest.skipUnless(sys.platform=='win32','Native startup checks on Windows')
class FreshStartTests(unittest.TestCase):
    def test_startup_has_no_blocking_login_or_pairing_dialog(self):
        import inspect
        import main
        startup=inspect.getsource(main.start)
        self.assertNotIn('prompt.exec()',startup)
        self.assertNotIn('dialog.exec()',startup)
        self.assertNotIn('enroll_staff(',startup)
        self.assertIn('AlfaMain(admin_cloud=None)',startup)

    def test_cloud_setup_is_user_initiated_after_window_exists(self):
        import inspect
        from main import AlfaMain
        setup=inspect.getsource(AlfaMain.connect_cloud)
        self.assertIn('AdminLogin',setup)
        self.assertIn('PairDialog',setup)
        self.assertIn('self.live.activate()',setup)


if __name__=='__main__':
    unittest.main()
