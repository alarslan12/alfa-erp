"""Firebase pairing and authorization boundaries; no real network or secrets."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from alfa_rtdb import Workstation, DeviceError


class FirebasePairingTests(unittest.TestCase):
    def test_new_device_gets_identity_but_no_owner_role(self):
        answer={'localId':'test-uid','refreshToken':'refresh-sample',
                'idToken':'access-sample','expiresIn':'3600'}
        with patch('alfa_rtdb.load_identity',return_value=None), \
             patch('alfa_rtdb.save_identity') as persist, \
             patch('alfa_rtdb._http_json',return_value=(answer,None,200)), \
             patch.object(Workstation,'_request',return_value=(None,None,200)) as put:
            device=Workstation()
            self.assertFalse(device.paired)
            uid=device.enroll_anonymous('Offline Tester')
            self.assertEqual(uid,'test-uid')
            self.assertTrue(device.paired)
            persist.assert_called_once()
            args=put.call_args.args
            self.assertEqual(args[0],'PUT')
            self.assertIn('device_requests/test-uid',args[1])
            self.assertNotIn('role',args[2])

    def test_dpapi_session_names_are_edition_scoped(self):
        import cihaz_sifreleme
        from alfa_rtdb import _session_path
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(cihaz_sifreleme,'DATA',Path(temporary)), \
                 patch.object(cihaz_sifreleme,'OWNER_APP',False):
                self.assertEqual(_session_path().name,'firebase_staff_session.bin')
            with patch.object(cihaz_sifreleme,'DATA',Path(temporary)), \
                 patch.object(cihaz_sifreleme,'OWNER_APP',True):
                self.assertEqual(_session_path().name,'firebase_owner_session.bin')

    def test_rules_are_private_by_default_and_owner_gated(self):
        rules=json.loads((Path(__file__).resolve().parents[1]/
                         'firebase/database.rules.json').read_text('utf-8'))['rules']
        self.assertFalse(rules['.read'])
        self.assertFalse(rules['.write'])
        space=rules['alfa']['$workspace']
        self.assertIn("owner",space['members']['$uid']['.write'])
        self.assertIn("auth.uid",space['device_requests']['$uid']['.write'])
        self.assertIn("data.val()+1",space['meta']['revisions']['$kind']['.write'])
        self.assertIn("newData.exists()",space['orders']['$id']['.write'])

    def test_owner_actions_do_not_use_stored_app_passwords(self):
        from pathlib import Path
        installer=(Path(__file__).resolve().parents[1]/'ALFACOPYCENTER_Suite.iss').read_text('utf-8')
        self.assertNotIn('OwnerPasswordValid',installer)
        self.assertNotIn('GetSHA256OfString',installer)
        self.assertIn('Firebase',installer)


if __name__=='__main__':
    unittest.main()
