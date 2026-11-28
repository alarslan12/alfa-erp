"""Local outsourcing order store and ZIP regression tests (no network)."""
from pathlib import Path
import tempfile
import sqlite3
import json
import unittest
from zipfile import ZipFile

from siparis_derle import derle_siparis
from siparis_derleme_havuzu import DerlemeHavuzu, compile_snapshot, order_totals, local_label


class DerlemeHavuzuTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.store = DerlemeHavuzu(self.root)
        self.catalog = {'11': {'isim': 'Kitap 11', 'sayfa': 120, 'renkli_opsiyon': True},
                        '12': {'isim': 'Kitap 12', 'sayfa': 50, 'renkli_opsiyon': False}}
        self.items = [{'kod': '11', 'tur': 'SB', 'adet': 2},
                      {'kod': '11', 'tur': 'RNK', 'adet': 1}]

    def add(self, price=100):
        return self.store.add({'kod': '', 'ciro': price, 'order_note': 'Fason notu'},
                              self.items, self.catalog)

    def test_separate_persistent_groups_and_snapshot_totals(self):
        self.assertEqual(self.add('100,25'), 1)
        self.assertEqual(self.add('10.10'), 2)
        self.assertEqual(order_totals(self.store.list()), dict(
            siparis=2, kitap=6, sayfa=720, ciro_kurus=11035))
        self.store.set_completed(1, True)
        self.catalog['11']['sayfa'] = 900
        reopened = DerlemeHavuzu(self.root)
        self.assertEqual(order_totals(reopened.list()), dict(
            siparis=1, kitap=3, sayfa=360, ciro_kurus=1010))
        self.assertEqual(order_totals(reopened.list(True)), dict(
            siparis=1, kitap=3, sayfa=360, ciro_kurus=10025))
        self.assertTrue(reopened.get(1)['completed_at'])
        self.assertNotIn('hazir', reopened.get(1)['kitaplar'][0])
        self.assertNotIn('koli', reopened.get(1)['kitaplar'][0])
        reopened.set_completed(1, False)
        self.assertEqual(len(reopened.list()), 2)
        self.assertEqual(reopened.list(True), [])
        self.assertEqual([p.name for p in self.root.iterdir()], ['owner_derleme'])

    def test_bulk_completion_is_atomic_and_id_not_reused(self):
        one, two = self.add(), self.add()
        with self.assertRaises(ValueError):
            self.store.set_completed_many([one, 9999], True)
        self.assertEqual(len(self.store.list()), 2)
        self.store.set_completed_many([one, two], True)
        self.assertEqual(len(self.store.list(True)), 2)
        self.assertEqual(self.add(), 3)

    def test_zip_does_not_complete_order_and_uses_separate_name(self):
        sid = self.add()
        pdfs = self.root / 'pdfs'
        pdfs.mkdir()
        desktop = self.root / 'desktop'
        desktop.mkdir()
        (pdfs / '11.pdf').write_bytes(b'%PDF-1.4\nexample')
        order, catalog = compile_snapshot(self.store.get(sid))
        path = derle_siparis(order, catalog, pdfs, desktop)
        self.store.record_zip(sid, path)
        self.assertEqual(path.name, 'D001.zip')
        with ZipFile(path) as archive:
            note = archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig')
            self.assertIn('Sipariş Kodu: D001', note)
            self.assertIn('Toplam Sayfa Sayısı: 360', note)
            self.assertIn('Toplam Kitap Sayısı: 3', note)
            self.assertIn('Fason notu', note)
        self.assertEqual(len(self.store.list()), 1)
        self.assertTrue(self.store.get(sid)['last_zip_at'])
        self.assertIsNone(self.store.get(sid)['completed_at'])

    def test_invalid_orders_leave_no_rows(self):
        for info, items in [
            ({'ciro': 'NaN'}, self.items),
            ({'ciro': -1}, self.items),
            ({'ciro': 10}, []),
            ({'ciro': 10}, [{'kod': '12', 'tur': 'RNK', 'adet': 1}]),
        ]:
            with self.assertRaises(ValueError):
                self.store.add(info, items, self.catalog)
        self.assertEqual(self.store.list(), [])

    def test_edit_preserves_snapshot_and_invalidates_stale_zip(self):
        sid = self.add()
        self.store.record_zip(sid, 'old.zip')
        old = self.store.get(sid)
        self.catalog['11']['sayfa'] = 900
        self.store.update(sid, {'kod': 'REF', 'ciro': 150, 'order_note': 'Yeni'},
                          [{'kod': '11', 'tur': 'SB', 'adet': 3},
                           {'kod': '12', 'tur': 'SB', 'adet': 2}],
                          self.catalog, expected=old)
        edited = self.store.get(sid)
        self.assertEqual(edited['created_at'], old['created_at'])
        self.assertEqual(order_totals([edited]), dict(
            siparis=1, kitap=5, sayfa=460, ciro_kurus=15000))
        self.assertIsNone(edited['last_zip_at'])
        self.assertIsNone(edited['last_zip_path'])
        with self.assertRaises(ValueError):
            self.store.record_zip(sid, 'stale.zip', expected=old)
        self.store.record_zip(sid, 'current.zip', expected=edited)
        with self.assertRaises(ValueError):
            self.store.update(sid, {'ciro': 1}, self.items, self.catalog, expected=old)
        self.assertEqual(self.store.get(sid)['last_zip_path'], 'current.zip')

    def test_soft_delete_atomic_and_does_not_reuse_number(self):
        first, second = self.add(), self.add()
        self.store.set_completed(second, True)
        with self.assertRaises(ValueError):
            self.store.delete_many([first, 9999])
        self.assertEqual(len(self.store.list()), 1)
        self.store.delete_many([first, second])
        self.assertEqual(self.store.list(), [])
        self.assertEqual(self.store.list(True), [])
        with self.assertRaises(ValueError):
            self.store.get(first)
        with sqlite3.connect(self.store.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM orders WHERE deleted_at IS NOT NULL').fetchone()[0], 2)
        self.assertEqual(self.add(), 3)
        self.assertEqual(local_label(3), 'D003')
        self.assertEqual(local_label(1000), 'D1000')

    def test_existing_v220_database_migrates_without_changing_rows(self):
        with sqlite3.connect(self.store.path) as db:
            db.execute('ALTER TABLE orders DROP COLUMN deleted_at')
            db.execute("""INSERT INTO orders (id, kod, ciro_kurus, order_note, kitaplar, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                       (7, 'OLD', 500, 'Not', json.dumps([dict(kod='11', tur='SB', adet=1,
                          isim='Kitap 11', sayfa=120, sayfa_birim=120)]), '2026-11-28T12:00:00'))
        reopened = DerlemeHavuzu(self.root)
        self.assertEqual(local_label(reopened.get(7)['id']), 'D007')
        self.assertEqual(reopened.get(7)['kod'], 'OLD')
        self.assertEqual(reopened.add({'ciro': 1}, self.items, self.catalog), 8)
