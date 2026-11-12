"""Offline-first Firebase queue and pricing safeguards; no remote service calls."""
import json, tempfile, unittest
from pathlib import Path
from database import ERPDatabase

ROOT=Path(__file__).resolve().parents[1]

class FirebaseOfflineDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='alfa_firebase_offline_')
        self.addCleanup(self.tmp.cleanup)
        self.db=ERPDatabase(ROOT/'KİTAPS.xlsx',data_dir=self.tmp.name)
        self.book=next(iter(self.db.katalog))

    def add_order(self,db,platform='Gardrops',amount=245.75):
        return db.yeni_siparis_olustur(
            {'kod':'123456789','platform':platform,'ciro':amount,
             'siparis_turu':'Normal Sipariş'},
            [{'kod':self.book,'tur':'SB','adet':1,'hazir':0,'koli':0}])

    def test_full_gardrops_amount_is_preserved(self):
        order=self.add_order(self.db)
        self.assertEqual(order['ciro'],245.75)
        reopened=ERPDatabase(ROOT/'KİTAPS.xlsx',data_dir=self.tmp.name)
        self.assertEqual(reopened.siparisler[0]['ciro'],245.75)

    def test_verified_epoch_persists_across_offline_restart(self):
        marker=Path(self.tmp.name)/'alfa_cloud_epoch.json'
        self.db._atomik_json_yaz(str(marker),{'epoch':'verified-firebase-workspace'})
        db=ERPDatabase(ROOT/'KİTAPS.xlsx',data_dir=self.tmp.name)
        self.assertEqual(db.cloud_epoch,'verified-firebase-workspace')
        db.cloud_required=True
        db.cloud_api=object()  # Deliberately has no network methods.
        row=self.add_order(db,amount=500.50)
        self.assertEqual(row['ciro'],500.50)
        self.assertEqual(db.pending_count,1)
        self.assertEqual(db.next_outbox_batch()['kind'],'commit')
        reopened=ERPDatabase(ROOT/'KİTAPS.xlsx',data_dir=self.tmp.name)
        self.assertEqual(reopened.pending_count,1)
        self.assertEqual(reopened.cloud_epoch,'verified-firebase-workspace')

    def test_new_unverified_device_does_not_queue_cloud_orders(self):
        self.db.cloud_required=True
        self.db.cloud_api=object()
        with self.assertRaises(ValueError):
            self.add_order(self.db)
        self.assertFalse(self.db.siparisler)
        self.assertEqual(self.db.pending_count,0)

    def test_changed_firebase_epoch_cannot_discard_queued_work(self):
        marker=Path(self.tmp.name)/'alfa_cloud_epoch.json'
        self.db._atomik_json_yaz(str(marker),{'epoch':'previous-firebase-epoch'})
        db=ERPDatabase(ROOT/'KİTAPS.xlsx',data_dir=self.tmp.name)
        db.cloud_required=True
        db.cloud_api=object()
        self.add_order(db,amount=60)
        pending=Path(self.tmp.name)/'alfa_outbox.json'
        before=pending.read_bytes()
        with self.assertRaises(ValueError):
            db.apply_cloud_snapshot({
                'epoch':'different-firebase-epoch','orders':[],'items':[]})
        self.assertEqual(pending.read_bytes(),before)
        self.assertEqual(db.pending_count,1)

if __name__=='__main__':
    unittest.main()
