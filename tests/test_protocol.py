"""Network protocol and error classification without production requests."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from alfa_cihaz import api, DeviceError

class ProtocolTests(unittest.TestCase):
    def test_conflict_is_not_labeled_as_offline(self):
        error = HTTPError('https://example.invalid',409,'Conflict',{},
                          io.BytesIO(b'{"error":"Version conflict"}'))
        with patch('alfa_cihaz.urllib.request.urlopen', side_effect=error):
            with self.assertRaises(DeviceError) as ctx:
                api('progress','A'*64,events=[])
        self.assertEqual(ctx.exception.status,409)
        self.assertTrue(ctx.exception.permanent)
        self.assertIn('Version conflict',str(ctx.exception))

    def test_sync_requests_revisions_in_one_call_without_separate_pulse(self):
        from alfa_cihaz import Workstation
        revisions={'epoch':'a','orders_revision':11,
                   'catalog_revision':8,'inventory_revision':4}
        with patch('alfa_cihaz.api',return_value={'epoch':'a'}) as request:
            workstation=Workstation(token='C'*64)
            self.assertEqual(workstation.sync(known=revisions),{'epoch':'a'})
            request.assert_called_once_with('sync','C'*64,timeout=20,
                known=revisions)

    def test_tray_uses_order_headers_not_large_snapshot(self):
        from bildirim_servisi import Reader
        class FakeClient:
            def sync(self,**kwargs):
                self.kwargs=kwargs
                return {'epoch':'a','orders_revision':12,
                   'catalog_revision':8,'inventory_revision':4,
                   'orders_brief':[{'id':'new-order','order_number':35}]}
            def pulse(self):raise AssertionError('Unnecessary HTTP pulse')
            def snapshot(self):raise AssertionError('Unnecessary large snapshot')
        client=FakeClient()
        worker=Reader(client,{'epoch':'a','orders_revision':11},34)
        received=[]
        worker.done.connect(received.append)
        worker.run()
        self.assertEqual(len(received),1)
        self.assertEqual(received[0]['orders'][0]['order_number'],35)
        self.assertTrue(client.kwargs['notification'])
        self.assertEqual(client.kwargs['last_order_number'],34)

    def test_temporary_network_failure_is_retryable(self):
        with patch('alfa_cihaz.urllib.request.urlopen',side_effect=URLError('DNS unavailable')):
            with self.assertRaises(DeviceError) as ctx:
                api('pulse','B'*64)
        self.assertIsNone(ctx.exception.status)
        self.assertFalse(ctx.exception.permanent)
        self.assertNotIn('B'*64,str(ctx.exception))

if __name__ == '__main__': unittest.main()
