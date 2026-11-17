"""2.0.39: return reason normalization and lifecycle."""
import unittest
from database import ERPDatabase

class FakeDB:
    def __init__(self, order):
        self.siparisler = [order]
        self.cloud_api = None
        self.cloud_required = False
        self.saved = 0
    @staticmethod
    def siparis_durumu(order):
        return ERPDatabase.siparis_durumu(order)
    def siparisleri_kaydet(self):
        self.saved += 1

class ReturnReasonTests(unittest.TestCase):
    def test_reason_required_and_editable(self):
        order = {'id': 1, 'durum': 'tamamlandi'}
        db = FakeDB(order)
        with self.assertRaises(ValueError):
            ERPDatabase.set_order_returned(db,order,True,reason='')
        with self.assertRaises(ValueError):
            ERPDatabase.set_order_returned(db,order,True,reason='x'*501)
        ERPDatabase.set_order_returned(db,order,True,reason='  Kargo   hasarlı  ')
        self.assertEqual(order['iade_sebebi'],'Kargo hasarlı')
        stamp=order['iade_tarihi']
        ERPDatabase.set_order_returned(db,order,True,reason='Müşteri isteği')
        self.assertEqual(order['iade_tarihi'],stamp)
        self.assertEqual(order['iade_sebebi'],'Müşteri isteği')
        ERPDatabase.set_order_returned(db,order,False)
        self.assertNotIn('iade_tarihi',order)
        self.assertNotIn('iade_sebebi',order)
        self.assertEqual(db.saved,3)

if __name__ == '__main__':
    unittest.main()
