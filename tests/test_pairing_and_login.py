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

    def test_owner_login_only_checks_admin_status_not_four_public_tables(self):
        from yonetici_giris import AdminLogin
        cloud=MagicMock()
        cloud.logged_in=True
        cloud._session={'access_token':'test.jwt'}
        form=AdminLogin()
        form.email.setText('operator@example.invalid')
        form.password.setText('dummy-password-not-saved')
        with patch('yonetici_giris.AlfaCloud',return_value=cloud), \
             patch('yonetici_giris.admin_request',return_value={'access':True,'role':'admin'}) as call, \
             patch('yonetici_giris.get_token',return_value='C'*64):
            form.authenticate()
            cloud.sign_in.assert_called_once()
            cloud.read_status.assert_not_called()
            call.assert_called_once_with(cloud,'admin_status')
            self.assertEqual(form.result(),QDialog.DialogCode.Accepted)
            self.assertEqual(form.password.text(),'')

    def test_owner_connection_check_does_not_require_password(self):
        from yonetici_giris import AdminLogin
        cloud=MagicMock()
        form=AdminLogin()
        with patch('yonetici_giris.AlfaCloud',return_value=cloud):
            form.check_connection()
            cloud.health.assert_called_once()
            cloud.sign_in.assert_not_called()
            self.assertIn('başarılı',form.message.text().lower())
        form.close()


if __name__ == '__main__':
    unittest.main()
