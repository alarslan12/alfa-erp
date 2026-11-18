"""Regression checks for approved v2.0.44 analytics mockup fixes."""
import inspect
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")


class AnalyticsMockupFixTests(unittest.TestCase):
    def test_line_chart_unfilled_and_y_axis_numbers(self):
        from ekran_analitik import LineChart
        code=inspect.getsource(LineChart.paintEvent)
        self.assertIn("p.setBrush(Qt.BrushStyle.NoBrush)", code)
        self.assertIn("p.drawPath(path)", code)
        self.assertIn("self._formatted(value)", code)
        self.assertIn("p.drawText(5,int(y)-8", code)
        self.assertNotIn("peak_idx", code)

    def test_open_path_has_no_filled_triangle_in_real_qt_paint(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
        from PySide6.QtWidgets import QApplication
        from ekran_analitik import LineChart
        app=QApplication.instance() or QApplication(["alfa-unfilled-chart-test"])
        app.setProperty("alfa_theme","koyu")
        chart=LineChart("Test", [("orders","Sipariş","#409fff")])
        chart.resize(640,220)
        chart.set_data([
            {"label":"11/14","orders":0},
            {"label":"11/15","orders":100},
            {"label":"11/16","orders":0},
        ])
        canvas=QImage(640,220,QImage.Format.Format_ARGB32)
        canvas.fill(Qt.GlobalColor.transparent)
        chart.render(canvas)
        # This point is inside the triangle formed by the open line. A
        # retained QPainter brush paints it bright blue; a line-only chart
        # leaves the dark navy panel intact.
        pixel=canvas.pixelColor(320,125)
        self.assertLess(pixel.blue(),135,repr((pixel.red(),pixel.green(),pixel.blue())))
        chart.close()

    def test_cloud_badge_does_not_override_all_hover_tooltips(self):
        from main import AlfaMain
        source=inspect.getsource(AlfaMain._cloud_status)
        self.assertNotIn("self.setToolTip(message)",source)
        self.assertIn("self.cloud_badge.setToolTip(message)",source)

    def test_donut_shares_grid_with_real_metrics(self):
        from ekran_analitik import AnalitikView
        from analitik_pasta import PlatformRevenueDonut
        report=inspect.getsource(AnalitikView._build_report)
        self.assertIn("dashboard_row.addWidget(platform_panel,0,0)",report)
        self.assertIn("dashboard_row.addWidget(summary_panel,0,1)",report)
        self.assertIn("money(m['after_shipping'])",report)
        self.assertIn("integer(m['pages'])",report)
        self.assertIn("integer(m['books'])",report)
        self.assertIn("integer(m['sb'])",report)
        self.assertIn("integer(m['rnk'])",report)
        self.assertNotIn("ÖNCEKİ DÖNEME GÖRE",report.upper())
        self.assertIn("PLATFORMA GÖRE GELİR DAĞILIMI",
                      inspect.getsource(PlatformRevenueDonut.__init__))


if __name__=="__main__":
    unittest.main()
