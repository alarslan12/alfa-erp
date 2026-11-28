"""Windows GUI smoke checks against the Firebase desktop edition."""
import os, sys, tempfile, unittest
from unittest.mock import patch

class OfflineWorkstation:
    paired=False
    token=None
    uid=None

@unittest.skipUnless(sys.platform=='win32','Native GUI checks run on Windows CI')
class WindowsGuiTests(unittest.TestCase):
    def test_staff_edition_opens_without_network_or_login(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_firebase_staff_') as data:
            os.environ['ALFA_ERP_DATA_DIR']=data
            from PySide6.QtWidgets import QApplication
            from main import AlfaMain
            app=QApplication.instance() or QApplication(['alfa-staff-ci'])
            with patch('main.OWNER_EDITION',False), \
                 patch('main.Workstation',OfflineWorkstation):
                win=AlfaMain(admin_cloud=None)
                try:
                    self.assertEqual(win.stack.count(),5)
                    self.assertGreater(len(win.db.katalog),0)
                    self.assertEqual(win.inventory_view.count(),2)
                    self.assertTrue(win.db.cloud_required)
                    self.assertFalse(win.device.paired)
                    self.assertIsNone(win.catalog.local_order_btn)
                    self.assertNotIn('derleme',win.subnav)
                    self.assertIsNone(win._derleme_store)
                    self.assertEqual(win.settings_page.nav[1].text(),"Bildirimler && Cihazlar")
                    self.assertFalse(hasattr(win,"announcements_button"))
                    self.assertEqual(win.update_button.size(),win.cloud_connect.size())
                    self.assertEqual(win.report_button.size(),win.settings_btn.size())
                    self.assertEqual(win.update_button.width(),win.update_button.height())
                    self.assertEqual(win.cloud_badge.height(),win.update_button.height())
                    self.assertEqual(win.cloud_badge.width(),110)
                    win.navigate(3)
                    app.processEvents()
                    self.assertEqual(win.stack.currentIndex(),3)
                    # Exercise the real analytics widget after a successful
                    # PIN gate, including viewport resizing and report rebuild.
                    win._analytics_unlocked=True
                    win.navigate(2)
                    app.processEvents()
                    win.analytics.resize(1075,850)
                    app.processEvents()
                    win.analytics.refresh()
                    app.processEvents()
                    self.assertEqual(win.stack.currentIndex(),2)
                finally:
                    win.close()
                    app.processEvents()

    def test_edit_order_quantity_grid_and_delayed_search(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        from pathlib import Path
        from PySide6.QtWidgets import QApplication, QPushButton
        from database import ERPDatabase
        from widgets import Covers
        from editor_siparis import SiparisEditor
        from tema import QSS
        from ayar_yonetimi import theme_styles
        app=QApplication.instance() or QApplication(['alfa-editor-ci'])
        original_style=app.styleSheet()
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='alfa_edit_ci_') as data:
            db=ERPDatabase(root/'KİTAPS.xlsx',data_dir=data)
            codes=list(db.katalog)[:5]
            order=db.yeni_siparis_olustur(
                {'kod':'CI-EDIT','platform':'Manuel','ciro':50,'siparis_turu':''},
                [{'kod':code,'tur':'SB','adet':1,'hazir':0,'koli':0} for code in codes[:4]])
            editor=SiparisEditor(db,Covers(db,root),order['id'],lambda:None,mode='edit')
            try:
                app.setStyleSheet(QSS+theme_styles('koyu'))
                editor.resize(1050,780)
                editor.show()
                app.processEvents()
                editor._reflow_edit_cards()
                self.assertGreaterEqual(editor._edit_columns,2)
                self.assertEqual(editor.rows_lay.getItemPosition(1)[:2],(0,1))
                spin=editor.qty_inputs[codes[0],'SB']
                self.assertEqual(spin.value(),1)
                for theme in ('koyu','acik','kontrast'):
                    app.setStyleSheet(QSS+theme_styles(theme))
                    app.processEvents()
                    self.assertEqual(spin.height(),36)
                    self.assertGreaterEqual(spin.lineEdit().contentsRect().height(),16)
                    self.assertEqual(spin.lineEdit().text(),'1')
                steps=editor._edit_cards[0].findChildren(QPushButton,'OrderEditQtyStep')
                steps[1].click()
                self.assertEqual(spin.value(),2)
                steps[0].click()
                self.assertEqual(spin.value(),1)
                editor._schedule_book_suggestions('abcde')
                self.assertFalse(editor._book_search_timer.isActive())
                self.assertEqual(editor._book_model.rowCount(),0)
                editor._schedule_book_suggestions('abcdef')
                self.assertTrue(editor._book_search_timer.isActive())
                editor._book_search_timer.stop()
                self.assertEqual(editor._resolve_book_code(codes[4]),codes[4])
                label=editor._book_label(db.katalog[codes[4]])
                self.assertEqual(editor._resolve_book_code(label),codes[4])
                editor.add_search.setText(codes[4])
                editor.add_book('SB')
                self.assertEqual(editor.qty_inputs[codes[4],'SB'].value(),1)
                editor.resize(760,650)
                app.processEvents()
                editor._reflow_edit_cards()
                self.assertEqual(editor.qty_inputs[codes[4],'SB'].value(),1)
                self.assertEqual(len(order['kitaplar']),4)  # no mutation before save
            finally:
                editor.close()
                app.setStyleSheet(original_style)
                app.processEvents()

    def test_order_tabs_detach_and_return_without_losing_page(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_tab_ui_') as data:
            os.environ['ALFA_ERP_DATA_DIR']=data
            from pathlib import Path
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QPoint, Qt
            from database import ERPDatabase
            from widgets import Covers
            from editor_siparis import SiparisTakipSekmeleri
            root=Path(__file__).resolve().parents[1]
            app=QApplication.instance() or QApplication(['alfa-tab-ci'])
            db=ERPDatabase(root/'KİTAPS.xlsx',data_dir=data)
            code=next(iter(db.katalog))
            created=db.yeni_siparis_olustur(
                {'kod':'test-001','platform':'Manuel','ciro':50,'siparis_turu':''},
                [{'kod':code,'tur':'SB','adet':2,'hazir':0,'koli':0}])
            hub=SiparisTakipSekmeleri(db,Covers(db,root),lambda:None)
            try:
                hub.add_order(created['id'])
                hub.show()
                app.processEvents()
                self.assertEqual(hub.tabs.count(),1)
                page=hub.tabs.widget(0)
                self.assertIsNotNone(page)
                hub.detach_order(0,QPoint(30,30))
                app.processEvents()
                self.assertEqual(hub.tabs.count(),0)
                self.assertIn(str(created['id']),hub.detached)
                hub.reattach_order(created['id'])
                app.processEvents()
                self.assertEqual(hub.tabs.count(),1)
                self.assertIs(hub.tabs.widget(0),page)
                self.assertFalse(hub.detached)
            finally:
                hub.close()
                app.processEvents()

    def test_order_track_filter_chooses_unboxed_books(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_unboxed_') as data:
            os.environ['ALFA_ERP_DATA_DIR']=data
            from pathlib import Path
            from PySide6.QtWidgets import QApplication
            from database import ERPDatabase
            from widgets import Covers
            from editor_siparis import SiparisEditor
            root=Path(__file__).resolve().parents[1]
            app=QApplication.instance() or QApplication(['alfa-filter-ci'])
            db=ERPDatabase(root/'KİTAPS.xlsx',data_dir=data)
            code=next(iter(db.katalog))
            order=db.yeni_siparis_olustur(
                {'kod':'test-002','platform':'Manuel','ciro':50,'siparis_turu':''},
                [{'kod':code,'tur':'SB','adet':1,'hazir':0,'koli':0}])
            db.siparis_durumunu_degistir(order,'aktif')
            editor=SiparisEditor(db,Covers(db,root),order['id'],lambda:None,
                                 mode='track',embedded=True)
            try:
                self.assertEqual(editor._visible_track_codes(),(code,))
                editor.only_unboxed.setChecked(True)
                app.processEvents()
                self.assertEqual(editor._visible_track_codes(),(code,))
                editor.only_unprepared.setChecked(True)
                app.processEvents()
                self.assertFalse(editor.only_unboxed.isChecked())
                self.assertTrue(editor.only_unprepared.isChecked())
            finally:
                editor.close()
                app.processEvents()

    def test_initial_note_popup_immediate_local_ack_and_click_routing(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_notice_ui_') as data:
            from pathlib import Path
            from PySide6.QtWidgets import QApplication, QDialog, QLabel
            from database import ERPDatabase
            from widgets import Covers
            from ekran_siparis import SiparisView
            from siparis_uyari_ui import OrderNoticeDialog
            from siparis_uyari import pending_notice
            app=QApplication.instance() or QApplication(['alfa-notice-ci'])
            root=Path(__file__).resolve().parents[1]
            db=ERPDatabase(root/'KİTAPS.xlsx',data_dir=data)
            code=next(iter(db.katalog))
            def order(note):
                return db.yeni_siparis_olustur(
                    {'kod':'CI','platform':'Manuel','ciro':50,'siparis_turu':'','order_note':note},
                    [{'kod':code,'tur':'SB','adet':1,'hazir':0,'koli':0}])
            covers=Covers(db,root)
            first=order('23 numaralı kitap')
            second=order('Ayrı paket')
            view=SiparisView(db,covers,admin_mode=True)
            def review(dialog):
                labels=[w.text() for w in dialog.findChildren(QLabel)]
                self.assertFalse(any(s.startswith('Önce:') or s.startswith('Yeni:') for s in labels))
                dialog.checked.setChecked(True)
                dialog._confirm()
                return dialog.result()
            try:
                with patch.object(OrderNoticeDialog,'exec',review):
                    view.open_editor(first['id'],'notice')
                    app.processEvents()
                    self.assertFalse(pending_notice(first))
                    self.assertNotIn('track_hub',view.windows)
                    view.open_editor(second['id'],'track')
                    app.processEvents()
                    self.assertFalse(pending_notice(second))
                    self.assertIn('track_hub',view.windows)
            finally:
                for w in list(view.windows.values()):w.close()
                view.close()
                app.processEvents()

    def test_owner_edition_opens_without_backend_calls(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        with tempfile.TemporaryDirectory(prefix='alfa_firebase_owner_') as data:
            os.environ['ALFA_ERP_DATA_DIR']=data
            from PySide6.QtWidgets import QApplication
            from main import AlfaMain
            app=QApplication.instance() or QApplication(['alfa-owner-ci'])
            with patch('main.OWNER_EDITION',True), \
                 patch('main.Workstation',OfflineWorkstation):
                win=AlfaMain(admin_cloud=None)
                try:
                    self.assertEqual(win.stack.count(),5)
                    self.assertIsNotNone(win.settings_page)
                    self.assertEqual(win.settings_page.stack.count(),4)
                    self.assertEqual(win.settings_page.nav[1].text(),"Bildirimler && Cihazlar")
                    self.assertEqual(win.settings_page.notification_split.count(),2)
                    self.assertEqual(win.settings_page._owner_tabs["devices"],1)
                    self.assertEqual(win.settings_page._owner_tabs["errors"],3)
                    self.assertEqual(win.update_button.size(),win.cloud_connect.size())
                    self.assertEqual(win.settings_btn.size(),win.cloud_connect.size())
                    self.assertFalse(hasattr(win,"announcements_button"))
                    self.assertEqual(win.update_button.width(),48)
                    self.assertEqual(win.update_button.height(),48)
                    self.assertEqual(win.cloud_badge.width(),110)
                    self.assertEqual(win.update_button.accessibleName(),"Duyurular ve Güncelleme Merkezi")
                    with patch("main.AnnouncementsDialog") as dialog:
                        win.update_button.click()
                        dialog.assert_called_once()
                    self.assertTrue(callable(win.db.owner_admin_request))
                    self.assertIn('derleme',win.subnav)
                    self.assertIn('derleme_bitti',win.subnav)
                    self.assertIsNotNone(win.catalog.local_order_btn)
                    self.assertIsNone(win._derleme_store)
                    code=next(iter(win.db.katalog))
                    win.catalog.cart={code:{'SB':2,'RNK':0}}
                    win.catalog.revenue.setValue(35.50)
                    before=len(win.db.siparisler)
                    with patch.object(win.db,'yeni_siparis_olustur',side_effect=AssertionError('Cloud route used')) as cloud:
                        win.catalog.make_order(local=True)
                        cloud.assert_not_called()
                    self.assertEqual(len(win.db.siparisler),before)
                    win.open_order_status('derleme')
                    view=win._derleme_view
                    self.assertIs(win.stack.currentWidget(),view)
                    self.assertEqual(view.metrics['siparis'].text(),'1')
                    self.assertEqual(view.metrics['kitap'].text(),'2')
                    self.assertEqual(view.metrics['ciro_kurus'].text(),'35,50 TL')
                    view.table.selectRow(0)
                    with patch('ekran_derleme_havuzu.confirm',return_value=True):
                        view.change_completion()
                    self.assertEqual(view.metrics['siparis'].text(),'0')
                    win.open_order_status('derleme_bitti')
                    self.assertEqual(view.metrics['siparis'].text(),'1')
                    self.assertEqual(view.metrics['kitap'].text(),'2')
                    self.assertEqual(view.metrics['ciro_kurus'].text(),'35,50 TL')
                    self.assertEqual(len(win.db.siparisler),before)
                    app.processEvents()
                finally:
                    win.close()
                    app.processEvents()

if __name__=='__main__':
    unittest.main()
