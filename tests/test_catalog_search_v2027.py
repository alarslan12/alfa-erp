"""Keep numeric series searches separate from catalog code fragments."""
import unittest
from utils import metin_eslesiyor_mu


class CatalogSearchTests(unittest.TestCase):
    def setUp(self):
        self.book = {'kod': '365', 'isim': 'TUSDATA 24 Konu Dahiliye', 'grup': 'TUSDATA'}
        self.unrelated = {'kod': '424', 'isim': 'PROSPEKTUS KÜÇÜK STAJLAR 2', 'grup': 'PROSPEKTUS'}
        self.other = {'kod': '24', 'isim': 'TUSDATA Konu Pediatri', 'grup': 'TUSDATA'}

    def test_series_alias_word_order_and_joined_terms(self):
        for query in ('TUSDATA 24', '24 tusdata', 'TUS 24', '24 TUS', 'TUSDATA24', 'TUS DATA 24'):
            with self.subTest(query=query):
                self.assertTrue(metin_eslesiyor_mu(query, self.book))
                self.assertFalse(metin_eslesiyor_mu(query, self.unrelated))
                self.assertFalse(metin_eslesiyor_mu(query, self.other))

    def test_exact_series_number_and_code(self):
        self.assertFalse(metin_eslesiyor_mu('TUSDATA 2', self.book))
        self.assertFalse(metin_eslesiyor_mu('24', self.unrelated))
        self.assertTrue(metin_eslesiyor_mu('424', self.unrelated))
        self.assertTrue(metin_eslesiyor_mu('24', self.other))

    def test_existing_text_and_turkish_search(self):
        self.assertTrue(metin_eslesiyor_mu('küçük staj', self.unrelated))
        self.assertTrue(metin_eslesiyor_mu('TUSDATA dah', self.book))


if __name__ == '__main__':
    unittest.main()
