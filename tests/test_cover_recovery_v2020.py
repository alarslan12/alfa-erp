"""Regression for flipped Meditus PDFs, PRETUS volume-name lookup,
and stale generated JPEGs that must not replace a verified manual cover.
All tests work on temporary files and never contact Firebase.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")


class PdfCatalogMatchTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(prefix="alfa_pdf_names_")
        self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name)
        self.pdfs=self.root/"library"
        self.pdfs.mkdir()
        self.data=self.root/"data"
        self.data.mkdir()

    def new_book(self,name):
        path=self.pdfs/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b"%PDF-1.4\nmock-cover-by-test")
        return path

    def library(self):
        from pdf_kitap import PdfKutuphane
        library=PdfKutuphane(self.data)
        library.set_folder(self.pdfs)
        return library

    def test_pretus_title_finds_code_402_without_confusing_volume_three(self):
        original=self.new_book("TUSDATA PRETUS 3.pdf")
        library=self.library()
        self.assertTrue(library.find("402",title="TUSDATA PRETUS 3").samefile(original))
        self.assertIsNone(library.find("3",title="Başka yayınevi anatomi"))
        self.assertIsNone(library.find("403",title="TUSDATA PRETUS 4"))

    def test_unicode_turkish_and_nested_paths_resolve_exact_title(self):
        original=self.new_book("alt kategori/TUSDATA Meditus Küçük Stajlar - Kapak.pdf")
        library=self.library()
        self.assertTrue(
            library.find("393",title="TUSDATA Meditus KÜÇÜK STAJLAR").samefile(original))

    def test_duplicate_titles_do_not_pick_wrong_cover(self):
        self.new_book("a/TUSDATA PRETUS 3.pdf")
        self.new_book("b/TUSDATA PRETUS 3.pdf")
        library=self.library()
        with self.assertRaisesRegex(ValueError,"birden fazla PDF"):
            library.find("402",title="TUSDATA PRETUS 3")

    def test_scan_report_has_unmatched_real_catalog_names(self):
        from pdf_kapak import refresh_pdf_covers,CACHE_VERSION
        self.new_book("TUSDATA PRETUS 3.pdf")
        self.library()  # Persist the user-selected PDF source folder first.
        class FakePdf:
            def load(self, path):pass
            def pageCount(self):return 1
            def pagePointSize(self,_i):
                from PySide6.QtCore import QSizeF
                return QSizeF(400,200)
            def render(self,_i,size):
                from PySide6.QtGui import QImage
                image=QImage(size,QImage.Format.Format_RGB32)
                image.fill(0xffffffff)
                return image
            def close(self):pass
        with patch("pdf_kapak.QPdfDocument",FakePdf):
            result=refresh_pdf_covers(self.data,[
                {"kod":"402","isim":"TUSDATA PRETUS 3"},
                {"kod":"403","isim":"TUSDATA PRETUS 4"}])
        self.assertEqual(result["created"],1,str(result))
        self.assertEqual(result["missing"],1)
        self.assertTrue(any("#403" in x for x in result["missing_examples"]))
        auto=self.data/"kapaklar"/"pdf_otomatik"
        self.assertTrue((auto/"402.jpg").is_file())
        manifest=json.loads((auto/"alfa_pdf_kapak_onbellek.json").read_text("utf-8"))
        self.assertEqual(manifest["version"],CACHE_VERSION)
        self.assertEqual(set(manifest["entries"]),{"402"})
        self.assertTrue((self.data/"alfa_pdf_kapak_tarama_raporu.json").is_file())

    def test_reject_stale_generated_cover_while_preserving_manual_cover(self):
        from widgets import Covers
        from pdf_kapak import CACHE_VERSION
        from PySide6.QtGui import QImage
        auto=self.data/"kapaklar"/"pdf_otomatik"
        auto.mkdir(parents=True)
        shot=QImage(300,400,QImage.Format.Format_RGB32)
        shot.fill(0xffbbccdd)
        stale=auto/"402.jpg"
        self.assertTrue(shot.save(str(stale),"JPEG",90))
        (auto/"alfa_pdf_kapak_onbellek.json").write_text(
            json.dumps({"version":CACHE_VERSION,"entries":{}}),encoding="utf-8")
        class Db:
            sepet_dosyasi=str(self.data/"orders.json")
        covers=Covers(Db(),self.root)
        book={"kod":"402","isim":"TUSDATA PRETUS 3"}
        self.assertIsNone(covers.path(book))
        (auto/"alfa_pdf_kapak_onbellek.json").write_text(
            json.dumps({"version":CACHE_VERSION,"entries":{"402":["tested"]}}),
            encoding="utf-8")
        covers.refresh()
        self.assertEqual(covers.path(book),stale)
        manual=self.data/"kapaklar"/"402.png"
        self.assertTrue(shot.save(str(manual),"PNG"))
        covers.refresh()
        self.assertEqual(covers.path(book),manual)

    def test_negative_ninety_rotates_visible_text_from_upside_down(self):
        from PySide6.QtGui import QImage
        from PySide6.QtCore import QSizeF
        from pdf_kapak import render_first_page,CACHE_VERSION
        class OrientationPdf:
            def load(self,path):pass
            def pageCount(self):return 1
            def pagePointSize(self,_index):return QSizeF(400,200)
            def render(self,_index,size):
                pic=QImage(size,QImage.Format.Format_RGB32)
                pic.fill(0xffffffff)
                from PySide6.QtGui import QPainter,QColor
                painter=QPainter(pic)
                painter.fillRect(0,0,size.width()//5,size.height()//5,QColor("#ff0000"))
                painter.end()
                return pic
            def close(self):pass
        target=self.root/"corrected.jpg"
        with patch("pdf_kapak.QPdfDocument",OrientationPdf):
            render_first_page(self.root/"any.pdf",target)
        result=QImage(str(target))
        self.assertFalse(result.isNull())
        self.assertGreater(result.height(),result.width())
        # A top-left red marker moves to bottom-left after -90 rotation.
        at=result.pixelColor(10,result.height()-20)
        self.assertGreater(at.red(),180)
        self.assertLess(at.green(),100)
        self.assertGreaterEqual(CACHE_VERSION,4)


if __name__=="__main__":
    unittest.main()
