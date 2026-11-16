import unittest
from siparis_arsivi import shipping_fee_entered
from muhasebe_veri import completed_summary, completion_fingerprints

class DB:
    katalog={}
    def __init__(self,orders):self.siparisler=orders
    @staticmethod
    def siparis_durumu(o):return o['durum']

class ReturnAndFeeTests(unittest.TestCase):
    def test_fee(self):
        for v in (None,0,'0,00',-1,'nan','bad'):
            self.assertFalse(shipping_fee_entered({'kargo_ucreti':v}))
        for v in (0.01,95,'95,50'):
            self.assertTrue(shipping_fee_entered({'kargo_ucreti':v}))
    def test_refund_keeps_shipping(self):
        a={'id':1,'durum':'tamamlandi','platform':'Açık Adres','ciro':500,'kargo_ucreti':80,'tamamlanma_tarihi':'2026-11-15','kitaplar':[]}
        b={**a,'id':2,'ciro':1000,'kargo_ucreti':0}
        db=DB([a,b]);before=completion_fingerprints(db)
        a['iade_tarihi']='2026-11-16T12:00:00+03:00'
        m=completed_summary(db,'2026-11-15','2026-11-15')['metrics']
        self.assertEqual((m['gross_before_returns'],m['returned_revenue'],m['gross'],m['shipping_total'],m['after_shipping']),(1500,500,1000,80,920))
        self.assertEqual((m['returned_orders'],m['return_order_ratio'],m['shipping_missing']),(1,50,1))
        self.assertNotEqual(before,completion_fingerprints(db))
        a.pop('iade_tarihi')
        self.assertEqual(completed_summary(db,'2026-11-15','2026-11-15')['metrics']['gross'],1500)
