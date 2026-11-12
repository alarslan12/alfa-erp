"""Firebase-only regression tests. No network and no production writes."""
import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError,URLError
import io

from alfa_rtdb import DeviceError, Workstation, _http_json


class FirebaseProtocolTests(unittest.TestCase):
    def test_rtdb_conflict_is_not_an_internet_outage(self):
        ex=HTTPError('https://example.invalid',412,'Precondition Failed',{},
                     io.BytesIO(b'{"error":"conflict"}'))
        with patch('alfa_rtdb.urllib.request.urlopen',side_effect=ex):
            with self.assertRaises(DeviceError) as result:
                _http_json('https://example.invalid')
        self.assertEqual(result.exception.status,409)
        self.assertTrue(result.exception.permanent)

    def test_temporary_firebase_unavailable_is_retryable(self):
        ex=HTTPError('https://example.invalid',503,'Unavailable',{},
                     io.BytesIO(b'{}'))
        with patch('alfa_rtdb.urllib.request.urlopen',side_effect=ex):
            with self.assertRaises(DeviceError) as result:
                _http_json('https://example.invalid')
        self.assertEqual(result.exception.status,503)
        self.assertFalse(result.exception.permanent)

    def test_firebase_permission_denial_is_not_a_revoked_token(self):
        ex=HTTPError('https://example.invalid',401,'Unauthorized',{},
                     io.BytesIO(b'{"error":"Permission denied"}'))
        with patch('alfa_rtdb.urllib.request.urlopen',side_effect=ex):
            with self.assertRaises(DeviceError) as result:
                _http_json('https://example.invalid')
        self.assertEqual(result.exception.status,403)

    def test_network_failure_does_not_expose_credentials(self):
        with patch('alfa_rtdb.urllib.request.urlopen',side_effect=URLError('DNS failed')):
            with self.assertRaises(DeviceError) as result:
                _http_json('https://example.invalid/secret?auth=SENSITIVE')
        self.assertIsNone(result.exception.status)
        self.assertNotIn('SENSITIVE',str(result.exception))

    def test_notification_reads_headers_only(self):
        from bildirim_servisi import Reader
        class FakeClient:
            def sync(self,**kwargs):
                self.kwargs=kwargs
                return {'epoch':'live','orders_revision':12,'catalog_revision':4,
                        'inventory_revision':3,
                        'orders_brief':[{'id':'order','order_number':35}]}
        client=FakeClient()
        worker=Reader(client,{'epoch':'live','orders_revision':11},34)
        received=[]
        worker.done.connect(received.append)
        worker.run()
        self.assertEqual(received[0]['orders'][0]['order_number'],35)
        self.assertTrue(client.kwargs['notification'])
        self.assertEqual(client.kwargs['last_order_number'],34)


if __name__=='__main__':
    unittest.main()
