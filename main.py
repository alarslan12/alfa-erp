"""ALFA ERP Desktop - Qt/PySide6 yerel Windows masaüstü uygulaması."""
import sys, traceback, os, json
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
from urun_katalogu import GeneralProductCatalog
from ekran_ayarlar import SettingsPage
from alfa_rtdb import Workstation
from bulut_canli import Sync
from ayar_yonetimi import UserSettings, theme_styles
from widgets import text,button,panel,Covers

ROOT=Path(__file__).resolve().parent
VERSION='6.4.0'
OWNER_EDITION=(ROOT/'YONETICI_SURUMU.flag').exists()


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
        self._analytics_unlocked=False
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
        self.cloud_badge=text('◌ Bağlanıyor…','Tiny')
        self.cloud_badge.setToolTip('Siparişler yalnızca eşleştirilmiş cihazlarda buluta aktarılır.')
        right_row.addWidget(self.cloud_badge)
        self.cloud_connect=QPushButton('Buluta bağla')
        self.cloud_connect.setObjectName('CloudConnect')
        self.cloud_connect.setToolTip(
            'İlk kurulumda bir kez cihazı yetkilendir; sonraki açılışlar girişsiz.')
        self.cloud_connect.clicked.connect(self.connect_cloud)
        right_row.addWidget(self.cloud_connect)
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
        self.general_catalog=GeneralProductCatalog(self.db)
        self.catalog_host=QWidget()
        self.catalog_host.setObjectName('CatalogHost')
        catalog_root=QVBoxLayout(self.catalog_host)
        catalog_root.setContentsMargins(0,0,0,0)
        catalog_root.setSpacing(6)
        catalog_choices=QHBoxLayout()
        catalog_choices.setSpacing(7)
        self.catalog_tabs=[]
        for number,label in enumerate(('▦  Kitap Kataloğu','▤  Genel Ürünler')):
            tab=button(label,'SettingsNav')
            tab.setCheckable(True)
            tab.clicked.connect(lambda checked=False,n=number:self.select_catalog(n))
            self.catalog_tabs.append(tab)
            catalog_choices.addWidget(tab)
        catalog_choices.addStretch()
        catalog_root.addLayout(catalog_choices)
        self.catalog_view=QStackedWidget()
        self.catalog_view.addWidget(self.catalog)
        self.catalog_view.addWidget(self.general_catalog)
        catalog_root.addWidget(self.catalog_view,1)
        self.catalog_tabs[0].setChecked(True)
        self.title_line.insertWidget(1,self.catalog.toolbar,1)
        self.orders=SiparisView(self.db,self.covers,self.open_book_pool,admin_mode=OWNER_EDITION)
        self.analytics=AnalitikView(self.db,lambda sid:self.orders.open_editor(sid,'track'))
        self.inventory=EnvanterView(self.db)
        if OWNER_EDITION:
            from yonetici_kompakt import OwnerSettingsPage
            self.settings_page=OwnerSettingsPage(self.db,self.config,self.admin_cloud)
        else:
            self.settings_page=SettingsPage(self.db,self.config)
        for page in (self.catalog_host,self.orders,self.analytics,self.inventory,self.settings_page):self.stack.addWidget(page)
        self.device=Workstation()
        if OWNER_EDITION:
            from rtdb_owner_admin import admin_request
            # Owner role verified with RTDB Security Rules on every write.
            self.db.owner_admin_request=lambda action,**kw:admin_request(self.device,action,**kw)
            self.analytics.cloud_admin_request=self.db.owner_admin_request
        if not OWNER_EDITION:
            # Çalışan bilgisayarına işlem günlüğünün yerel kopyasını yazma.
            class NoStaffAudit:
                def record_diff(self,*_a,**_k):return 0
                def record_action(self,*_a,**_k):return None
            self.db.audit=NoStaffAudit()
        self.db.cloud_required=True
        self.live=Sync(self.device,self.db,parent=self)
        if not self.device.paired:
            self.cloud_badge.setText('◌ Buluta bağlı değil')
            self.cloud_badge.setToolTip(
                'Uygulama girişsiz açıldı. Katalog yerelde kullanılabilir. '
                'Bulut siparişlerini görmek ve değiştirmek için cihazı bir kez eşleştir.')
        self.cloud_connect.setText(
            'Cihaz yetkisi' if OWNER_EDITION else
            'Yeniden eşleştir' if self.device.paired else 'Buluta bağla')
        self.live.changed.connect(self._cloud_orders_changed)
        self.live.status.connect(self._cloud_status)
        self.catalog.order_created.connect(self.order_created)
        self._auto_enroll_worker=None
        self._auto_enroll_retry=QTimer(self)
        self._auto_enroll_retry.setInterval(60000)
        self._auto_enroll_retry.timeout.connect(self.try_auto_enrollment)
        self.navigate(0)
        # A private setup bundle can provide the one-time code without typing
        # or requiring an owner/staff login. Never block the first window.
        QTimer.singleShot(350,self.try_auto_enrollment)

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
        # Use the same branded icon as the native EXE, taskbar and installer.
        logo=ROOT/'assets'/'icons'/('alfa_yonetici.ico' if OWNER_EDITION else 'alfa_personel.ico')
        if logo.is_file():
            return QIcon(str(logo))
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
        self.catalog.toolbar.setVisible(index==0 and self.catalog_view.currentIndex()==0)
        for key,tab in self.subnav.items():
            tab.setChecked(index==1 and key==sub)

    def select_catalog(self,index):
        """Keep the printed-book ordering UI intact; offer a separate shared product master."""
        self.catalog_view.setCurrentIndex(index)
        for n,tab in enumerate(self.catalog_tabs):
            tab.setChecked(n==index)
        self.catalog.toolbar.setVisible(self.stack.currentIndex()==0 and index==0)
        self.page_title.setText('Kitap kataloğu' if index==0 else 'Genel ürün kataloğu')
        if index==1:self.general_catalog.refresh()

    def try_auto_enrollment(self):
        """Old Supabase setup tickets are intentionally ignored in Firebase mode."""
        self._auto_enroll_retry.stop()

    def connect_cloud(self):
        """One-time anonymous Firebase identity plus owner device approval."""
        from firebase_pair_ui import PairDialog
        dialog=PairDialog(client=self.device,owner=OWNER_EDITION,parent=self)
        if dialog.exec()!=dialog.DialogCode.Accepted:
            return
        # PairDialog shares self.device: identity was already persisted by the
        # registration worker. reload() here can race concurrent Firebase
        # refresh/SSE threads and reset a working token unnecessarily.
        if not self.device.paired:
            QMessageBox.warning(self,'Firebase bağlantısı',
                'Cihaz oturumu kaydedilemedi. Veriler yerelde korunuyor.')
            return
        self._auto_enroll_retry.stop()
        self.cloud_connect.setEnabled(False)
        QTimer.singleShot(150, self._activate_cloud_after_pairing)

    def _activate_cloud_after_pairing(self):
        try:
            if not self.device.paired:
                raise RuntimeError("Firebase cihaz kimliği kaydedilemedi.")
            # An already-paired machine started Sync at application launch.
            # Refresh it in place instead of starting its timers/watchers again.
            if self.live.timer.isActive():
                self.live.force_pull=True
                self.live._pull_retry_after=0
                self.live.pull()
            else:
                self.live.activate()
            self.cloud_connect.setText('Cihaz yetkisi')
            self.cloud_badge.setToolTip('Firebase Realtime Database eşitlemesi kontrol ediliyor.')
        except Exception as exc:
            self.cloud_badge.setText('◌ Bulut bağlantısı beklemede')
            QMessageBox.warning(self,'Firebase eşitleme başlatılamadı',
                str(exc) + '\\nCihaz kaydı korunuyor; yeniden yetkilendirme gerekmez.')
        finally:
            self.cloud_connect.setEnabled(True)

    def navigate(self,index):
        if index==2 and not self._analytics_unlocked:
            from analytics_access import AnalyticsGate
            pin=AnalyticsGate(owner=OWNER_EDITION,parent=self)
            if pin.exec()!=pin.DialogCode.Accepted:
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
            self.general_catalog.refresh()
        if any(x not in ('__katalog__','__muhasebe__','__envanter__') for x in ids):
            self.orders.refresh()
            if self.bookpool and self.bookpool.isVisible():self.bookpool.refresh()
        if self.stack.currentWidget() is self.analytics:self.analytics.refresh()

    def _cloud_status(self,online,message):
        self.setWindowTitle('ALFA ERP · '+('Bulut bağlı' if online else 'Bağlantı bekleniyor'))
        self.setToolTip(message)
        conflicts=self.db.unreviewed_cloud_conflicts
        if conflicts:
            count=len(conflicts)
            reason=str(conflicts[-1].get('reason') or 'Bilinmeyen işlem çakışması')
            self.cloud_badge.setText(f'⚠ {count} geçmiş çakışma' if online
                else f'◌ Eşitleme hatası · {count} eski kayıt')
            self.cloud_badge.setToolTip(
                ('Bulut bağlı.\n' if online else 'Güncel eşitleme hatası: '+message[:190]+'\n')
                +'Bunlar daha önce reddedilmiş ve arşivlenmiş işlemlerdir; '
                'şu anda bekleyen kuyruk sayısı değildir.\n'
                'Ayarlar → İşlem günlüğü → Eski bulut hatalarını incele.\n'
                +reason[:220])
            previous=getattr(self,'_last_conflict_notice',None)
            self._last_conflict_notice=count
            if previous is not None and count>previous:
                self.statusBar().showMessage('Bulut işlemi reddedildi: '+reason[:170],20000)
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

