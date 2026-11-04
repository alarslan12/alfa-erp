"""ALFA ERP Desktop - Qt/PySide6 yerel Windows masaüstü uygulaması."""
import sys, traceback, os, hashlib, hmac
from pathlib import Path
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QStackedWidget,
 QLabel,QFrame,QGridLayout,QPushButton,QMessageBox,QInputDialog,QLineEdit)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon,QPixmap,QPainter,QFont,QColor
from database import ERPDatabase
from ekran_katalog import KatalogView
from ekran_siparis import SiparisView
from ekran_kitap_havuzu import SiparisKitapHavuzu
from tema import QSS
from ekran_analitik import AnalitikView
from ekran_envanter import EnvanterView
from ekran_ayarlar import SettingsPage
from alfa_cihaz import Workstation
from bulut_canli import Sync
from ayar_yonetimi import UserSettings, theme_styles
from widgets import text,button,panel,Covers

ROOT=Path(__file__).resolve().parent
VERSION='6.1.3'
OWNER_EDITION=(ROOT/'YONETICI_SURUMU.flag').exists()


# Yerel parola doğrulaması: yalnızca tuzlanmış türetilmiş özet saklanır.
# Windows personel paketi içinde düz metin parola BULUNMAZ.
_ANALYTICS_SALT=bytes.fromhex('df6879d7e2c980a2105f9bca0967d49f8fd2a05a')
_ANALYTICS_CHECK=bytes.fromhex('f8381ac312ac801806484e67072d9234d9f0e4917d975789ab30582688a177e5')

def analytics_password_matches(password):
    digest=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),_ANALYTICS_SALT,260000)
    return hmac.compare_digest(digest,_ANALYTICS_CHECK)

