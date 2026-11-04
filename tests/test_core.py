"""ALFA ERP offline regression checks; never touches production Supabase."""
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='alfa_ci_')
        self.addCleanup(self.tmp.cleanup)
        from database import ERPDatabase
        self.db = ERPDatabase(ROOT / 'KİTAPS.xlsx', data_dir=self.tmp.name)
        self.assertGreater(len(self.db.katalog), 0)
        self.book = next(iter(self.db.katalog))

    def new_order(self, connected=False):
        if connected:
            # No network calls allowed: even when attached to a cloud client,
            # writes must be durable local queue operations.
            class BombCloud:
                def __getattr__(self, name):
                    raise AssertionError('Unexpected network access on main thread: ' + name)
            self.db.cloud_api = BombCloud()
            self.db.cloud_epoch = str(uuid.uuid4())
        return self.db.yeni_siparis_olustur(
            {'kod':'CI-TEST', 'platform':'Manuel', 'ciro':75, 'siparis_turu':''},
            [{'kod':self.book, 'tur':'SB', 'adet':3, 'hazir':0, 'koli':0}])

    def test_local_order_lifecycle_and_persistence(self):
        order = self.new_order()
        self.assertEqual(order['id'], 1)
        self.db.siparis_durumunu_degistir(order, 'aktif')
        self.db.siparis_ilerleme_degistir(order, self.book, 'SB', 3, 2)
        self.assertRaises(ValueError, self.db.siparis_durumunu_degistir, order, 'tamamlandi')
        self.db.siparis_ilerleme_degistir(order, self.book, 'SB', 3, 3)
        self.db.siparis_durumunu_degistir(order, 'tamamlandi')
        self.assertEqual(self.db.siparis_durumu(order), 'tamamlandi')
        from database import ERPDatabase
        reopened = ERPDatabase(ROOT / 'KİTAPS.xlsx', data_dir=self.tmp.name)
        self.assertEqual(reopened.siparisler[0]['id'], 1)
        self.assertEqual(reopened.siparis_durumu(reopened.siparisler[0]), 'tamamlandi')

    def test_cloud_queue_dependency_order_and_ack(self):
        order = self.new_order(connected=True)
        self.assertEqual(self.db.pending_count, 1)
        batch = self.db.next_outbox_batch()
        self.assertEqual(batch['kind'], 'commit')
        self.db.confirm_outbox(batch, [{
            'local_id':str(order['id']), 'uuid':str(uuid.uuid4()),
            'version':1, 'order_number':1}])
        self.assertEqual(self.db.pending_count, 0)
        self.db.siparis_durumunu_degistir(order, 'aktif')
        self.db.siparis_ilerleme_degistir(order, self.book, 'SB', 1, 0)
        self.db.siparis_ilerleme_degistir(order, self.book, 'SB', 2, 1)
        first = self.db.next_outbox_batch()
        self.assertEqual(first['kind'], 'status')
        self.assertEqual(first['events'][0]['from_status'], 'havuz')
        self.assertEqual(first['events'][0]['to_status'], 'aktif')
        self.db.confirm_outbox(first, [{
            'op_id': first['events'][0]['op_id'],
            'order_id':order['bulut_id'], 'version':2}])
        second = self.db.next_outbox_batch()
        self.assertEqual(second['kind'], 'progress')
        self.assertGreaterEqual(len(second['events']), 1)
        self.db.confirm_outbox(second, [{
            'op_id':event['op_id'], 'order_id':order['bulut_id'], 'version':4}
            for event in second['events']])
        self.assertEqual(self.db.pending_count, 0)

    def test_cloud_imported_order_clicks_use_status_and_targeted_progress(self):
        """Actual server-snapshot order shape, not only a locally created order."""
        cloud_id=str(uuid.uuid4())
        self.db.cloud_epoch='ci-existing'
        payload={
          'epoch':'ci-existing','orders_revision':1,
          'orders':[{'id':cloud_id,'order_number':71,'status':'havuz',
            'platform':'Manuel','shipping_reference':'TEST-71',
            'order_type':'','gross_amount':125,'version':14,
            'created_at':'2026-11-04T10:00:00Z','deleted_at':None}],
          'items':[{'id':str(uuid.uuid4()),'order_id':cloud_id,
            'book_code':self.book,'book_name_snapshot':'Kitap',
            'print_type':'SB','page_count_snapshot':100,'quantity':2,
            'prepared_count':0,'boxed_count':0}]
        }
        self.db.apply_cloud_snapshot(payload)
        order=next(x for x in self.db.siparisler if x.get('bulut_id')==cloud_id)
        class OfflineCloud:pass
        self.db.cloud_api=OfflineCloud()
        self.db.siparis_durumunu_degistir(order,'aktif')
        batch=self.db.next_outbox_batch()
        self.assertEqual(batch['kind'],'status')
        self.assertEqual(batch['events'][0]['to_status'],'aktif')
        self.db.confirm_outbox(batch,[{'op_id':batch['events'][0]['op_id'],
            'order_id':cloud_id,'version':15}])
        self.db.siparis_ilerleme_degistir(order,self.book,'SB',1,1)
        batch=self.db.next_outbox_batch()
        self.assertEqual(batch['kind'],'progress')
        self.assertEqual(batch['events'][0]['target_ready'],1)
        self.assertEqual(batch['events'][0]['target_boxed'],1)
        self.assertEqual(batch['events'][0]['base_ready'],0)
        self.db.confirm_outbox(batch,[{'op_id':batch['events'][0]['op_id'],
            'order_id':cloud_id,'version':16}])
        self.db.siparis_durumunu_degistir(order,'havuz')
        batch=self.db.next_outbox_batch()
        self.assertEqual(batch['kind'],'status')
        self.assertEqual(batch['events'][0]['from_status'],'aktif')
        self.assertEqual(batch['events'][0]['to_status'],'havuz')

    def test_failed_operation_is_quarantined_not_infinite_retry(self):
        order = self.new_order(connected=True)
        batch = self.db.next_outbox_batch()
        self.db.confirm_outbox(batch,[{'local_id':str(order['id']),
            'uuid':str(uuid.uuid4()), 'version':1, 'order_number':1}])
        self.db.siparis_durumunu_degistir(order,'aktif')
        bad = self.db.next_outbox_batch()
        self.db.quarantine_batch(bad,'Conflict 409')
        self.assertEqual(self.db.pending_count,0)
        self.assertIsNone(self.db.next_outbox_batch())
        path=Path(self.tmp.name)/'alfa_outbox.json'
        saved=json.loads(path.read_text('utf-8'))
        self.assertEqual(len(saved['conflicts']),1)
        self.assertIn('Conflict',saved['conflicts'][0]['reason'])

    def test_partial_cloud_delta_preserves_orders_without_redownloading_catalog(self):
        order=self.new_order()
        self.db.cloud_epoch='epoch-1'
        original_catalog_count=len(self.db.katalog)
        updates=self.db.apply_cloud_snapshot({
            'epoch':'epoch-1',
            'orders_revision':8,
            'inventory_revision':5,
            'inventory_products':[{'id':'example','sku':'STOCK-1'}],
            'inventory_sales':[]
        })
        self.assertEqual([x['id'] for x in self.db.siparisler],[order['id']])
        self.assertEqual(len(self.db.katalog),original_catalog_count)
        self.assertEqual(self.db.inventory_revision,5)
        self.assertEqual(self.db.inventory_products[0]['sku'],'STOCK-1')
        self.assertIn('__envanter__',updates)

    def test_partial_delta_cannot_silently_reset_cloud_epoch(self):
        self.new_order()
        self.db.cloud_epoch='old-epoch'
        with self.assertRaises(ValueError):
            self.db.apply_cloud_snapshot({'epoch':'new-epoch',
                'inventory_revision':2,'inventory_products':[]})
        self.assertEqual(len(self.db.siparisler),1)

    def test_product_catalog_master_and_inventory_membership(self):
        self.db.cloud_epoch='ci-catalog'
        self.assertEqual(self.db.siparisler,[])
        updates=self.db.apply_cloud_snapshot({
            'epoch':'ci-catalog','inventory_revision':22,
            'inventory_products':[{'id':'test-master','sku':'EPSON-TEST',
                'title':'Yazıcı','quantity':0,'sale_price':275.50,
                'active':True,'in_inventory':False}],
            'inventory_sales':[]
        })
        self.assertEqual(self.db.inventory_products[0]['in_inventory'],False)
        self.assertIn('__envanter__',updates)
        self.assertEqual(self.db.siparisler,[])
        updates=self.db.apply_cloud_snapshot({
            'epoch':'ci-catalog','inventory_revision':23,
            'inventory_products':[{'id':'test-master','sku':'EPSON-TEST',
                'title':'Yazıcı','quantity':3,'sale_price':310,
                'active':True,'in_inventory':True}],
            'inventory_sales':[]
        })
        self.assertEqual(self.db.inventory_products[0]['quantity'],3)
        self.assertTrue(self.db.inventory_products[0]['in_inventory'])
        self.assertIn('__envanter__',updates)

    def test_review_cloud_conflicts_preserves_archived_events_and_queue(self):
        self.new_order(connected=True)
        self.db._conflicts=[
            {'at':'2026-11-04T12:00:00Z','reason':'old 409',
             'batch':{'kind':'progress','events':[{'op_id':'legacy'}]}}
        ]
        self.assertEqual(len(self.db.unreviewed_cloud_conflicts),1)
        self.assertEqual(self.db.pending_count,1)
        self.assertEqual(self.db.mark_cloud_conflicts_reviewed(),1)
        self.assertEqual(len(self.db.unreviewed_cloud_conflicts),0)
        self.assertEqual(self.db.pending_count,1)
        from database import ERPDatabase
        reopened=ERPDatabase(ROOT/'KİTAPS.xlsx',data_dir=self.tmp.name)
        self.assertEqual(len(reopened._conflicts),1)
        self.assertTrue(reopened._conflicts[0]['reviewed_at'])
        self.assertEqual(reopened.pending_count,1)

    def test_reopen_pending_queue_after_restart(self):
        self.new_order(connected=True)
        from database import ERPDatabase
        recovered=ERPDatabase(ROOT / 'KİTAPS.xlsx', data_dir=self.tmp.name)
        self.assertEqual(recovered.pending_count,1)
        self.assertEqual(recovered.next_outbox_batch()['kind'],'commit')

if __name__ == '__main__':
    unittest.main()
