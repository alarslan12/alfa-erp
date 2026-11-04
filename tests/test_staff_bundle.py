"""One-time enrollment bundle can be created without any PyInstaller rebuild."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from personel_paketi import create_staff_installer_bundle

class StaffBundleTests(unittest.TestCase):
    def test_generic_setup_plus_per_device_ticket(self):
        with tempfile.TemporaryDirectory(prefix='alfa_ticket_ci_') as root:
            folder=Path(root)
            setup=folder/'ALFA_ERP_Personel_Setup_V6_1_2.exe'
            setup.write_bytes(b'MZ_fake_windows_binary_for_archive_test')
            archive=folder/'YeniPersonel.zip'
            create_staff_installer_bundle(archive,setup,'AB'*24)
            with zipfile.ZipFile(archive) as zipped:
                self.assertIn(setup.name,zipped.namelist())
                self.assertEqual(json.loads(zipped.read('kurulum_bilgisi.json'))['enrollment_code'],'AB'*24)
                self.assertIn('KURULUM.txt',zipped.namelist())

    def test_rejects_invalid_enrollment_token(self):
        with tempfile.TemporaryDirectory() as root:
            setup=Path(root)/'setup.exe';setup.write_bytes(b'MZ')
            with self.assertRaises(ValueError):
                create_staff_installer_bundle(Path(root)/'bad.zip',setup,'not-a-token')

if __name__ == '__main__':unittest.main()