class AlfaMain(QMainWindow):
    def __init__(self,admin_cloud=None):
        super().__init__()
        self.admin_cloud=admin_cloud
        user_root = (os.environ.get('ALFA_ERP_DATA_DIR') or
                     str(Path(os.environ.get('LOCALAPPDATA') or (Path.home()/'.local'/'share'))/'AlfaERP'))
        self.config=UserSettings(user_root)
        custom=self.config.get('ozel_katalog')
        chosen=Path(custom) if custom and Path(custom).is_file() else ROOT/'KİTAPS.xlsx'
        self.db=ERPDatabase(chosen, data_dir=user_root)
        QApplication.instance().setProperty('alfa_theme', self.config.get('tema', 'koyu'))
        QApplication.instance().setStyleSheet(QSS + theme_styles(self.config.get('tema', 'koyu')))
        if not self.db.katalog:
            raise RuntimeError('Katalog okunamadı; KİTAPS.xlsx dosyasını kontrol edin.')
        self.covers=Covers(self.db,ROOT)
        self.setWindowTitle('ALFA ERP · Desktop')
        self.setMinimumSize(860,620)
        self.resize(1480,900)
        self.setWindowIcon(self.make_icon())
        self._last_orders_tab='havuz'
        self._analytics_unlocked=OWNER_EDITION
        self.bookpool=None

        holder=QWidget();holder.setObjectName('AppRoot')
        self.setCentralWidget(holder)
        root=QVBoxLayout(holder);root.setContentsMargins(0,0,0,0);root.setSpacing(0)

        # Ana ERP gezintisi: katalog, sipariş, analitik ve envanter.
        header=QFrame();header.setObjectName('Header')
        main_bar=QGridLayout(header)
        main_bar.setContentsMargins(14,0,14,0)
        main_bar.setColumnStretch(0,1)
        main_bar.setColumnStretch(2,1)
        nav_box=QWidget();nav_row=QHBoxLayout(nav_box)
        nav_row.setContentsMargins(0,0,0,0);nav_row.setSpacing(8)
        self.nav={}
        for index,label in enumerate(('▦  Katalog','▤  Siparişler','◈  Analitik','▥  Envanter')):
            action=button(label,'Nav')
            action.setCheckable(True)
            action.setAccessibleName(label.strip())
            if index==0:
                action.clicked.connect(lambda checked=False:self.navigate(0))
            elif index==1:
                action.clicked.connect(lambda checked=False:self.open_last_orders())
            elif index==2:
                action.clicked.connect(lambda checked=False:self.navigate(2))
            else:
                action.clicked.connect(lambda checked=False:self.navigate(3))
            self.nav[index]=action
            nav_row.addWidget(action)
        main_bar.addWidget(nav_box,0,1,Qt.AlignmentFlag.AlignCenter)
        right_box=QWidget();right_row=QHBoxLayout(right_box)
        right_row.setContentsMargins(0,0,0,0);right_row.setSpacing(10)
        settings_btn=button('⚙','SettingsGear')
        settings_btn.setToolTip('Ayarlar · '+('Excel, cihazlar, işlem günlüğü, PDF' if OWNER_EDITION else 'Görünüm ve PDF klasörü'))
        settings_btn.setAccessibleName('Ayarlar menüsünü aç')
        settings_btn.setCheckable(True)
        settings_btn.clicked.connect(lambda checked=False:self.navigate(4))
        self.settings_btn=settings_btn
        right_row.addWidget(settings_btn)
        self.cloud_badge=text('● Bağlanıyor…','Tiny')
        self.cloud_badge.setToolTip('Yerel işlemler arka planda buluta aktarılır.')
        right_row.addWidget(self.cloud_badge)
        right_row.addWidget(text('v'+VERSION,'Tiny'))
        main_bar.addWidget(right_box,0,2,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        header.setFixedHeight(57)
        root.addWidget(header)

        # Siparişler'e tıklanınca hemen ALTINDA, sabit yatay ikinci menü.
        self.orders_subbar=QFrame();self.orders_subbar.setObjectName('OrdersSubbar')
        subrow=QHBoxLayout(self.orders_subbar)
        subrow.setContentsMargins(12,0,12,0);subrow.setSpacing(3)
        subrow.addStretch()
        self.subnav={}
        sub_entries=(('havuz','Sipariş Havuzu'),('aktif','Aktif Siparişler'),
                     ('tamamlandi','Tamamlanan'))
        for key,label in sub_entries:
            tab=button(label,'OrdersSubnav')
            tab.setCheckable(True)
            tab.setProperty('orderStage', key)
            tab.setToolTip(f'{label} ekranını aç')
            tab.clicked.connect(lambda checked=False,k=key:
                                self.open_book_pool() if k=='pool' else self.open_order_status(k))
            subrow.addWidget(tab)
            self.subnav[key]=tab
        subrow.addStretch()
        self.orders_subbar.setFixedHeight(32)
        self.orders_subbar.setVisible(False)
        root.addWidget(self.orders_subbar)

        content=QWidget();content.setObjectName('AppBody')
        self.body=QVBoxLayout(content)
        self.body.setContentsMargins(13,5,13,8)
        self.body.setSpacing(7)

        # Katalog özel başlığı korunur; siparişlerde tekrar eden büyük başlık yok.
        self.title_widget=QWidget()
        self.title_line=QHBoxLayout(self.title_widget)
        self.title_line.setContentsMargins(0,0,0,0)
        self.title_line.setSpacing(12)
        self.page_title=text('Kitap kataloğu','PageTitle')
        self.title_line.addWidget(self.page_title)
        self.title_line.addStretch()
        self.body.addWidget(self.title_widget)

        self.stack=QStackedWidget()
        self.body.addWidget(self.stack,1)
        root.addWidget(content,1)
        self.catalog=KatalogView(self.db,self.covers)
        self.title_line.insertWidget(1,self.catalog.toolbar,1)
        self.orders=SiparisView(self.db,self.covers,self.open_book_pool,admin_mode=OWNER_EDITION)
        self.analytics=AnalitikView(self.db,lambda sid:self.orders.open_editor(sid,'track'))
        self.inventory=EnvanterView(self.db)
        if OWNER_EDITION:
            from yonetici_kompakt import OwnerSettingsPage
            self.settings_page=OwnerSettingsPage(self.db,self.config,self.admin_cloud)
        else:
            self.settings_page=SettingsPage(self.db,self.config)
        for page in (self.catalog,self.orders,self.analytics,self.inventory,self.settings_page):self.stack.addWidget(page)
        self.device=Workstation()
        if OWNER_EDITION and self.admin_cloud is not None:
            from yonetici_giris import AdminWorkstation, admin_request
            self.db.owner_admin_request=lambda action,**kw:admin_request(self.admin_cloud,action,**kw)
            self.device=AdminWorkstation(self.admin_cloud,self.device.token)
            self.analytics.cloud_admin_request=self.db.owner_admin_request
        if not OWNER_EDITION:
            # Çalışan bilgisayarına işlem günlüğünün yerel kopyasını yazma.
            class NoStaffAudit:
                def record_diff(self,*_a,**_k):return 0
                def record_action(self,*_a,**_k):return None
            self.db.audit=NoStaffAudit()
        self.db.cloud_required=True
        self.live=Sync(self.device,self.db,parent=self)
        self.live.changed.connect(self._cloud_orders_changed)
        self.live.status.connect(self._cloud_status)
        self.catalog.order_created.connect(self.order_created)
        self.navigate(0)

    def showEvent(self,event):
        super().showEvent(event)
        if not getattr(self,'_screen_linked',False):
            handle=self.windowHandle()
            if handle:
                handle.screenChanged.connect(self._attach_screen)
                self._screen_linked=True
                self._attach_screen(handle.screen())

    def _attach_screen(self,screen):
        if screen is None:
            return
        if getattr(self,'_attached_screen',None) is not screen:
            old=getattr(self,'_attached_screen',None)
            if old is not None:
                try: old.availableGeometryChanged.disconnect(self._screen_geometry_changed)
                except (RuntimeError,TypeError): pass
            screen.availableGeometryChanged.connect(self._screen_geometry_changed)
            self._attached_screen=screen
        self._screen_changed(screen)

    def _screen_geometry_changed(self,_geometry):
        self._screen_changed(getattr(self,'_attached_screen',None))

    def _screen_changed(self,screen):
        # Qt 6 automatically handles screen DPI. Keep the current window within
        # the newly selected monitor and let its layouts recalculate in place.
        if screen is None:
            return
        area=screen.availableGeometry()
        new_w=min(self.width(),max(760,area.width()-24))
        new_h=min(self.height(),max(540,area.height()-24))
        self.setMinimumSize(min(760,new_w),min(540,new_h))
        if self.width()!=new_w or self.height()!=new_h:
            self.resize(new_w,new_h)
        frame=self.frameGeometry()
        if not area.intersects(frame):
            frame.moveCenter(area.center())
            self.move(frame.topLeft())

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'body'):
            narrow=self.width()<1120
            self.body.setContentsMargins(7 if narrow else 13,4 if narrow else 5,7 if narrow else 13,6 if narrow else 8)

    def make_icon(self):
        pix=QPixmap(64,64);pix.fill(QColor('#f1b46f'))
        paint=QPainter(pix)
        paint.setPen(QColor('#151c28'))
        font=QFont('Segoe UI',35);font.setBold(True)
        paint.setFont(font)
        paint.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,'A')
        paint.end()
        return QIcon(pix)

    def open_last_orders(self):
        if self._last_orders_tab=='pool':
            self.open_book_pool()
        else:
            self.open_order_status(self._last_orders_tab)

    def _mark_navigation(self,index,sub=None):
        self.nav[0].setChecked(index==0)
        self.nav[1].setChecked(index==1)
        self.nav[2].setChecked(index==2)
        self.nav[3].setChecked(index==3)
        self.settings_btn.setChecked(index==4)
        self.orders_subbar.setVisible(index==1)
        self.title_widget.setVisible(index==0)
        self.catalog.toolbar.setVisible(index==0)
        for key,tab in self.subnav.items():
            tab.setChecked(index==1 and key==sub)

    def navigate(self,index):
        if index==2 and not self._analytics_unlocked:
            password,ok=QInputDialog.getText(self,'Analitik Erişimi',
                'Analitik ekranını açmak için yetki parolasını girin:',QLineEdit.EchoMode.Password)
            if not ok or not analytics_password_matches(password):
                if ok: QMessageBox.warning(self,'Analitik','Parola doğru değil.')
                return
            self._analytics_unlocked=True
        if index==1:
            self.open_last_orders()
            return
        self.stack.setCurrentIndex(index)
        self._mark_navigation(index)
        if index==2:
            self.analytics.refresh()
        elif index==3:
            self.inventory.refresh()
        elif index==4:
            self.settings_page.show_tab(self.settings_page.current_tab)

    def _cloud_orders_changed(self,ids):
        if not ids:return
        if '__katalog__' in ids:
            self.catalog.refresh_grid()
            self.catalog.update_cart()
        if '__envanter__' in ids:
            self.inventory.refresh()
        if any(x not in ('__katalog__','__muhasebe__','__envanter__') for x in ids):
            self.orders.refresh()
            if self.bookpool and self.bookpool.isVisible():self.bookpool.refresh()
        if self.stack.currentWidget() is self.analytics:self.analytics.refresh()

    def _cloud_status(self,online,message):
        self.setWindowTitle('ALFA ERP · '+('Bulut bağlı' if online else 'Bağlantı bekleniyor'))
        self.setToolTip(message)
        conflicts=getattr(self.db,'_conflicts',[])
        if conflicts:
            count=len(conflicts)
            reason=str(conflicts[-1].get('reason') or 'Bilinmeyen işlem çakışması')
            self.cloud_badge.setText(f'⚠ {count} işlem onaylanmadı')
            self.cloud_badge.setToolTip(
                'İşlem sunucuda reddedildi; yerel optimistik görünüm geri alınabilir.\n'
                +reason[:280]+'\nKayıt: alfa_outbox.json / conflicts')
            if count>getattr(self,'_last_conflict_notice',0):
                self._last_conflict_notice=count
                self.statusBar().showMessage('Bulut işlemi kaydedilemedi: '+reason[:170],20000)
            return
        marker='● ' if online else '◌ '
        self.cloud_badge.setText(marker + ('Bulut bağlı' if online and not self.db.pending_count
            else f'{self.db.pending_count} işlem sırada' if online else 'Çevrimdışı · kuyrukta'))
        self.cloud_badge.setToolTip(message)

    def open_order_status(self,status):
        if status not in ('havuz','aktif','tamamlandi'):
            return
        self._last_orders_tab=status
        self.stack.setCurrentWidget(self.orders)
        self._mark_navigation(1,status)
        self.orders.change_status(status)
        if status=='havuz':
            self.live.pull()

    def open_book_pool(self):
        """Genel bakış, ana ekranı değiştirmeden bağımsız popup olarak açılır."""
        if self.bookpool is None:
            self.bookpool = SiparisKitapHavuzu(self.db, self.covers,
                                               self.navigate_to_order, self)
        else:
            self.bookpool.refresh()
        self.bookpool.showNormal()
        self.bookpool.raise_()
        self.bookpool.activateWindow()

    def navigate_to_order(self,sid):
        order=next((o for o in self.db.siparisler
                    if str(o.get('id'))==str(sid)),None)
        if not order:
            QMessageBox.warning(self,'Sipariş bulunamadı',
                                f'#{sid} numaralı sipariş artık mevcut değil.')
            self.bookpool.refresh()
            return
        # Kitap havuzu yerinde kalsın; ilgili sipariş detayını ikinci popup'ta aç.
        self.orders.open_editor(sid, 'track')

    def backup(self):
        try:
            path=self.db.yedek_al()
            QMessageBox.information(self,'Yedek oluşturuldu',
                                    f'Siparişlerin kopyası kaydedildi:\n{path}')
        except Exception as exc:
            QMessageBox.warning(self,'Yedekleme hatası',str(exc))

    def order_created(self):
        self.open_order_status('havuz')