def _install_error_diagnostics():
    """Persist sanitized callback failures; no customer rows or tokens logged."""
    import datetime
    from pathlib import Path as _Path
    root=_Path(os.environ.get('ALFA_ERP_DATA_DIR') or
               _Path(os.environ.get('LOCALAPPDATA') or _Path.home())/'AlfaERP')
    errors=root/'logs'
    errors.mkdir(parents=True,exist_ok=True)
    outfile=errors/'last_error.txt'
    # Capture native Qt/PySide fatal aborts, which bypass sys.excepthook.
    # Only technical Python stack frames are written, not credentials or rows.
    try:
        import faulthandler
        native_log=(errors/'fatal_error.log').open('a',encoding='utf-8')
        faulthandler.enable(file=native_log,all_threads=True)
        globals()['_alfa_native_log_handle']=native_log
    except (OSError,RuntimeError,ValueError):
        pass
    def report(error_type,error,tb):
        try:
            trace=traceback.extract_tb(tb)
            lines=[datetime.datetime.now().isoformat(timespec='seconds'),
                   'Exception: '+error_type.__name__,
                   *('  '+_Path(frame.filename).name+':'+str(frame.lineno)+
                     ' in '+frame.name for frame in trace[-20:])]
            outfile.write_text('\\n'.join(lines)+'\\n',encoding='utf-8')
        except Exception:pass
        try:
            QMessageBox.critical(None,'ALFA ERP beklenmedik hata',
                 'Uygulamada beklenmedik bir hata oluştu.\\n'
                 'Hata türü: '+error_type.__name__+'\\n'
                 'Kayıt: '+str(outfile)+'\\n'
                 'Cihazı yeniden yetkilendirmene gerek yok.')
        except Exception:pass
        # Do not allow the default PySide6 exception hook to abort the process.
    sys.excepthook=report


def start():
    _install_error_diagnostics()
    app=QApplication(sys.argv);app.setApplicationName('ALFA ERP');app.setStyle('Fusion')
    app.setStyleSheet(QSS)
    try:
        # Both editions open immediately, without blocking authentication
        # or mandatory enrollment dialogs. A safe, visible one-time activation
        # is available from the app header if this device is not paired.
        main=AlfaMain(admin_cloud=None)
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



if __name__=='__main__':
    sys.exit(start())
