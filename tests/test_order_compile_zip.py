"""Offline regression guards for the outsourced-printing ZIP feature."""
import tempfile
from pathlib import Path
from zipfile import ZipFile
import unittest

from siparis_derle import DerlemeHatasi, derle_siparis, _rasterize_pdf


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
        self.source.write_bytes(b'%PDF-1.4 fake source Author SECRET_ORIGINAL_MARKER')
        self.order = {
            'id': 76, 'kod': 'KARGO-XX-99',
            'kitaplar': [
                {'kod': '11', 'tur': 'SB', 'adet': 2},
                {'kod': '11', 'tur': 'RNK', 'adet': 1},
            ],
        }
        self.catalog = {'11': {'isim': 'Orijinal Gizli Kitap'}}

    @staticmethod
    def fake_sanitize(source, destination, kind, *, progress, cancel):
        destination.write_bytes(b'%PDF-1.4\nSANITIZED-' + kind.encode('ascii'))

    def test_single_zip_separates_print_type_and_quantities_without_title(self):
        target = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop,
                              sanitize=self.fake_sanitize)
        self.assertEqual(target.name, 'Sipariş 76.zip')
        with ZipFile(target) as archive:
            names = archive.namelist()
            self.assertIn('Siyah/', names)
            self.assertIn('Renkli/', names)
            self.assertEqual(len([x for x in names if x.endswith('.pdf')]), 2)
            black = next(name for name in names if name.startswith('Siyah/') and name.endswith('.pdf'))
            color = next(name for name in names if name.startswith('Renkli/') and name.endswith('.pdf'))
            self.assertIn('2_ADET_BASILACAK', black)
            self.assertNotIn('2_ADET_BASILACAK', color)
            self.assertNotIn('Konfidentiel', '|'.join(names))
            self.assertNotIn('Gizli', '|'.join(names))
            self.assertNotIn('SECRET_ORIGINAL_MARKER', archive.read(black).decode())
            note = archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig')
            self.assertIn('Siparis No: 76', note)
            self.assertIn('Siparis Kodu: KARGO-XX-99', note)
            self.assertIn('TOPLAM BASILACAK KITAP: 3', note)
            self.assertIn(black + ' -> 2 ADET BASILACAK', note)
            self.assertIn(color + ' -> 1 ADET BASILACAK', note)
        self.assertIn(b'SECRET_ORIGINAL_MARKER', self.source.read_bytes())

    def test_selected_book_only_and_existing_zip_not_overwritten(self):
        other = self.pdfs / '12-Diger-Gizli.pdf'
        other.write_bytes(b'%PDF-1.4 another fake')
        self.order['kitaplar'].append({'kod': '12', 'tur': 'SB', 'adet': 3})
        self.catalog['12'] = {'isim': 'Diger'}
        first = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop,
                             codes=['11'], sanitize=self.fake_sanitize)
        second = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop,
                              codes=['12'], sanitize=self.fake_sanitize)
        self.assertEqual(second.name, 'Sipariş 76 (2).zip')
        with ZipFile(first) as archive:
            self.assertIn('TOPLAM BASILACAK KITAP: 3',
                          archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig'))
        with ZipFile(second) as archive:
            self.assertIn('TOPLAM BASILACAK KITAP: 3',
                          archive.read('BASKI_TALIMATI.txt').decode('utf-8-sig'))
            self.assertEqual(len([name for name in archive.namelist()
                                  if name.endswith('.pdf')]), 1)

    def test_legacy_duplicate_rows_are_combined(self):
        self.order['kitaplar'].append({'kod': '11', 'tur': 'SB', 'adet': 3})
        target = derle_siparis(self.order, self.catalog, self.pdfs, self.desktop,
                              sanitize=self.fake_sanitize)
        with ZipFile(target) as archive:
            entries = [n for n in archive.namelist() if n.startswith('Siyah/') and n.endswith('.pdf')]
            self.assertEqual(len(entries), 1)
            self.assertIn('5_ADET_BASILACAK', entries[0])

    def test_missing_pdf_does_not_create_partial_zip(self):
        self.order['kitaplar'].append({'kod': '98', 'tur': 'SB', 'adet': 1})
        with self.assertRaises(DerlemeHatasi):
            derle_siparis(self.order, self.catalog, self.pdfs, self.desktop,
                          sanitize=self.fake_sanitize)
        self.assertEqual(list(self.desktop.iterdir()), [])

    def test_sanitize_failure_does_not_create_zip(self):
        def broken(*_args, **_kwargs):
            raise ValueError('bad source PDF')
        with self.assertRaises(DerlemeHatasi):
            derle_siparis(self.order, self.catalog, self.pdfs, self.desktop,
                          sanitize=broken)
        self.assertEqual(list(self.desktop.iterdir()), [])

    def test_cancel_does_not_create_zip(self):
        with self.assertRaises(InterruptedError):
            derle_siparis(self.order, self.catalog, self.pdfs, self.desktop,
                          sanitize=self.fake_sanitize, cancel=lambda: True)
        self.assertEqual(list(self.desktop.iterdir()), [])

    def test_qt_rasterizer_strips_document_identity(self):
        try:
            from PySide6.QtGui import QPdfWriter, QPainter
            from PySide6.QtPdf import QPdfDocument
        except ImportError:
            self.skipTest('QtPdf is not installed in this environment')
        genuine_source = self.pdfs / 'test-metadata.pdf'
        writer = QPdfWriter(str(genuine_source))
        writer.setAuthor('SECRET_AUTHOR_123')
        writer.setTitle('SECRET_TITLE_123')
        writer.setCreator('SECRET_CREATOR_123')
        painter = QPainter(writer)
        self.assertTrue(painter.isActive())
        painter.drawText(60, 140, 'TEST PRINT CONTENT')
        self.assertTrue(painter.end())
        del writer
        sanitized = self.root / 'sanitized.pdf'
        _rasterize_pdf(genuine_source, sanitized, 'SB')
        reader = QPdfDocument()
        try:
            reader.load(str(sanitized))
            self.assertEqual(reader.status(), QPdfDocument.Status.Ready)
            self.assertEqual(reader.pageCount(), 1)
            for field in (QPdfDocument.MetaDataField.Author,
                          QPdfDocument.MetaDataField.Title,
                          QPdfDocument.MetaDataField.Creator):
                self.assertFalse(reader.metaData(field))
        finally:
            reader.close()
        result = sanitized.read_bytes()
        for secret in (b'SECRET_AUTHOR_123', b'SECRET_TITLE_123', b'SECRET_CREATOR_123'):
            self.assertNotIn(secret, result)


if __name__ == '__main__':
    unittest.main()
