"""Regression checks for v2.0.42 finance, in-page FlexFlow and readability."""
import inspect
import os
import unittest

from muhasebe_veri import (
    accounting_shipping, after_shipping_revenue, completed_summary,
)


class DummyDatabase:
    katalog = {}
    def __init__(self, rows):
        self.siparisler=rows

    @staticmethod
    def siparis_durumu(order):
        return order["durum"]


class AnalyticsFixTests(unittest.TestCase):
    def test_returns_and_all_recorded_shipping_reconcile(self):
        a={"durum":"tamamlandi","id":1,"ciro":1000,"kargo_ucreti":"95,50",
           "tamamlanma_tarihi":"2026-11-17","kitaplar":[]}
        b={"durum":"tamamlandi","id":2,"ciro":500,"kargo_ucreti":40,
           "tamamlanma_tarihi":"2026-11-18","iade_tarihi":"2026-11-18",
           "kitaplar":[]}
        c={"durum":"tamamlandi","id":3,"ciro":999,"kargo_ucreti":10,
           "siparis_turu":"Telafi Sipariş","tamamlanma_tarihi":"2026-11-18",
           "kitaplar":[]}
        data=completed_summary(DummyDatabase([a,b,c]),"2026-11-17","2026-11-18")
        m=data["metrics"]
        self.assertEqual(m["gross_before_returns"],1500)
        self.assertEqual(m["returned_revenue"],500)
        self.assertEqual(m["gross"],1000)
        self.assertEqual(m["shipping_total"],145.5)
        self.assertEqual(m["after_shipping"],854.5)
        self.assertEqual(after_shipping_revenue(a),904.5)
        self.assertEqual(after_shipping_revenue(b),-40)
        self.assertEqual(after_shipping_revenue(c),-10)
        self.assertEqual(sum(after_shipping_revenue(x) for x in (a,b,c)),
                         m["after_shipping"])
        self.assertEqual(accounting_shipping({"kargo_ucreti":"1.234,56"}),1234.56)

    def test_one_integrated_screen_not_three_subtabs_or_popup(self):
        from ekran_analitik import AnalitikView
        from ekran_verimlilik import FlexFlowView
        from PySide6.QtWidgets import QDialog, QWidget
        self.assertTrue(issubclass(FlexFlowView,QWidget))
        self.assertFalse(issubclass(FlexFlowView,QDialog))
        code=inspect.getsource(AnalitikView.__init__)
        self.assertIn('self.sections.addTab(normal_page,"Normal Analitik")',code)
        self.assertIn('self.sections.addTab(self.flexflow,"FlexFlow")',code)
        self.assertNotIn("FlexFlowDialog",inspect.getsource(AnalitikView))
        report=inspect.getsource(AnalitikView._build_report)
        self.assertIn("KİTAP · SAYFA · BASKI TÜRLERİ",report)
        self.assertIn("Kitap başına ciro",report)
        self.assertNotIn("Ödeme kapsama",report)
        self.assertNotIn("Aktif açık adres kargo (tümü)",report)
        self.assertNotIn("self.result_layout.addWidget(text('SİPARİŞLER'",report)

    def test_return_reason_uses_themed_plain_text_input(self):
        os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
        from PySide6.QtWidgets import QApplication
        from iade_nedeni import ReturnReasonDialog
        app=QApplication.instance() or QApplication(["alfa-refund-theme"])
        dialog=ReturnReasonDialog(123,"Paket yıpranmış")
        try:
            self.assertIn("QPlainTextEdit",dialog.styleSheet())
            self.assertIn("color:",dialog.styleSheet())
            self.assertEqual(dialog.reason,"Paket yıpranmış")
        finally:
            dialog.close()


if __name__=="__main__":
    unittest.main()
