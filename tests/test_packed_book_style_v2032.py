"""Visual state is strictly tied to complete packing, not total preparation."""
import unittest
from kart_siparis import fully_boxed, pool_cover_group

class BoxedStyleTests(unittest.TestCase):
    def test_ready_only_is_not_green(self):
        self.assertFalse(fully_boxed({'adet':3,'hazir':3,'koli':0}))
        self.assertFalse(fully_boxed({'adet':3,'hazir':3,'koli':2}))
    def test_full_pack_and_undo(self):
        group={'adet':3,'hazir':3,'koli':3}
        self.assertTrue(fully_boxed(group))
        group['koli']=2
        self.assertFalse(fully_boxed(group))
    def test_pool_mixed_copies(self):
        row={'sb':3,'rnk':2,'sb_ready':3,'rnk_ready':2,'sb_boxed':3,'rnk_boxed':1}
        self.assertFalse(fully_boxed(pool_cover_group(row)))
        row['rnk_boxed']=2
        self.assertTrue(fully_boxed(pool_cover_group(row)))
    def test_no_false_empty_or_inactive(self):
        self.assertFalse(fully_boxed({'adet':0,'koli':0}))
        self.assertFalse(fully_boxed({'adet':1,'koli':1},False))

if __name__=='__main__':
    unittest.main()
