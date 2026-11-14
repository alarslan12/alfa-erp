"""Private shipping PDF workflow: fake client, no production access."""
import copy
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from alfa_rtdb import DeviceError, Workstation
from kargo_etiketi import encode_pdf, decode_pdf, label_ready, MAX_LABEL_BYTES
from rtdb_kargo_etiketi import upload_label, download_label


class FakeClient:
    def __init__(self):
        self.uid = 'owner-ci'
        self.role = 'owner'
        self.order_id = str(uuid.uuid4())
        self.row = {'id': self.order_id, 'platform':'Açık Adres / Manuel',
                    'shipping_reference':'CI address', 'status':'aktif',
                    'version':1, 'items':{'x':{'quantity':1, 'boxed_count':1}}}
        self.files = {}

    def _get(self, path):
        if path.startswith('members/'):
            return {'active':True, 'role':self.role}
        if path == 'orders/' + self.order_id:
            return copy.deepcopy(self.row)
        raise AssertionError(path)

    def _request(self, method, path, body=None, **kwargs):
        if method == 'PUT':
            self.files[path] = copy.deepcopy(body)
        elif method == 'DELETE':
            self.files.pop(path, None)
        elif method == 'GET':
            return copy.deepcopy(self.files.get(path)), None, 200
        else:
            raise AssertionError(method)
        return None, None, 200

    def _atomic_order(self, order_id, mutate):
        assert order_id == self.order_id
        row, result = mutate(copy.deepcopy(self.row))
        if row is not None:
            self.row = row
        return result

    transition = Workstation.transition
    _apply_events = Workstation._apply_events


class ShippingLabelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root / 'label.pdf'
        self.pdf.write_bytes(b'%PDF-1.4\n%%EOF\n')
        self.client = FakeClient()
        self.args = (self.client, self.client.order_id, 'CI address')

    def test_owner_upload_then_staff_download_and_replace(self):
        c = self.client
        label = upload_label(*self.args, self.pdf)
        self.assertFalse(label_ready(c.row))
        self.assertNotIn('payload', c.row['shipping_label'])
        dest = self.root / 'saved.pdf'
        download_label(*self.args, dest)
        self.assertFalse(label_ready(c.row))  # owner's own download not accepted
        c.role, c.uid = 'staff', 'staff-ci'
        self.assertTrue(download_label(*self.args, dest)['acknowledged'])
        self.assertEqual(dest.read_bytes(), self.pdf.read_bytes())
        self.assertTrue(label_ready(c.row))
        self.assertEqual(c.row['shipping_label_receipt']['downloaded_by'], 'staff-ci')
        c.role, c.uid = 'owner', 'owner-ci'
        next_label = upload_label(*self.args, self.pdf)
        self.assertNotEqual(label['revision'], next_label['revision'])
        self.assertFalse(label_ready(c.row))
        self.assertEqual(len(c.files), 1)

    def test_failed_save_and_unauthorized_upload(self):
        upload_label(*self.args, self.pdf)
        self.client.role, self.client.uid = 'staff', 'staff-ci'
        with self.assertRaises(DeviceError):
            upload_label(*self.args, self.pdf)
        with self.assertRaises(OSError):
            download_label(*self.args, self.root / 'no-parent' / 'missing.pdf')
        self.assertFalse(label_ready(self.client.row))

    def test_completion_requires_current_acknowledgement(self):
        c = self.client
        event = {'order_id':c.order_id, 'op_id':str(uuid.uuid4()),
                 'from_status':'aktif', 'to_status':'tamamlandi', 'shipping_fee':70}
        with self.assertRaises(DeviceError):
            c.transition([event])
        upload_label(*self.args, self.pdf)
        with self.assertRaises(DeviceError):
            c.transition([event])
        c.role, c.uid = 'staff', 'staff-ci'
        download_label(*self.args, self.root / 'saved.pdf')
        c.transition([event])
        self.assertEqual(c.row['status'], 'tamamlandi')

    def test_other_platform_unchanged_and_changed_address_rejected(self):
        self.assertTrue(label_ready({'platform':'Dolap'}))
        self.assertTrue(label_ready({'platform':'Gardrops'}))
        self.assertFalse(label_ready({'platform':'Açık Adres / Manuel'}))
        with self.assertRaises(DeviceError):
            upload_label(self.client, self.client.order_id, 'wrong address', self.pdf)

    def test_file_validation(self):
        encoded = encode_pdf(self.pdf)
        self.assertEqual(decode_pdf(encoded, encoded), self.pdf.read_bytes())
        corrupted = dict(encoded, sha256='0'*64)
        with self.assertRaises(ValueError):
            decode_pdf(corrupted, encoded)
        self.pdf.write_bytes(b'%PDF-' + b'0'*MAX_LABEL_BYTES)
        with self.assertRaises(ValueError):
            encode_pdf(self.pdf)


if __name__ == '__main__':
    unittest.main()
