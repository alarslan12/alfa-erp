"""Independent and persistent accessibility preference; no production access."""
import tempfile
import unittest
from ayar_yonetimi import UserSettings,colorblind_styles

class ColorblindModeTests(unittest.TestCase):
    def test_default_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg=UserSettings(directory)
            self.assertFalse(cfg.get('colorblind_mode'))
            cfg.set('tema','acik')
            cfg.set('colorblind_mode',True)
            cfg=UserSettings(directory)
            self.assertTrue(cfg.get('colorblind_mode'))
            self.assertEqual(cfg.get('tema'),'acik')
            cfg.set('colorblind_mode',False)
            self.assertEqual(UserSettings(directory).get('tema'),'acik')

    def test_high_visibility_palette_for_both_themes(self):
        for light in (False,True):
            qss=colorblind_styles(light)
            for token in ('#00dfff','#ffed00','OrderDoneTag','BoxProgress','OrderReviewNew','ProductionMetric','OrderRow[orderStatus="tamamlandi"]'):
                self.assertIn(token,qss)
            self.assertNotIn('#36a86e',qss)