def start():
    app=QApplication(sys.argv);app.setApplicationName('ALFA ERP');app.setStyle('Fusion')
    app.setStyleSheet(QSS)
    try:
        admin_cloud=None
        if OWNER_EDITION:
            from yonetici_giris import AdminLogin
            prompt=AdminLogin()
            if prompt.exec()!=prompt.DialogCode.Accepted:
                return 0
            admin_cloud=prompt.cloud
        else:
            # Shared main.py is the entry point for BOTH frozen editions.
            # On normal staff launch, enroll once using the optional file
            # beside the Setup.exe. --self-test bypasses start() entirely.
            from alfa_cihaz import get_token
            if not get_token():
                from auto_eslestir import main as enroll_staff
                try:
                    enroll_staff(install_startup=False)
                except Exception as exc:
                    QMessageBox.critical(None,'ALFA ERP · Cihaz eşleştirme',
                      'Cihaz henüz eşleştirilmedi. Tek kullanımlık kurulum '
                      'dosyasını Setup.exe ile aynı klasöre koyup yeniden '
                      'kurun veya yöneticiden yeni cihaz kodu isteyin.\n\n'
                      +str(exc)[:300])
                    return 1
        main=AlfaMain(admin_cloud=admin_cloud)
        # Mevcut ekranın kullanılabilir alanına göre ölçeklendir ve tam ortala.
        screen=app.primaryScreen()
        if screen:
            area=screen.availableGeometry()
            width=min(1600,max(780,area.width()-32))
            height=min(960,max(580,area.height()-32))
            main.setMinimumSize(min(860,width),min(620,height))
            main.resize(width,height)
            frame=main.frameGeometry()
            frame.moveCenter(area.center())
            main.move(frame.topLeft())
        main.show();return app.exec()
    except Exception as exc:
        QMessageBox.critical(None,'ALFA ERP başlangıç hatası',str(exc)+'\n\n'+traceback.format_exc(limit=3))
        return 1



