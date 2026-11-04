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

    def test_temporary_network_failure_is_retryable(self):
        with patch('alfa_cihaz.urllib.request.urlopen',side_effect=URLError('DNS unavailable')):
            with self.assertRaises(DeviceError) as ctx:
                api('pulse','B'*64)
        self.assertIsNone(ctx.exception.status)
        self.assertFalse(ctx.exception.permanent)
        self.assertNotIn('B'*64,str(ctx.exception))

if __name__ == '__main__': unittest.main()
