"""Production summary is copy-based and keeps print vs pack distinct."""
import unittest
from siparis_uretim_ozeti import production_summary, count_text, money_text

class ProductionSummaryTests(unittest.TestCase):
    def test_mixed_orders_and_copy_counts(self):
        data=[
            {'ciro':500,'kitaplar':[
                {'kod':'1','tur':'SB','adet':4,'hazir':3,'koli':2,'sayfa':100},
                {'kod':'1','tur':'RNK','adet':3,'hazir':1,'koli':0,'sayfa':120}]},
            {'ciro':250,'kitaplar':[
                {'kod':'2','tur':'SB','adet':2,'hazir':2,'koli':2,'sayfa':80}]},
        ]
        x=production_summary(data,lambda i:i['sayfa'])
        self.assertEqual((x['orders'],x['books'],x['sb'],x['rnk']),(2,9,6,3))
        self.assertEqual((x['ready'],x['boxed'],x['remaining']),(6,4,5))
        self.assertEqual((x['print_waiting'],x['pack_ready']),(3,2))
        self.assertEqual((x['print_sb'],x['print_rnk']),(1,2))
        self.assertEqual((x['pages'],x['print_pages'],x['revenue']),(920,340,750))
        self.assertEqual(x['remaining'],x['print_waiting']+x['pack_ready'])
    def test_undo_and_unknown_pages(self):
        i={'adet':2,'hazir':2,'koli':2}
        orders=[{'kitaplar':[i]}]
        self.assertEqual(production_summary(orders,lambda i:0)['remaining'],0)
        i['koli']=1
        x=production_summary(orders,lambda i:0)
        self.assertEqual((x['remaining'],x['pack_ready'],x['print_waiting']),(1,1,0))
        self.assertEqual(x['unknown_pages'],2)
        i['hazir']=0
        x=production_summary(orders,lambda i:0)
        self.assertEqual((x['boxed'],x['unknown_print']),(0,2))
    def test_empty_and_format(self):
        self.assertEqual(production_summary([],lambda i:0)['packed_percent'],0)
        self.assertEqual(count_text(12345),'12.345')
        self.assertEqual(money_text(1234.5),'1.234,50 TL')
