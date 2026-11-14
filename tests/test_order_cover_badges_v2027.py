"""Order cover quantity badges never disappear for single-copy orders."""
import unittest
from kart_siparis import order_cover_badges


class OrderCoverBadgeTests(unittest.TestCase):
    def test_one_bw_copy(self):
        self.assertEqual(order_cover_badges({'adet':1,'sb':1,'rnk':0}),
                         [('total','1×'),('sb','SB 1')])

    def test_one_color_copy(self):
        self.assertEqual(order_cover_badges({'adet':1,'sb':0,'rnk':1}),
                         [('total','1×'),('rnk','RNK 1')])

    def test_mixed_prints(self):
        self.assertEqual(order_cover_badges({'adet':5,'sb':3,'rnk':2}),
                         [('total','5×'),('sb','SB 3'),('rnk','RNK 2')])

    def test_multiple_same_variant(self):
        self.assertEqual(order_cover_badges({'adet':12,'sb':0,'rnk':12}),
                         [('total','12×'),('rnk','RNK 12')])


if __name__=='__main__':
    unittest.main()
