"""Regression coverage for page-visibility preferences and TUSDATA topic PDFs."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ayar_yonetimi import UserSettings
from pdf_kitap import PdfKutuphane


class PageVisibilityTests(unittest.TestCase):
    def test_previous_show_preference_migrates_to_hidden_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"alfa_ayarlar.json"
            source.write_text(json.dumps({"show_books_without_pages": True,
                                          "tema":"koyu"}),encoding="utf-8")
            first=UserSettings(tmp)
            self.assertFalse(first.get("show_books_without_pages"))
            first.set("show_books_without_pages",True)
            self.assertTrue(UserSettings(tmp).get("show_books_without_pages"))

    def test_catalog_uses_config_even_before_parented_to_window(self):
        # KatalogView builds its first page before it joins the main window.
        from ekran_katalog import KatalogView
        with tempfile.TemporaryDirectory() as tmp:
            cfg=UserSettings(tmp)
            books=[{"kod":"365","isim":"TUSDATA Konu Dahiliye 1",
                    "sayfa":160,"grup":"TUSDATA"},
                   {"kod":"465","isim":"TUSDATA YDUS Konu Dahiliye 1",
                    "sayfa":0,"grup":"TUSDATA"}]
            fake=SimpleNamespace(
                config=cfg,db=SimpleNamespace(kitaplar=books),
                search=SimpleNamespace(text=lambda:""),
                window=lambda:None)
            visible=KatalogView.filtered(fake)
            self.assertEqual([b["kod"] for b in visible],["365"])
            cfg.set("show_books_without_pages",True)
            self.assertEqual(len(KatalogView.filtered(fake)),2)


class TopicTitleTests(unittest.TestCase):
    def test_tusdata_konu_volume_is_not_a_catalog_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            folder=p/"pdfs";folder.mkdir()
            target=folder/"TUSDATA - Dahiliye - 1. Cilt - Konu.pdf"
            target.write_bytes(b"%PDF-1.4")
            lib=PdfKutuphane(p)
            lib.set_folder(folder)
            self.assertEqual(lib.find("365",title="TUSDATA Konu Dahiliye 1"),target.resolve())
            self.assertIsNone(lib.find("366",title="TUSDATA Konu Dahiliye 2"))
            self.assertIsNone(lib.find("1"))

if __name__=="__main__":
    unittest.main()
