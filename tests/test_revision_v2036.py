"""Completed pagination, static status palette and fee accounting."""
import unittest
from datetime import date
from siparis_arsivi import ayir_tamamlananlar, completed_page
from ayar_yonetimi import replace_red_green,static_completed_styles
from muhasebe_veri import completed_summary
from analitik_veri import build_dashboard

class Data:
    def __init__(self,orders):self.siparisler=orders;self.katalog={}
    @staticmethod
    def siparis_durumu(order):return order['durum']

class Revision36Tests(unittest.TestCase):
    def test_recent_three_calendar_days_and_pages(self):
        rows=[{'id':i,'tamamlanma_tarihi':'2026-11-15'} for i in range(41)]
        rows += [{'id':41,'tamamlanma_tarihi':'2026-11-13'},{'id':42,'tamamlanma_tarihi':'2026-11-12'}]
        recent,archive=ayir_tamamlananlar(rows,date(2026,11,15))
        self.assertEqual((len(recent),len(archive)),(42,1))
        self.assertEqual([len(completed_page(recent,i)[0]) for i in range(3)],[20,20,2])
        self.assertEqual(completed_page(recent,99)[1:],(2,3))

    def test_palette_mapping(self):
        self.assertNotEqual(replace_red_green('#ff0000'),'#ff0000')
        self.assertNotEqual(replace_red_green('#36a86e'),'#36a86e')
        self.assertEqual(replace_red_green('#00dfff'),'#00dfff')
        self.assertIn(':hover',static_completed_styles('koyu'))

    def test_active_shipping_separate_and_then_moved_to_completed(self):
        row={'id':'a','durum':'aktif','platform':'Açık Adres','ciro':500,
             'kargo_ucreti':80,'tarih':'2026-11-15','kitaplar':[]}
        db=Data([row])
        report=completed_summary(db,'2026-11-15','2026-11-15')['metrics']
        self.assertEqual((report['active_address_shipping'],report['shipping_total']),(80,0))
        row.update(durum='tamamlandi',tamamlanma_tarihi='2026-11-15')
        report=completed_summary(db,'2026-11-15','2026-11-15')['metrics']
        self.assertEqual((report['active_address_shipping'],report['shipping_total'],report['after_shipping']),(0,80,420))
