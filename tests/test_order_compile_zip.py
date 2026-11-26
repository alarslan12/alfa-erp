"""Offline regression checks for fast, unmodified PDF ZIP packaging."""
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED
import unittest

from siparis_derle import DerlemeHatasi, derle_siparis


class LocalOrderBundleTests(unittest.TestCase):
    def setUp(self):
        self.working = tempfile.TemporaryDirectory(prefix='alfa_order_bundle_test_')
        self.addCleanup(self.working.cleanup)
        self.root = Path(self.working.name)
        self.pdfs = self.root / 'pdfs'
        self.pdfs.mkdir()
        self.desktop = self.root / 'desktop'
        self.desktop.mkdir()
        self.source = self.pdfs / '11-Ozel-Konfidentiel-Kitap.pdf'
        self.original_bytes = b'%PDF-1.4\n% ORIGINAL AUTHOR SECRET_ORIGINAL_MARKER\nSOURCE CONTENT'
        self.source.write_bytes(self.original_bytes)
        self.order = {
            'id': 76, 'kod': 'KARGO-XX-99',
            'kitaplar': [
                {'kod': '11', 'tur': 'SB', 'adet': 2},
                {'kod': '11', 'tur': 'RNK', 'adet': 1},
            ],
        }
        self.catalog = {'11': {'isim': 'Orijinal Gizli Kitap', 'sayfa': 100}}

    def test_single_zip_separates_print_type_and_quantities_without_title(self):
        target = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop)
        self.assertEqual(target.name, 'Sipariş 76.zip')
        with ZipFile(target) as archive:
            names = archive.namelist()
            self.assertIn('Siyah/', names)
            self.assertIn('Renkli/', names)
            self.assertEqual(len([x for x in names if x.endswith('.pdf')]), 2)
            black = next(name for name in names if name.startswith('Siyah/') and name.endswith('.pdf'))
            color = next(name for name in names if name.startswith('Renkli/') and name.endswith('.pdf'))
            self.assertRegex(black, r'^Siyah/2 ADET - DOSYA_[0-9A-F]{12}\.pdf$')
            self.assertRegex(color, r'^Renkli/1 ADET - DOSYA_[0-9A-F]{12}\.pdf$')
            self.assertNotIn('Konfidentiel', '|'.join(names))
            self.assertNotIn('Gizli', '|'.join(names))
            # No metadata stripping, grayscale conversion or PDF re-encoding:
            # every byte, including the source's identity marker, is retained.
            self.assertEqual(archive.read(black), self.original_bytes)
            self.assertEqual(archive.read(color), self.original_bytes)
            self.assertEqual(archive.getinfo(black).compress_type, ZIP_STORED)
            note = archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig')
            self.assertEqual(note.splitlines(), [
                'Sipariş Kodu: KARGO-XX-99',
                'Toplam Sayfa Sayısı: 300',
                'Toplam Kitap Sayısı: 3',
            ])
        self.assertEqual(self.source.read_bytes(), self.original_bytes)

    def test_order_note_is_appended_after_summary(self):
        self.order['order_note'] = 'Önce renkli basın.\nİkinci satır Türkçe not.'
        target = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop)
        with ZipFile(target) as archive:
            self.assertEqual(
                archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig').splitlines(),
                ['Sipariş Kodu: KARGO-XX-99',
                 'Toplam Sayfa Sayısı: 300',
                 'Toplam Kitap Sayısı: 3',
                 '',
                 'Sipariş Notu:',
                 'Önce renkli basın.',
                 'İkinci satır Türkçe not.'])

    def test_whitespace_only_note_does_not_change_three_line_instruction(self):
        self.order['order_note'] = '  \n  '
        target = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop)
        with ZipFile(target) as archive:
            self.assertEqual(
                archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig').splitlines(),
                ['Sipariş Kodu: KARGO-XX-99',
                 'Toplam Sayfa Sayısı: 300',
                 'Toplam Kitap Sayısı: 3'])

    def test_selected_book_only_and_existing_zip_not_overwritten(self):
        other = self.pdfs / '12-Diger-Gizli.pdf'
        other.write_bytes(b'%PDF-1.4\nother')
        self.order['kitaplar'].append({'kod': '12', 'tur': 'SB', 'adet': 3})
        self.catalog['12'] = {'isim': 'Diger', 'sayfa': 80}
        first = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop, codes=['11'])
        second = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop, codes=['12'])
        self.assertEqual(second.name, 'Sipariş 76 (2).zip')
        with ZipFile(first) as archive:
            self.assertEqual(
                archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig').splitlines(),
                ['Sipariş Kodu: KARGO-XX-99',
                 'Toplam Sayfa Sayısı: 300',
                 'Toplam Kitap Sayısı: 3'])
        with ZipFile(second) as archive:
            self.assertEqual(
                archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig').splitlines(),
                ['Sipariş Kodu: KARGO-XX-99',
                 'Toplam Sayfa Sayısı: 240',
                 'Toplam Kitap Sayısı: 3'])
            self.assertEqual(len([name for name in archive.namelist()
                                  if name.endswith('.pdf')]), 1)

    def test_legacy_duplicate_rows_are_combined(self):
        self.order['kitaplar'].append({'kod': '11', 'tur': 'SB', 'adet': 3})
        target = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop)
        with ZipFile(target) as archive:
            entries = [n for n in archive.namelist()
                       if n.startswith('Siyah/') and n.endswith('.pdf')]
            self.assertEqual(len(entries), 1)
            self.assertRegex(entries[0], r'^Siyah/5 ADET - DOSYA_[0-9A-F]{12}\.pdf$')
            self.assertEqual(
                archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig').splitlines(),
                ['Sipariş Kodu: KARGO-XX-99',
                 'Toplam Sayfa Sayısı: 600',
                 'Toplam Kitap Sayısı: 6'])

    def test_historical_page_snapshot_precedes_catalog_and_invalid_value_falls_back(self):
        self.order['kitaplar'][0]['sayfa_birim'] = 125
        self.order['kitaplar'][0]['sayfa'] = 900
        self.order['kitaplar'][1]['sayfa_birim'] = 'invalid'
        target = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop)
        with ZipFile(target) as archive:
            self.assertEqual(
                archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig').splitlines(),
                ['Sipariş Kodu: KARGO-XX-99',
                 'Toplam Sayfa Sayısı: 350',
                 'Toplam Kitap Sayısı: 3'])

    def test_missing_pdf_does_not_create_partial_zip(self):
        self.order['kitaplar'].append({'kod': '98', 'tur': 'SB', 'adet': 1})
        with self.assertRaises(DerlemeHatasi):
            derle_siparis(self.order, self.catalog, self.pdfs, self.desktop)
        self.assertEqual(list(self.desktop.iterdir()), [])

    def test_empty_pdf_does_not_create_zip(self):
        self.source.write_bytes(b'')
        with self.assertRaises(DerlemeHatasi):
            derle_siparis(self.order, self.catalog, self.pdfs, self.desktop)
        self.assertEqual(list(self.desktop.iterdir()), [])

    def test_cancel_does_not_create_zip(self):
        with self.assertRaises(InterruptedError):
            derle_siparis(self.order, self.catalog, self.pdfs, self.desktop,
                          cancel=lambda: True)
        self.assertEqual(list(self.desktop.iterdir()), [])

    def test_progress_reports_file_counts_without_page_rendering(self):
        events = []
        derle_siparis(self.order, self.catalog, self.pdfs, self.desktop,
                      progress=lambda index, total, _unused1, _unused2:
                      events.append((index, total)))
        self.assertEqual(events, [(1, 2), (2, 2)])


if __name__ == '__main__':
    unittest.main()
