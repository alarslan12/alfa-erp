"""Windows GUI regression checks for owner sign-in and generic staff enrollment.

All network access, secrets and file persistence are mocked.
"""
import os
import socket
import unittest
from unittest.mock import patch,MagicMock

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

from PySide6.QtWidgets import QApplication,QDialog

class EnrollmentAndLoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication(['alfa-enrollment-ci'])

    def test_generic_staff_installer_can_pair_without_ticket(self):
        from cihaz_eslestir import PairDialog
        modal=PairDialog()
        self.assertIn('cihaz',modal.windowTitle().lower())
        modal.code.setText('A'*48)
        mock_reply={'device_token':'C'*64}
        with patch('cihaz_eslestir.api',return_value=mock_reply) as request,patch('cihaz_eslestir.save_token') as save:
            modal.pair_now()
            request.assert_called_once()
            self.assertEqual(request.call_args.args[:1],('pair',))
            self.assertEqual(request.call_args.kwargs['code'],'A'*48)
            save.assert_called_once_with('C'*64)
            self.assertEqual(modal.result(),QDialog.DialogCode.Accepted)

    def test_private_reinstall_ticket_replaces_stale_device_credential(self):
        import json,tempfile
        from pathlib import Path
        from auto_eslestir import main as pair_from_ticket
        with tempfile.TemporaryDirectory(prefix='alfa_ticket_ci_') as folder:
            path=Path(folder)/'kurulum_bilgisi.json'
            path.write_text(json.dumps({
                'enrollment_code':'D'*48,'replace_existing':True
            }),encoding='utf-8')
            with patch('auto_eslestir.ROOT',Path(folder)), \
                 patch('auto_eslestir.get_token',return_value='A'*64), \
                 patch('auto_eslestir.api',
                       return_value={'device_token':'C'*64}) as gateway, \
                 patch('auto_eslestir.save_token') as saved:
                pair_from_ticket(install_startup=False)
                gateway.assert_called_once()
                self.assertEqual(gateway.call_args.kwargs['code'],'D'*48)
                saved.assert_called_once_with('C'*64)
                self.assertFalse(path.exists())

    def test_invalid_pairing_code_must_not_call_network(self):
        from cihaz_eslestir import PairDialog
        modal=PairDialog()
        modal.code.setText('123')
        with patch('cihaz_eslestir.api') as network:
            modal.pair_now()
            network.assert_not_called()
            self.assertNotEqual(modal.result(),QDialog.DialogCode.Accepted)
            self.assertIn('48',modal.message.text())
        modal.close()

    def test_owner_login_worker_uses_direct_rls_access(self):
        from yonetici_giris import LoginWorker
        cloud=MagicMock()
        cloud.verify_owner_access.return_value={'access':True,'role':'admin'}
        worker=LoginWorker('operator@example.invalid','dummy-password')
        messages=[]
        worker.done.connect(messages.append)
        with patch('yonetici_giris.AlfaCloud',return_value=cloud), \
             patch('yonetici_giris.pair_owner_device',return_value='A'*64) as activated:
            # Run worker logic deterministically without creating a native
            # Windows Qt thread in the unit-test runner.
            worker.run()
            cloud.sign_in.assert_called_once()
            cloud.verify_owner_access.assert_not_called()
            cloud.read_status.assert_not_called()
            activated.assert_called_once_with(cloud,timeout=12)
            self.assertEqual(messages,[cloud])
            self.assertEqual(worker.password,'')

    def test_authenticated_owner_setup_mints_owner_code_not_staff_code(self):
        from yonetici_giris import pair_owner_device
        cloud=MagicMock()
        with patch('yonetici_giris.admin_request',
                   return_value={'code':'A'*48}) as request, \
             patch('yonetici_giris.api',
                   return_value={'device_token':'B'*64}) as paired, \
             patch('yonetici_giris.save_token') as save:
            self.assertEqual(pair_owner_device(cloud,timeout=9),'B'*64)
            request.assert_called_once_with(cloud,'admin_owner_code',timeout=9)
            paired.assert_called_once()
            self.assertEqual(paired.call_args.args[0],'pair')
            save.assert_called_once_with('B'*64)

    def test_admin_action_uses_only_owner_device_credential_when_paired(self):
        from yonetici_giris import admin_request
        with patch('yonetici_giris.get_token',return_value='F'*64), \
             patch('yonetici_giris.api',return_value={'ok':True}) as request:
            result=admin_request(None,'admin_devices')
            self.assertTrue(result['ok'])
            request.assert_called_once_with(
                'admin_devices',token='F'*64,timeout=25)

    def test_login_form_starts_worker_without_network_on_gui_thread(self):
        from yonetici_giris import AdminLogin,LoginWorker
        form=AdminLogin()
        form.email.setText('operator@example.invalid')
        form.password.setText('dummy-password')
        with patch.object(LoginWorker,'start') as start:
            form.authenticate()
            start.assert_called_once()
            self.assertFalse(form.button.isEnabled())
            self.assertEqual(form.password.text(),'')
        # No real thread was started, so reject safely.
        form._login_worker=None
        form.reject()

    def test_rls_admin_verification_is_small_and_fails_closed(self):
        from alfa_bulut import AlfaCloud,CloudError
        cloud=AlfaCloud()
        with patch.object(cloud,'get',side_effect=[
            [{'id':'workspace-test'}],
            [{'role':'admin','active':True}]
        ]) as getter:
            result=cloud.verify_owner_access()
            self.assertTrue(result['access'])
            self.assertEqual(getter.call_count,2)
            self.assertIn('workspace_members',getter.call_args.args[0])
        with patch.object(cloud,'get',side_effect=[
            [{'id':'workspace-test'}],
            [{'role':'viewer','active':True}]
        ]):
            with self.assertRaises(CloudError):
                cloud.verify_owner_access()

    def test_owner_connection_check_is_nonblocking(self):
        from yonetici_giris import AdminLogin
        cloud=MagicMock()
        form=AdminLogin()
        with patch('yonetici_giris.AlfaCloud',return_value=cloud):
            form.check_connection()
            self.assertFalse(form.diagnostic_button.isEnabled())
            self.assertTrue(form._check_worker.wait(5000))
            self.app.processEvents()
            cloud.health.assert_called_once()
            cloud.sign_in.assert_not_called()
            self.assertIn('başarılı',form.message.text().lower())
        form.close()


if __name__ == '__main__':
    unittest.main()
