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


@unittest.skipUnless(sys.platform=='win32','Native Qt start smoke on Windows runner')
class FreshStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication(['alfa-open-win-ci'])

    def _open(self,owner):
        from main import AlfaMain
        temp=tempfile.TemporaryDirectory(prefix='alfa_clean_ci_')
        os.environ['ALFA_ERP_DATA_DIR']=temp.name
        with patch('main.OWNER_EDITION',owner), \
             patch('main.Workstation',OfflineWorkstation), \
             patch('yonetici_giris.AdminLogin') as login:
            window=AlfaMain(admin_cloud=None)
            login.assert_not_called()
        return temp,window

    def test_owner_opens_offline_without_supabase_login_dialog(self):
        temp,window=self._open(True)
        try:
            self.assertEqual(window.stack.count(),5)
            self.assertFalse(window._analytics_unlocked)
            self.assertTrue(window.cloud_connect.isEnabled())
            self.assertIn('bağlı değil',window.cloud_badge.text())
            self.assertTrue(callable(window.db.owner_admin_request))
        finally:
            window.live.timer.stop()
            window.live.sender.stop()
            window.close()
            temp.cleanup()

    def test_staff_opens_offline_without_code_entry_popup(self):
        temp,window=self._open(False)
        try:
            self.assertEqual(window.stack.count(),5)
            self.assertFalse(window._analytics_unlocked)
            self.assertTrue(window.cloud_connect.isEnabled())
            self.assertIn('bağlı değil',window.cloud_badge.text())
            self.assertFalse(callable(getattr(window.db,'owner_admin_request',None)))
        finally:
            window.live.timer.stop()
            window.live.sender.stop()
            window.close()
            temp.cleanup()


if __name__=='__main__':
    unittest.main()
