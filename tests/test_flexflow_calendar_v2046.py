"""FlexFlow date filters, activity day list and decision support regressions."""
import inspect
import unittest
from datetime import date, datetime, timedelta, timezone

from flexflow_operasyon import (
    activity_dates, daily_dashboard, operation_insight,
)
from flexflow_rapor import csv_report, html_report


class FakeDB:
    def __init__(self, orders):
        self.siparisler=orders

    @staticmethod
    def siparis_durumu(order):
        return order["durum"]

    @staticmethod
    def _book_page_count(item):
        return int(item.get("sayfa_birim") or 0)


def fixture():
    tz=timezone(timedelta(hours=3))
    now=datetime(2026,11,19,16,0,tzinfo=tz)
    orders=[
        {"id":1,"durum":"tamamlandi","tamamlanma_tarihi":"2026-11-19T11:00:00+03:00",
         "kitaplar":[{"kod":"A","adet":2,"hazir":2,"koli":2,"sayfa_birim":100}]},
        {"id":2,"durum":"tamamlandi","tamamlanma_tarihi":"2026-11-17T10:00:00+03:00",
         "kitaplar":[{"kod":"B","adet":1,"hazir":1,"koli":1,"sayfa_birim":150}]},
        {"id":3,"durum":"aktif","isleme_alinma_tarihi":"2026-11-18T09:00:00+03:00",
         "kitaplar":[{"kod":"C","adet":4,"hazir":2,"koli":1,"sayfa_birim":80}]},
        {"id":4,"durum":"havuz",
         "kitaplar":[{"kod":"D","adet":2,"hazir":0,"koli":0,"sayfa_birim":200}]},
    ]
    events=[
        {"at":"2026-11-18T09:30:00+03:00","order_id":"3","ready":2,"boxed":0,"status":"aktif"},
        {"at":"2026-11-18T10:00:00+03:00","order_id":"3","ready":0,"boxed":1,"status":""},
    ]
    return now, FakeDB(orders), events


class FlexFlowFilterTests(unittest.TestCase):
    def test_activity_dropdown_has_only_recorded_production_days(self):
        now,db,events=fixture()
        dates=activity_dates(db,events,now=now)
        self.assertEqual(dates,["2026-11-19","2026-11-18","2026-11-17"])
        self.assertNotIn("2026-11-16",dates)

    def test_exact_historic_day_filters_all_daily_metrics(self):
        now,db,events=fixture()
        report=daily_dashboard(db,events,now=now,
                               start_date="2026-11-17",end_date="2026-11-17")
        self.assertEqual(report["start"],"2026-11-17")
        self.assertEqual(report["end"],"2026-11-17")
        self.assertEqual(len(report["points"]),1)
        self.assertEqual(report["selected"]["orders"],1)
        self.assertEqual(report["selected"]["pages"],150)
        self.assertEqual(report["today"]["orders"],0)
        self.assertFalse(report["selected_activity_known"])
        self.assertEqual(report["hourly"][10]["orders"],1)
        self.assertIn("2026-11-17",csv_report(report))
        insight=operation_insight(report,now=now)
        self.assertIn("17.11.2026",insight["title"])
        self.assertIn("1 sipariş",insight["observation"])
        self.assertIn("Şu an",insight["live"])
        self.assertIn("saat kaydı yok",insight["progress"])

    def test_calendar_date_range_filters_totals_graph_data_and_reports(self):
        now,db,events=fixture()
        report=daily_dashboard(db,events,now=now,
                               start_date=date(2026,11,17),
                               end_date=date(2026,11,19))
        self.assertEqual([p["date"] for p in report["points"]],
                         ["2026-11-17","2026-11-18","2026-11-19"])
        self.assertEqual(report["period"]["orders"],2)
        self.assertEqual(report["period"]["pages"],350)
        self.assertEqual(report["period"]["ready"],2)
        self.assertEqual(report["period"]["boxed"],1)
        self.assertEqual(report["selected_day"],"2026-11-19")
        summary=operation_insight(report,now=now)
        self.assertIn("DÖNEM DEĞERLENDİRMESİ",summary["title"])
        self.assertIn("2 sipariş",summary["observation"])
        self.assertIn("17.11.2026",summary["title"])
        self.assertIn("19.11.2026",summary["title"])
        self.assertIn("DÖNEM DEĞERLENDİRMESİ",html_report(report))

    def test_missing_progress_logs_are_not_fabricated(self):
        now,db,_=fixture()
        report=daily_dashboard(db,[],now=now,
                               start_date="2026-11-17")
        self.assertFalse(report["selected_activity_known"])
        self.assertIn("saat kaydı yok",operation_insight(report,now)["progress"])
        self.assertIn("Kayıt yok",csv_report(report))

    def test_invalid_calendar_future_or_enormous_ranges_fail(self):
        now,db,events=fixture()
        with self.assertRaisesRegex(ValueError,"Gelecek"):
            daily_dashboard(db,events,now=now,start_date="2026-11-20")
        with self.assertRaisesRegex(ValueError,"366"):
            daily_dashboard(db,events,now=now,start_date="2025-01-01",
                            end_date="2026-11-19")

    def test_shared_modern_picker_and_one_day_controls(self):
        from ekran_verimlilik import FlexFlowView
        from takvim import TarihPopup
        source=inspect.getsource(FlexFlowView.__init__)
        self.assertIn("AlfaTemaliCombo()",source)
        self.assertIn('"CalendarTrigger"',source)
        self.assertNotIn("Son 7 gün",source)
        self.assertNotIn("Son 14 gün",source)
        self.assertNotIn("Son 30 gün",source)
        self.assertIn("self.insight_panel",source)
        self.assertIn("def open_calendar",inspect.getsource(FlexFlowView))
        self.assertIn("activity_label",inspect.getsource(TarihPopup))


if __name__=="__main__":
    unittest.main()
