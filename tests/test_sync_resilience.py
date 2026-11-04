"""Resilient desktop sync regression checks. No real Supabase requests."""
import unittest
from PySide6.QtCore import QCoreApplication
from bulut_canli import Pull, Sync


class FakeWorkstation:
    paired = False
    def sync(self, known=None, **_kwargs):
        return {'epoch':'current','orders_revision':101,
                'catalog_revision':4,'inventory_revision':2,
                'orders':[], 'items':[]} if known is None or known.get('orders_revision') == -1 else {
                'epoch':'current','orders_revision':101,
                'catalog_revision':4,'inventory_revision':2
                }


class FakeDB:
    pending_count = 0


class SyncResilienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(['alfa-ci-sync'])

    def setUp(self):
        self.sync = Sync(FakeWorkstation(), FakeDB())
        self.sync.last_pulse={'epoch':'current','orders_revision':101,
                              'catalog_revision':4,'inventory_revision':2}
        self.sync.force_pull=False
        self.sync._last_orders_verified=100.0

    def test_unmodified_revisions_skip_large_data(self):
        known,initial=self.sync._revision_request(now=110.0)
        self.assertFalse(initial)
        self.assertEqual(known['orders_revision'],101)
        self.assertEqual(known['catalog_revision'],4)
        self.assertEqual(self.sync.last_pulse['orders_revision'],101)

    def test_auto_reconcile_orders_after_five_minutes(self):
        known,initial=self.sync._revision_request(now=401.0)
        self.assertFalse(initial)
        self.assertEqual(known['orders_revision'],-1)
        self.assertEqual(known['catalog_revision'],4)
        self.assertEqual(known['inventory_revision'],2)
        self.assertEqual(self.sync.last_pulse['orders_revision'],101)

    def test_after_successful_push_force_a_new_authoritative_pull(self):
        self.sync.force_pull=True
        known,initial=self.sync._revision_request(now=101.0)
        self.assertFalse(initial)
        self.assertEqual(known['orders_revision'],-1)

    def test_initial_sync_downloads_everything_once(self):
        self.sync.last_pulse=None
        known,initial=self.sync._revision_request(now=101.0)
        self.assertTrue(initial)
        self.assertIsNone(known)

    def test_one_round_trip_pull_respects_order_revision(self):
        client=FakeWorkstation()
        result=[]
        worker=Pull(client,last={
            'epoch':'current','orders_revision':-1,
            'catalog_revision':4,'inventory_revision':2
        },force=False)
        worker.done.connect(result.append)
        worker.run()
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['pulse']['orders_revision'],101)
        self.assertEqual(result[0]['snapshot']['orders'],[])


if __name__ == '__main__':
    unittest.main()
