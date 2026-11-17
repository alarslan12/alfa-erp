"""FlexFlow arithmetic contracts: no printer/device or Firebase side effects."""
import unittest
from datetime import datetime
from flexflow import estimate, BLACK_PPM, COLOR_PPM


class FlexFlowTests(unittest.TestCase):
    def test_parallel_printer_capacities(self):
        self.assertEqual(BLACK_PPM, 135)
        self.assertEqual(COLOR_PPM, 37.5)

    def test_pending_counts_and_manual_work(self):
        orders = [{"kitaplar": [
            {"kod": "1", "adet": 2, "hazir": 1, "koli": 0, "tur": "SB"},
            {"kod": "2", "adet": 1, "hazir": 0, "koli": 0, "tur": "RNK"}
        ]}]
        pages = {"1": 300, "2": 150}
        r = estimate(orders, lambda item: pages[item["kod"]],
                     now=datetime(2026, 11, 18, 8, 0))
        self.assertEqual(r["print_copies"], 2)
        self.assertEqual(r["pages_sb"], 300)
        self.assertEqual(r["pages_color"], 150)
        self.assertEqual(r["pack_orders"], 1)
        self.assertEqual(r["shift_remaining_min"], 540)
        self.assertLessEqual(r["optimistic_elapsed_min"], r["sequential_elapsed_min"])

    def test_missing_pages_block_confident_forecast(self):
        r = estimate([{"kitaplar":[{"kod": 10,"adet":1}]}],
                     lambda item: 0, now=datetime(2026, 11, 18, 7, 0))
        self.assertFalse(r["fully_known"])
        self.assertIsNone(r["minimum_overtime_min"])
        self.assertEqual(r["missing_page_codes"], ["10"])

    def test_completed_standard_includes_prepared_copies(self):
        rows = [{"kitaplar":[{"adet":3, "hazir":3, "koli":3, "tur":"SB"}]}]
        self.assertEqual(estimate(rows,lambda item:200)["print_copies"],0)
        self.assertEqual(estimate(rows,lambda item:200,completed=True)["print_pages"],600)


if __name__ == "__main__":
    unittest.main()
