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

    def test_owner_login_uses_background_worker_and_direct_rls_access(self):
        from yonetici_giris import AdminLogin
        cloud=MagicMock()
        cloud.logged_in=True
        cloud.verify_owner_access.return_value={'access':True,'role':'admin'}
        cloud._session={'access_token':'test.jwt'}
        form=AdminLogin()
        form.email.setText('operator@example.invalid')
        form.password.setText('dummy-password-not-saved')
        with patch('yonetici_giris.AlfaCloud',return_value=cloud), \
             patch('yonetici_giris.admin_request') as edge:
            form.authenticate()
            self.assertFalse(form.button.isEnabled())
            self.assertEqual(form.password.text(),'')
            self.assertTrue(form._login_worker.wait(5000))
            self.app.processEvents()
            cloud.sign_in.assert_called_once()
            cloud.verify_owner_access.assert_called_once()
            cloud.read_status.assert_not_called()
            edge.assert_not_called()
            self.assertEqual(form.result(),QDialog.DialogCode.Accepted)

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
