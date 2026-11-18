"""v2.0.43: platform income shares and hover-only line-chart labels."""
import inspect
import unittest

from analitik_pasta import revenue_slices
from muhasebe_veri import completed_summary


class TinyDB:
    katalog = {}

    def __init__(self, rows):
        self.siparisler = rows

    @staticmethod
    def siparis_durumu(row):
        return row["durum"]


class PlatformDonutTests(unittest.TestCase):
    def test_revenue_not_order_counts(self):
        rows = [
            {"name":"Gardrops","gross":850,"orders":100},
            {"name":"Dolap","gross":150,"orders":1},
            {"name":"WhatsApp","gross":0,"orders":14},
        ]
        result = revenue_slices(rows)
        self.assertEqual([r["name"] for r in result], ["Gardrops","Dolap"])
        self.assertAlmostEqual(result[0]["percent"],85)
        self.assertAlmostEqual(result[1]["percent"],15)
        self.assertAlmostEqual(sum(r["percent"] for r in result),100)

    def test_group_small_platforms_and_skip_invalid(self):
        rows=[{"name":"K"+str(i),"gross":i+1} for i in range(12)]
        rows.extend([{"name":"None","gross":float("nan")},{"name":"Other","gross":-4}])
        result=revenue_slices(rows,max_slices=6)
        self.assertEqual(len(result),6)
        self.assertEqual(result[-1]["name"],"Diğer platformlar")
        self.assertAlmostEqual(sum(r["percent"] for r in result),100)
        self.assertEqual(sum(r["amount"] for r in result),78)

    def test_completed_refund_is_removed_from_pie_and_shipping_is_not(self):
        rows=[
            {"id":1,"durum":"tamamlandi","platform":"Dolap","ciro":100,
             "kargo_ucreti":10,"tamamlanma_tarihi":"2026-11-18","kitaplar":[]},
            {"id":2,"durum":"tamamlandi","platform":"Gardrops","ciro":200,
             "kargo_ucreti":80,"iade_tarihi":"2026-11-18",
             "tamamlanma_tarihi":"2026-11-18","kitaplar":[]},
        ]
        report=completed_summary(TinyDB(rows),"2026-11-18","2026-11-18")
        slices=revenue_slices(report["platforms"])
        self.assertEqual(len(slices),1)
        self.assertEqual(slices[0]["name"],"Dolap")
        self.assertAlmostEqual(slices[0]["percent"],100)
        self.assertEqual(sum(r["amount"] for r in slices), report["metrics"]["gross"])
        self.assertEqual(report["metrics"]["after_shipping"],10)

    def test_line_chart_has_no_permanent_peak_number_labels(self):
        from ekran_analitik import LineChart, AnalitikView
        code=inspect.getsource(LineChart.paintEvent)
        self.assertNotIn("peak_idx",code)
        self.assertNotIn("p.drawText(7,int(y)",code)
        self.assertIn("p.drawPath(path)",code)
        self.assertIn("if self.hovered:",code)
        self.assertIn("PlatformRevenueDonut",inspect.getsource(AnalitikView._build_report))


if __name__=="__main__":
    unittest.main()
