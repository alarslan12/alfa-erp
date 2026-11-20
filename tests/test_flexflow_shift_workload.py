"""FlexFlow shift allocation: provenance, conservation and capacity guards."""
import inspect
import unittest
from datetime import date, datetime, timedelta

from flexflow_emek import build_workload
from flexflow_operasyon import daily_dashboard, operation_insight
from flexflow_rapor import csv_report, html_report


class FakeDB:
    def __init__(self, rows):
        self.siparisler = rows

    @staticmethod
    def siparis_durumu(row):
        return row["durum"]

    @staticmethod
    def _book_page_count(item):
        return int(item.get("sayfa_birim") or 0)


def _dates():
    tz = datetime.now().astimezone().tzinfo
    return (datetime(2026, 11, 20, 12, 0, tzinfo=tz),
            datetime(2026, 11, 19, 10, 0, tzinfo=tz),
            datetime(2026, 11, 20, 12, 0, tzinfo=tz))


def _orders(qty=16, pages=300, activated_yesterday=True):
    now, started, finished = _dates()
    rows = []
    for n in range(qty):
        row = {"id": n+1, "bulut_id": "o-"+str(n),
               "durum": "tamamlandi",
               "tamamlanma_tarihi": finished.isoformat(),
               "kitaplar": [{"kod": "A", "tur": "SB", "adet": 1,
                            "hazir": 1, "koli": 1, "sayfa_birim": pages}]}
        if activated_yesterday:
            row["isleme_alinma_tarihi"] = started.isoformat()
        rows.append(row)
    return now, FakeDB(rows)


class ShiftWorkloadTests(unittest.TestCase):
    def test_prior_activation_smooths_completion_spike_without_changing_orders(self):
        now, db = _orders()
        result = daily_dashboard(db, [], now=now,
                                 start_date="2026-11-19",
                                 end_date="2026-11-20")
        yesterday, today = result["points"]
        self.assertEqual(yesterday["orders"], 0)
        self.assertEqual(today["orders"], 16)
        self.assertGreater(yesterday["modeled"], 0)
        self.assertLess(today["modeled"], 16)
        self.assertGreater(yesterday["carry_out_min"], 0)
        self.assertGreater(today["carry_in_min"], 0)
        self.assertEqual(result["period"]["orders"], 16)
        reference = result["work_model"]["reference_min"]
        self.assertAlmostEqual(
            yesterday["modeled_minutes"] + today["modeled_minutes"],
            reference * 16, places=2,
        )
        self.assertIn("tahmini", result["work_model"]["method"])
        self.assertIn("Üretim yükü tahmini", operation_insight(result, now)["model"])

    def test_earlier_actual_ready_event_has_priority_over_hourly_guess(self):
        now, db = _orders(qty=1)
        _, started, finished = _dates()
        events = [{
            "order_id": "o-0",
            "at": started.replace(hour=15).isoformat(),
            "ready": 1,
            "boxed": 0,
        }, {
            "order_id": "o-0",
            "at": finished.replace(hour=11).isoformat(),
            "ready": 0,
            "boxed": 1,
        }]
        model = build_workload(db, events, date(2026,11,19),
                               date(2026,11,20),now=now)
        prior = model["days"]["2026-11-19"]
        current = model["days"]["2026-11-20"]
        self.assertGreater(prior["logged_minutes"],0)
        self.assertEqual(prior["inferred_minutes"],0)
        self.assertGreater(current["logged_minutes"],0)
        self.assertAlmostEqual(prior["minutes"]+current["minutes"],
                               model["reference_min"],places=2)

    def test_no_prior_evidence_does_not_fabricate_yesterday_work(self):
        now, db = _orders(activated_yesterday=False)
        model = build_workload(db, [], "2026-11-19","2026-11-20",now=now)
        self.assertEqual(model["days"]["2026-11-19"]["minutes"],0)
        self.assertGreater(model["days"]["2026-11-20"]["minutes"],0)
        self.assertEqual(model["shifted_orders"],0)

    def test_theoretical_capacity_anomaly_shows_without_claiming_actual_work(self):
        now, db = _orders(qty=16,pages=10000,activated_yesterday=False)
        result=daily_dashboard(db,[],now=now,start_date="2026-11-20")
        capacity=result["work_model"]["capacity"]["2026-11-20"]
        self.assertTrue(capacity["over_capacity"])
        self.assertGreater(capacity["ideal_min"],capacity["elapsed_min"])
        self.assertEqual(result["work_model"]["shifted_orders"],0)
        insight=operation_insight(result,now)["model"]
        self.assertIn("teorik alt",insight)
        self.assertIn("Kesin geçmiş dağılımı değildir",insight)

    def test_capacity_constraint_moves_more_unlogged_prep_if_activation_is_prior(self):
        now, db = _orders(qty=16,pages=10000,activated_yesterday=True)
        model=build_workload(db,[],"2026-11-19","2026-11-20",now=now)
        self.assertTrue(model["capacity"]["2026-11-20"]["over_capacity"])
        self.assertGreater(model["days"]["2026-11-19"]["minutes"],
                           model["days"]["2026-11-20"]["minutes"])
        self.assertGreater(model["days"]["2026-11-19"]["inferred_minutes"],0)

    def test_unknown_pages_not_presented_as_zero_or_fully_modeled(self):
        now, db = _orders(qty=2)
        db.siparisler[1]["kitaplar"][0]["sayfa_birim"]=0
        report=daily_dashboard(db,[],now=now,start_date="2026-11-20")
        self.assertEqual(report["points"][0]["orders"],2)
        self.assertEqual(report["points"][0]["unmodeled_orders"],1)
        self.assertEqual(report["work_model"]["incomplete_orders"],1)
        self.assertIn("eksik",operation_insight(report,now)["model"])
        self.assertIn("Eksik veri",csv_report(report))
        self.assertIn("Eksik veri",html_report(report))

    def test_exact_yesterday_filter_includes_work_for_order_finished_today(self):
        now, db = _orders(qty=1)
        report=daily_dashboard(db,[],now=now,start_date="2026-11-19")
        self.assertEqual(report["selected"]["orders"],0)
        self.assertGreater(report["selected"]["modeled"],0)
        self.assertEqual(len(report["points"]),1)
        self.assertEqual(report["work_model"]["reference_samples"],1)

    def test_ui_keeps_real_completion_and_new_modeled_chart_separate(self):
        from ekran_verimlilik import FlexFlowView
        code=inspect.getsource(FlexFlowView.__init__)
        self.assertIn("self.completed_chart=LineChart",code)
        self.assertIn("self.model_chart=LineChart",code)
        self.assertIn('"modeled","Üretim eşdeğeri (tahmin)"',code)
        self.assertIn("self.insight_model",code)


if __name__=="__main__":
    unittest.main()
