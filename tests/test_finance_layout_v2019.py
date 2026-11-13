"""Compensation/shipping accounting and prominent revenue grouping regression."""
import inspect
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from analitik_veri import build_dashboard
from muhasebe_veri import completed_summary, accounting_revenue


class _Completed:
    def __init__(self,orders):
        self.siparisler=orders
        self.katalog={}
    @staticmethod
    def siparis_durumu(order):
        return order["durum"]


class CompensationFinanceTests(unittest.TestCase):
    def test_compensation_has_zero_sales_but_shipping_reduces_total(self):
        today=datetime.now().astimezone().date().isoformat()
        fake=_Completed([
            {"id":"a","durum":"tamamlandi","siparis_turu":"Telafi Sipariş",
             "kargo_turu":"telafi","ciro":799,"kargo_ucreti":60,
             "tamamlanma_tarihi":today,"kitaplar":[]},
            {"id":"b","durum":"tamamlandi","siparis_turu":"Normal Sipariş",
             "platform":"Açık Adres","kargo_turu":"acik_adres",
             "ciro":950,"kargo_ucreti":80,
             "tamamlanma_tarihi":today,"kitaplar":[]}
        ])
        data=completed_summary(fake,today,today)
        m=data["metrics"]
        self.assertEqual(m["gross"],950)
        self.assertEqual(m["shipping_total"],140)
        self.assertEqual(m["shipping_telafi"],60)
        self.assertEqual(m["shipping_acik_adres"],80)
        self.assertEqual(m["after_shipping"],810)
        self.assertEqual(accounting_revenue(fake.siparisler[0]),0)

    def test_new_and_edited_compensation_orders_discard_entered_revenue(self):
        from database import ERPDatabase
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            db=ERPDatabase(root/"KİTAPS.xlsx",data_dir=temp)
            code=next(iter(db.katalog))
            entries=[{"kod":code,"tur":"SB","adet":1,"hazir":0,"koli":0}]
            new=db.yeni_siparis_olustur({
                "kod":"test-compensation-1","platform":"Dolap",
                "ciro":799,"siparis_turu":"Telafi Sipariş"},entries)
            self.assertEqual(new["ciro"],0)
            db.siparis_duzenle(new,{
                "kod":"test-compensation-1","platform":"Dolap",
                "ciro":750,"siparis_turu":"Telafi Sipariş"},entries)
            self.assertEqual(new["ciro"],0)
            db.siparis_duzenle(new,{
                "kod":"test-compensation-1","platform":"Dolap",
                "ciro":950,"siparis_turu":"Normal Sipariş"},entries)
            self.assertEqual(new["ciro"],950)

    def test_cash_hero_has_four_cards_and_minor_averages_are_separate(self):
        from ekran_analitik import AnalitikView,RevenuePill
        from PySide6.QtWidgets import QApplication
        app=QApplication.instance() or QApplication(["alfa-accounting-regression"])
        text=inspect.getsource(AnalitikView._build_report)
        self.assertIn("AnalyticsRevenueGroup",text)
        self.assertIn("CİRO VE TAHSİLAT DURUMU",text)
        self.assertIn("ORTALAMALAR · BİRİM VERİMLİLİK",text)
        self.assertIn("revenue_columns=self._revenue_columns()",text)
        self.assertIn("m['shipping_telafi']",text)
        pill=RevenuePill("Toplam ciro","950,00 ₺","#35dda9","Tamamlananlar")
        self.assertEqual(pill.objectName(),"AnalyticsRevenuePill")
        self.assertEqual(pill.height(),108)
        pill.close()

    def test_cover_rotation_reverses_previous_270_and_invalidates_cache(self):
        import pdf_kapak
        source=inspect.getsource(pdf_kapak.render_first_page)
        # Suite v2.0.20: PDF sources in the user's Meditus catalogue
        # need the reverse direction of v2.0.19 (+90).
        self.assertIn("QTransform().rotate(-90)",source)
        self.assertNotIn("QTransform().rotate(90)",source)
        self.assertGreaterEqual(pdf_kapak.CACHE_VERSION,4)

    def test_old_paid_day_report_excludes_compensation_revenue(self):
        from muhasebe_veri import html_report
        date="2026-11-13"
        fake=_Completed([
            {"id":"a","durum":"tamamlandi","siparis_turu":"Telafi Sipariş",
             "kargo_turu":"telafi","ciro":799,"kargo_ucreti":60,
             "tamamlanma_tarihi":date,"kitaplar":[]},
        ])
        data=completed_summary(fake,date,date)
        report=html_report(data,{date})
        self.assertIn("0.00 TL",report)
        self.assertIn("60.00 TL",report)
        self.assertNotIn("799.00 TL",report)


if __name__=="__main__":
    unittest.main()
