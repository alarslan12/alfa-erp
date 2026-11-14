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

    def test_existing_packed_card_recolors_in_place(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication,QFrame
        from kart_siparis import set_boxed_card_style,refresh_accessible_order_widgets
        app=QApplication.instance() or QApplication(['alfa-colorblind-ci'])
        before=app.property('alfa_colorblind')
        before_theme=app.property('alfa_theme')
        card=QFrame(); card.setObjectName('TrackBookCard')
        try:
            app.setProperty('alfa_theme','koyu')
            app.setProperty('alfa_colorblind',False)
            set_boxed_card_style(card,{'adet':2,'koli':2})
            self.assertIn('#36a86e',card.styleSheet())
            app.setProperty('alfa_colorblind',True)
            refresh_accessible_order_widgets()
            self.assertIn('#00dfff',card.styleSheet())
            set_boxed_card_style(card,{'adet':2,'koli':1})
            self.assertEqual(card.styleSheet(),'')
            set_boxed_card_style(card,{'adet':2,'koli':2})
            app.setProperty('alfa_colorblind',False)
            refresh_accessible_order_widgets()
            self.assertIn('#36a86e',card.styleSheet())
        finally:
            card.close()
            app.setProperty('alfa_colorblind',before)
            app.setProperty('alfa_theme',before_theme)
            refresh_accessible_order_widgets()
