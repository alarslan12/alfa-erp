"""FlexFlow operations regressions: real event history, no synthetic hourly data."""
import unittest
from datetime import datetime, timezone, timedelta, date
from flexflow_operasyon import daily_dashboard, extract_history
from flexflow_rapor import csv_report, html_report


class FakeDB:
    def __init__(self,orders):
        self.siparisler=orders
    @staticmethod
    def siparis_durumu(row):
        return row["durum"]
    @staticmethod
    def _book_page_count(item):
        return int(item.get("sayfa_birim") or 0)


class FlexFlowOperationalTests(unittest.TestCase):
    def setup_orders(self):
        tz=datetime.now().astimezone().tzinfo
        now=datetime(2026,11,18,17,0,tzinfo=tz)
        orders=[
            {"id":1,"bulut_id":"cloud-one","durum":"tamamlandi",
             "isleme_alinma_tarihi":datetime(2026,11,18,8,0,tzinfo=tz).isoformat(),
             "tamamlanma_tarihi":datetime(2026,11,18,11,0,tzinfo=tz).isoformat(),
             "kitaplar":[{"kod":"a","tur":"SB","adet":2,"hazir":2,"koli":2,"sayfa_birim":300}]},
            {"id":2,"durum":"tamamlandi",
             "tamamlanma_tarihi":datetime(2026,11,17,10,0,tzinfo=tz).isoformat(),
             "kitaplar":[{"kod":"b","tur":"RNK","adet":1,"hazir":1,"koli":1,"sayfa_birim":100}]},
            {"id":3,"durum":"aktif",
             "isleme_alinma_tarihi":datetime(2026,11,18,9,0,tzinfo=tz).isoformat(),
             "kitaplar":[{"kod":"c","tur":"SB","adet":4,"hazir":2,"koli":1,"sayfa_birim":150}]},
        ]
        logs={
            "evt-1":{"id":"evt-1","action":"progress_bulk",
                     "created_at":datetime(2026,11,18,9,30,tzinfo=tz).isoformat(),
                     "details":{"events":[{"delta_ready":2,"delta_boxed":0}]}},
            "evt-2":{"id":"evt-2","action":"progress_bulk",
                     "created_at":datetime(2026,11,18,10,15,tzinfo=tz).isoformat(),
                     "details":{"events":[{"delta_ready":0,"delta_boxed":1}]}}
        }
        return now,orders,[{"id":"cloud-one","event_log":logs}]

    def test_extract_server_timestamps_and_deltas_without_extra_user_data(self):
        now,_,payload=self.setup_orders()
        records=extract_history(payload,now=now)
        self.assertEqual(len(records),2)
        self.assertEqual(sum(x["ready"] for x in records),2)
        self.assertEqual(sum(x["boxed"] for x in records),1)
        self.assertTrue(all("device_name" not in x for x in records))
        self.assertTrue(all("details" not in x for x in records))
        self.assertEqual(records[0]["at"][11:13],"10")
        self.assertEqual(records[1]["at"][11:13],"09")

    def test_daily_hourly_and_backlog_counts(self):
        now,orders,payload=self.setup_orders()
        events=extract_history(payload,now=now)
        r=daily_dashboard(FakeDB(orders),events,days=7,now=now,
                          selected_day=date(2026,11,18))
        self.assertEqual(r["today"]["orders"],1)
        self.assertEqual(r["today"]["books"],2)
        self.assertEqual(r["today"]["pages"],600)
        self.assertEqual(r["today"]["ready"],2)
        self.assertEqual(r["today"]["boxed"],1)
        self.assertEqual(r["hourly"][8]["started"],1)
        self.assertEqual(r["hourly"][9]["started"],1)
        self.assertEqual(r["hourly"][9]["ready"],2)
        self.assertEqual(r["hourly"][10]["boxed"],1)
        self.assertEqual(r["hourly"][11]["orders"],1)
        self.assertEqual(r["open_work"]["print_waiting"],2)
        self.assertEqual(r["open_work"]["pack_ready"],1)
        self.assertEqual(r["active_orders"],1)
        self.assertEqual(r["average_orders"],1)
        self.assertEqual(r["today_rate"],0.1)
        self.assertEqual(round(r["tempo_change"]),0)
        self.assertIn("2026-11-18",r["logged_days"])
        self.assertIn("Tamamlanan",html_report(r))
        self.assertIn("2026-11-18",csv_report(r))

    def test_missing_history_not_turned_into_false_zero(self):
        now,orders,_=self.setup_orders()
        r=daily_dashboard(FakeDB(orders),[],days=7,now=now)
        self.assertFalse(r["has_progress_history"])
        self.assertFalse(r["today_activity_known"])
        self.assertIn("Kayıt yok",csv_report(r))
        self.assertEqual(r["open_work"]["pack_ready"],1)

    def test_prior_day_hourly_view(self):
        now,orders,_=self.setup_orders()
        r=daily_dashboard(FakeDB(orders),[],days=7,now=now,
                          selected_day=date(2026,11,17))
        self.assertEqual(r["hourly"][10]["orders"],1)
        self.assertEqual(r["hourly"][11]["orders"],0)

    def test_production_screen_shows_business_metrics_not_raw_coefficients(self):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
        from PySide6.QtWidgets import QApplication
        from ekran_verimlilik import FlexFlowView
        app=QApplication.instance() or QApplication(["alfa-flexflow-operations-test"])
        now,orders,_=self.setup_orders()
        view=FlexFlowView(FakeDB(orders))
        try:
            view.refresh()
            self.assertIsNotNone(view.latest)
            self.assertEqual(len(view.cards),6)
            self.assertIn("ÜRETİM PANOSU",view.findChild(__import__(
                "PySide6.QtWidgets",fromlist=["QLabel"]).QLabel).text())
            self.assertEqual(view.daily_table.columnCount(),6)
            self.assertEqual(view.hourly_table.columnCount(),5)
            self.assertIn("Mesai",view.shift_note.text())
        finally:
            view.close()


if __name__=="__main__":
    unittest.main()