def release_smoke_test():
    """Offline startup and navigation probe used by Windows CI after PyInstaller.

    Uses a fresh temporary directory and NEVER connects to production Supabase.
    """
    import json as _json
    import tempfile as _tempfile
    import traceback as _traceback
    from pathlib import Path as _Path
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    class _OfflineDevice:
        paired=False
        token=None
    original_workstation=globals()['Workstation']
    globals()['Workstation']=_OfflineDevice
    with _tempfile.TemporaryDirectory(prefix='alfa_win_smoke_') as data_path:
        os.environ['ALFA_ERP_DATA_DIR']=data_path
        app=QApplication.instance() or QApplication(['AlfaERP-smoke'])
        app.setApplicationName('ALFA ERP CI')
        app.setStyle('Fusion')
        window=None
        try:
            window=AlfaMain(admin_cloud=None)
            if window.stack.count()!=5 or not window.db.katalog:
                raise RuntimeError('Missing expected ERP page or book catalog')
            # Headless test cannot answer the staff Analytics password dialog.
            # Bypass the dialog only in this offline self-test invocation.
            # Normal staff startup still requires the Analytics password.
            window._analytics_unlocked = True
            for index in range(5):
                window.navigate(index)
                app.processEvents()
                if window.stack.currentIndex()!=index:
                    raise RuntimeError(f'Navigation failed: {index}')
            report={'ok': True, 'version': VERSION, 'pages':5,
                    'books':len(window.db.katalog), 'mode':'owner' if OWNER_EDITION else 'staff'}
            code=0
        except Exception:
            report={'ok':False, 'traceback':_traceback.format_exc()}
            code=2
        finally:
            if window is not None:
                window.close()
            app.quit()
        result_path=os.environ.get('ALFA_SMOKE_RESULT_PATH')
        if result_path:
            _Path(result_path).write_text(_json.dumps(report,ensure_ascii=False),encoding='utf-8')
        globals()['Workstation']=original_workstation
        return code

if __name__=='__main__':
    sys.exit(release_smoke_test() if '--self-test' in sys.argv else start())
