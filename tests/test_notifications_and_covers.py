"""Offline Dolap, PDF orientation and notification-agent regressions."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import format_kargo_kodu
from bildirim_durumu import classify_new_orders
from bildirim_dogal_ses import cached_voice_path,validate_voice_id


class DolapFormattingTests(unittest.TestCase):
    def test_sixteen_digit_code_ends_with_its_own_four_digit_group(self):
        self.assertEqual(format_kargo_kodu("2624140909632909"),
                         "262 414 090 963 2909")
        self.assertEqual(format_kargo_kodu("262 414 090 9632909"),
                         "262 414 090 963 2909")

    def test_thirteen_and_nine_digit_codes_still_work(self):
        self.assertEqual(format_kargo_kodu("1234567890123"),
                         "123 456 789 0123")
        self.assertEqual(format_kargo_kodu("123456789",platform="Gardrops"),
                         "123 456 789")
        self.assertEqual(format_kargo_kodu("Açık adres, İstanbul"),
                         "Açık adres, İstanbul")


class NotificationStateTests(unittest.TestCase):
    def test_first_ever_order_one_is_not_lost(self):
        first,baseline=classify_new_orders(
            {"initialized":False,"last_order_number":0,"epoch":""},
            [],"epoch-a")
        self.assertEqual(first,[])
        fresh,new_state=classify_new_orders(
            baseline,[{"id":"one","order_number":1}],"epoch-a")
        self.assertEqual(len(fresh),1)
        self.assertEqual(new_state["last_order_number"],1)
        again,_=classify_new_orders(
            new_state,[{"id":"one","order_number":1}],"epoch-a")
        self.assertEqual(again,[])

    def test_baseline_does_not_announce_old_orders(self):
        fresh,state=classify_new_orders(
            {"initialized":False,"last_order_number":0,"epoch":""},
            [{"id":"old","order_number":50}],"epoch-a")
        self.assertFalse(fresh)
        fresh,_=classify_new_orders(
            state,[{"id":"old","order_number":50},
                   {"id":"new","order_number":51}],"epoch-a")
        self.assertEqual([x["id"] for x in fresh],["new"])

    def test_workspace_reset_silences_reused_numbers(self):
        fresh,state=classify_new_orders(
            {"initialized":True,"last_order_number":80,"epoch":"before"},
            [{"id":"fresh1","order_number":1}],"after")
        self.assertEqual(fresh,[])
        self.assertEqual(state["last_order_number"],1)
        fresh,_=classify_new_orders(
            state,[{"id":"fresh1","order_number":1},
                   {"id":"fresh2","order_number":2}],"after")
        self.assertEqual([x["id"] for x in fresh],["fresh2"])

    def test_duplicate_rows_not_announced_twice(self):
        fresh,_=classify_new_orders(
            {"initialized":True,"last_order_number":3,"epoch":"test"},
            [{"id":"same","order_number":4},{"id":"same","order_number":4}],
            "test")
        self.assertEqual(len(fresh),1)


class CoverOrientationTests(unittest.TestCase):
    def test_landscape_first_pdf_page_becomes_upright_jpeg(self):
        from PySide6.QtCore import QSizeF,QSize
        from PySide6.QtGui import QImage,QColor
        from pdf_kapak import render_first_page
        class FakePDF:
            def load(self,path):return None
            def pageCount(self):return 1
            def pagePointSize(self,index):return QSizeF(400,200)
            def render(self,index,size):
                image=QImage(size,QImage.Format.Format_RGB32)
                image.fill(QColor("white"))
                return image
            def close(self):pass
        with tempfile.TemporaryDirectory() as folder, \
             patch("pdf_kapak.QPdfDocument",FakePDF):
            dest=Path(folder)/"portrait.jpg"
            render_first_page(Path(folder)/"landscape.pdf",dest)
            image=QImage(str(dest))
            self.assertFalse(image.isNull())
            self.assertGreater(image.height(),image.width())
            self.assertLessEqual(image.height(),690)
            self.assertLessEqual(image.width(),480)

    def test_portrait_first_page_stays_portrait(self):
        from PySide6.QtCore import QSizeF
        from PySide6.QtGui import QImage,QColor
        from pdf_kapak import render_first_page
        class FakePDF:
            def load(self,path):return None
            def pageCount(self):return 1
            def pagePointSize(self,index):return QSizeF(200,400)
            def render(self,index,size):
                image=QImage(size,QImage.Format.Format_RGB32)
                image.fill(QColor("white"))
                return image
            def close(self):pass
        with tempfile.TemporaryDirectory() as folder, \
             patch("pdf_kapak.QPdfDocument",FakePDF):
            dest=Path(folder)/"portrait.jpg"
            render_first_page(Path(folder)/"portrait.pdf",dest)
            image=QImage(str(dest))
            self.assertFalse(image.isNull())
            self.assertGreater(image.height(),image.width())

    def test_cached_first_page_version_is_bumped(self):
        import pdf_kapak
        self.assertGreaterEqual(pdf_kapak.CACHE_VERSION,2)


class NotificationDeploymentContracts(unittest.TestCase):
    def test_scheduled_task_installed_and_removed_with_suite(self):
        root=Path(__file__).resolve().parents[1]
        script=(root/"tools/Install-OrderNotifications.ps1").read_text("utf-8")
        installer=(root/"ALFACOPYCENTER_Suite.iss").read_text("utf-8")
        for token in ("Register-ScheduledTask","-AtLogOn","-LogonType Interactive",
                      "Start-ScheduledTask","Unregister-ScheduledTask"):
            self.assertIn(token,script)
        self.assertIn("Install-OrderNotifications.ps1",installer)
        self.assertIn("[UninstallRun]",installer)
        self.assertIn("Components: staff",installer)

    def test_cloud_voice_configuration_is_not_a_plaintext_api_key(self):
        root=Path(__file__).resolve().parents[1]
        voices=(root/"bildirim_dogal_ses.py").read_text("utf-8")
        self.assertIn("store_api_key",voices)
        self.assertIn("crypt(key.encode",voices)
        self.assertIn("xi-api-key",voices)
        self.assertNotIn("sk_",voices)

    def test_cache_identifies_voice_and_does_not_leak_api_key(self):
        with tempfile.TemporaryDirectory() as folder:
            path=cached_voice_path(folder,"123456789ABCDefghij")
            self.assertIn("notification_voice_cache",str(path))
            self.assertNotIn("123456789ABCDefghij",path.name)
        self.assertRaises(ValueError,validate_voice_id,"danger/../123456789")


if __name__=="__main__":
    unittest.main()
