"""Title-only PDF cover mapping guardrails without Qt or Firebase."""
import tempfile
import unittest
from pathlib import Path
from pdf_kitap import PdfKutuphane


class TitleMappingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='alfa_pdf_names_')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.folder=self.root/'pdfs'
        self.folder.mkdir()
        self.lib=PdfKutuphane(self.root)

    def pdf(self,name):
        path=self.folder/name
        path.write_bytes(b'%PDF-1.4 placeholder for filename matching')
        return path

    def test_dusdata_33_matches_excel_title_not_number_33(self):
        expected=self.pdf('DUSDATA 33 Endodonti.pdf')
        self.lib.set_folder(self.folder)
        self.assertEqual(self.lib.find('119',title='DUSDATA 33 Endodonti'),expected.resolve())
        self.assertIsNone(self.lib.find('33'))

    def test_denttest_volume_not_conflated_with_catalog_code(self):
        expected=self.pdf('Denttest 12 - kapak.pdf')
        self.lib.set_folder(self.folder)
        self.assertEqual(self.lib.find('131',title='DUSDATA DENTTEST 12'),expected.resolve())
        self.assertIsNone(self.lib.find('12'))
        self.assertIsNone(self.lib.find('132',title='DUSDATA DENTTEST 13'))

    def test_adc_cerrahi_optional_on_pdf_cover(self):
        expected=self.pdf('DUSDATA 33 Cerrahi.pdf')
        self.lib.set_folder(self.folder)
        self.assertEqual(self.lib.find('117',title='DUSDATA 33 ADÇ Cerrahi'),expected.resolve())

    def test_explicit_numeric_filename_still_works(self):
        expected=self.pdf('kitap_31.pdf')
        self.lib.set_folder(self.folder)
        self.assertEqual(self.lib.find('31',title='Başka Kitap'),expected.resolve())

    def test_duplicate_full_titles_do_not_pick_arbitrary_cover(self):
        self.pdf('DUSDATA 33 Ortodonti.pdf')
        extra=self.folder/'copies'
        extra.mkdir()
        (extra/'DUSDATA 33 Ortodonti.pdf').write_bytes(b'%PDF-1.4')
        self.lib.set_folder(self.folder)
        self.assertIsNone(self.lib.find('120',title='DUSDATA 33 Ortodonti'))

    def test_tusdata_konu_ignores_word_order_and_cilt_decoration(self):
        expected=self.pdf('Dahiliye Cilt 1 TUS DATA Konu.pdf')
        self.lib.set_folder(self.folder)
        self.assertEqual(
            self.lib.find('365',title='TUSDATA Konu Dahiliye 1'),
            expected.resolve())
        self.assertIsNone(self.lib.find('366',title='TUSDATA Konu Dahiliye 2'))

    def test_tusdata_konu_roman_volume_and_tr_characters(self):
        expected=self.pdf('TUSDATA KONU KÜÇÜK STAJLAR CİLT II.pdf')
        self.lib.set_folder(self.folder)
        self.assertEqual(
            self.lib.find('374',title='TUSDATA Konu Küçük Stajlar 2'),
            expected.resolve())
        self.assertIsNone(
            self.lib.find('375',title='TUSDATA Konu Küçük Stajlar 3'))

    def test_other_tusdata_series_not_mixed_with_konu(self):
        self.pdf('TUSDATA Prime Dahiliye 2.pdf')
        self.lib.set_folder(self.folder)
        self.assertIsNone(self.lib.find('366',title='TUSDATA Konu Dahiliye 2'))

    def test_ambiguous_tusdata_konu_filenames_fail_closed(self):
        self.pdf('TUSDATA Konu Dahiliye 1 Cilt.pdf')
        self.pdf('Dahiliye 1 - TUSDATA Konu.pdf')
        self.lib.set_folder(self.folder)
        self.assertIsNone(self.lib.find('365',title='TUSDATA Konu Dahiliye 1'))


if __name__=='__main__':
    unittest.main()
