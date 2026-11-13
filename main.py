"""ALFA ERP Desktop - Qt/PySide6 yerel Windows masaüstü uygulaması."""
import sys, traceback, os, json
from pathlib import Path
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QStackedWidget,
 QLabel,QFrame,QGridLayout,QPushButton,QMessageBox,QInputDialog,QLineEdit,QSystemTrayIcon)
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
from alfa_hatalar import install_reporter,record_error,connect_device
from guncelleme_arayuzu import CheckWorker,should_check_today,mark_checked
from duyuru_merkezi import AnnouncementsDialog,ManualReportDialog

ROOT=Path(__file__).resolve().parent
VERSION='2.0.25'
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
        main_bar.setColumnStretch(0,0)
        main_bar.setColumnStretch(1,1)
        main_bar.setColumnStretch(2,0)
        self.brand=QLabel('ALFA ERP · '+('YÖNETİCİ' if OWNER_EDITION else 'PERSONEL')+'  v'+VERSION)
        self.brand.setObjectName('AlfaEditionBrand')
        self.brand.setStyleSheet('font-size:12px;font-weight:900;padding:0 3px;')
        self.brand.setToolTip('Bu bilgisayarda kurulu ALFA ERP sürümü: v'+VERSION)
        main_bar.addWidget(self.brand,0,0,Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
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
        settings_btn.setToolTip('Ayarlar · '+('Excel, cihazlar, işlem günlüğü, PDF' if OWNER_EDITION else 'Excel katalog, görünüm ve PDF'))
        settings_btn.setAccessibleName('Ayarlar menüsünü aç')
        settings_btn.setCheckable(True)
        settings_btn.clicked.connect(lambda checked=False:self.navigate(4))
        self.settings_btn=settings_btn
        settings_btn.setVisible(True)
        right_row.addWidget(settings_btn)
        self.announcements_button=QPushButton('◉ Duyurular')
        self.announcements_button.setToolTip('Sürüm notları ve Güncelleme Merkezi')
        self.announcements_button.clicked.connect(self.open_announcements)
        right_row.addWidget(self.announcements_button)
        if not OWNER_EDITION:
            self.staff_theme_switch=QPushButton('')
            self.staff_theme_switch.setObjectName('StaffThemeSwitch')
            self.staff_theme_switch.setCheckable(True)
            self.staff_theme_switch.setChecked(self.config.get('tema')=='acik')
            self.staff_theme_switch.setText('☼ Açık' if self.staff_theme_switch.isChecked() else '☾ Koyu')
            self.staff_theme_switch.setToolTip('Açık / koyu görünümü anında değiştir')
            self.staff_theme_switch.clicked.connect(self.toggle_staff_theme)
            right_row.addWidget(self.staff_theme_switch)
        self.cloud_badge=text('◌ Bağlanıyor…','Tiny')
        self.cloud_badge.setToolTip('Siparişler yalnızca eşleştirilmiş cihazlarda buluta aktarılır.')
        right_row.addWidget(self.cloud_badge)
        if not OWNER_EDITION:
            self.report_button=QPushButton('⚠ Hata Bildir')
            self.report_button.setToolTip('Seçilen teknik hata türünü Yönetici Hata Merkezi’ne bildir')
            self.report_button.clicked.connect(self.open_manual_report)
            right_row.addWidget(self.report_button)
        self.cloud_connect=QPushButton('Buluta bağla')
        self.cloud_connect.setObjectName('CloudConnect')
        self.cloud_connect.setToolTip(
            'İlk kurulumda bir kez cihazı yetkilendir; sonraki açılışlar girişsiz.')
        self.cloud_connect.clicked.connect(self.connect_cloud)
        right_row.addWidget(self.cloud_connect)
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
        # Katalog: exclusively printed books and checkout.
        self.catalog=KatalogView(self.db,self.covers)
        self.title_line.insertWidget(1,self.catalog.toolbar,1)
        self.orders=SiparisView(self.db,self.covers,self.open_book_pool,admin_mode=OWNER_EDITION)
        self.analytics=AnalitikView(self.db,lambda sid:self.orders.open_editor(sid,'track'))
        self.inventory=EnvanterView(self.db)
        # General products belong to INVENTORY, not the book catalog.
        self.general_catalog=GeneralProductCatalog(self.db)
        self.inventory_host=QWidget()
        self.inventory_host.setObjectName('InventoryHost')
        inv_layout=QVBoxLayout(self.inventory_host)
        inv_layout.setContentsMargins(0,0,0,0)
        inv_layout.setSpacing(9)
        inv_nav=QHBoxLayout()
        inv_nav.setContentsMargins(8,5,8,0)
        inv_nav.setSpacing(8)
        self.inventory_tabs=[]
        for index,label in enumerate(('▦  Stok ve Envanter','▤  Genel Ürünler')):
            tab=button(label,'InventoryModeTab')
            tab.setCheckable(True)
            tab.clicked.connect(lambda checked=False,n=index:self.select_inventory(n))
            self.inventory_tabs.append(tab)
            inv_nav.addWidget(tab)
        inv_nav.addStretch()
        inv_layout.addLayout(inv_nav)
        self.inventory_view=QStackedWidget()
        self.inventory_view.addWidget(self.inventory)
        self.inventory_view.addWidget(self.general_catalog)
        inv_layout.addWidget(self.inventory_view,1)
        self.inventory_tabs[0].setChecked(True)
        if OWNER_EDITION:
            from yonetici_kompakt import OwnerSettingsPage
            self.settings_page=OwnerSettingsPage(self.db,self.config,self.admin_cloud)
        else:
            self.settings_page=SettingsPage(self.db,self.config)
        for page in (self.catalog,self.orders,self.analytics,self.inventory_host,self.settings_page):self.stack.addWidget(page)
        self.device=Workstation()
        # Reuse the existing Workstation for event-only exception reports.
        # Never send credentials, order content or stack locals to Firebase.
        connect_device(lambda:self.device)
        if OWNER_EDITION:
            self.settings_page.enable_error_stream(self.device)
            self._error_tray=QSystemTrayIcon(self.make_icon(),self)
            self._error_tray.setToolTip("ALFA ERP · Yönetici hata bildirimleri")
            if QSystemTrayIcon.isSystemTrayAvailable():
                self._error_tray.show()
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
        self.navigate(0)
        # One local daily timer; only a due check makes one GitHub API GET.
        # No Firebase reads or dedicated polling service are added.
        self._update_job=None
        self._update_available=None
        self._announcements_dialog=None
        self._update_daily=QTimer(self)
        self._update_daily.setInterval(24*60*60*1000)
        self._update_daily.timeout.connect(self.check_background_updates)
        self._update_daily.start()
        # Announcements and update checks start after the splash closes.
        QApplication.instance().aboutToQuit.connect(self._stop_update_job)
        # Firebase pairing is explicit and remembered; legacy ticket timers
        # were intentionally removed (no idle work, no repeat login).

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

    def toggle_staff_theme(self):
        if OWNER_EDITION:return
        key='acik' if self.staff_theme_switch.isChecked() else 'koyu'
        self.staff_theme_switch.setText('☼ Açık' if key=='acik' else '☾ Koyu')
        self.config.set('tema',key)
        app=QApplication.instance()
        app.setProperty('alfa_theme',key)
        app.setStyleSheet(QSS+theme_styles(key))
        self.inventory.apply_theme()
        self.general_catalog.apply_theme()
        from widgets import refresh_cover_placeholders
        refresh_cover_placeholders()

    def open_manual_report(self):
        if not OWNER_EDITION:
            ManualReportDialog(self).exec()

    def open_announcements(self,release=None):
        edition='owner' if OWNER_EDITION else 'staff'
        dialog=AnnouncementsDialog(VERSION,edition,self.config.data_dir,
                                    release or self._update_available,self)
        self._announcements_dialog=dialog
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _show_whats_new_once(self):
        # The in-app changelog is bundled; no network request for this popup.
        file=Path(self.config.data_dir)/'alfa_whats_new.json'
        try:
            before=json.loads(file.read_text(encoding='utf-8'))
        except (OSError,ValueError,TypeError):
            before={}
        if before.get('version')==VERSION:return
        # Show release history once for each new Suite install/upgrade.
        try:
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(json.dumps({'version':VERSION}),encoding='utf-8')
        except OSError:
            pass
        self.open_announcements()

    def check_background_updates(self):
        if self._update_job is not None:return
        edition='owner' if OWNER_EDITION else 'staff'
        if not should_check_today(self.config.data_dir,edition):return
        try:mark_checked(self.config.data_dir,edition)
        except (OSError,ValueError):return
        job=CheckWorker(VERSION,edition,self)
        self._update_job=job
        outcome={'release':None}
        job.done.connect(lambda data:outcome.update(release=data))
        def completed():
            job.wait()
            self._update_job=None
            data=outcome['release']
            if data and data.get('available'):
                self._update_available=data
                tag=str(data.get('version') or '')
                notice=Path(self.config.data_dir)/('alfa_last_update_popup_'+edition+'.json')
                try:
                    saved=json.loads(notice.read_text(encoding='utf-8'))
                except (OSError,ValueError,TypeError):
                    saved={}
                if saved.get('version')!=tag:
                    try:notice.write_text(json.dumps({'version':tag}),encoding='utf-8')
                    except OSError:pass
                    self.statusBar().showMessage('Yeni kararlı sürüm: v'+tag,22000)
                    QTimer.singleShot(250,lambda:self.open_announcements(data))
        job.finished.connect(completed)
        job.finished.connect(job.deleteLater)
        job.start()

    def _stop_update_job(self):
        job=self._update_job
        if job is not None and job.isRunning():
            job.requestInterruption()
            job.wait()

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

    def select_inventory(self,index):
        """Inventory owns the shared general-product master and stock view."""
        self.inventory_view.setCurrentIndex(index)
        for n,tab in enumerate(self.inventory_tabs):
            tab.setChecked(n==index)
        if index==0:
            self.inventory.refresh()
        else:
            self.general_catalog.refresh()

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
            connect_device(lambda:self.device)
            if OWNER_EDITION:
                self.settings_page.enable_error_stream(self.device)
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
            self.select_inventory(self.inventory_view.currentIndex())
        elif index==4 and OWNER_EDITION:
            self.settings_page.show_tab(self.settings_page.current_tab)

    def _cloud_orders_changed(self,ids):
        if not ids:return
        if '__katalog__' in ids:
            self.catalog.refresh_grid()
            self.catalog.update_cart()
            # Historical 0-page order snapshots are recovered from the
            # authoritative catalog. Repaint order totals immediately.
            self.orders.refresh()
            if self.bookpool and self.bookpool.isVisible():
                self.bookpool.refresh()
        if '__envanter__' in ids:
            self.inventory.refresh()
            self.general_catalog.refresh()
        if any(x not in ('__katalog__','__muhasebe__','__envanter__') for x in ids):
            self.orders.refresh()
            if self.bookpool and self.bookpool.isVisible():self.bookpool.refresh()
        if self.stack.currentWidget() is self.analytics:self.analytics.refresh()

    def _cloud_status(self,online,message):
        # Pending crash reports retry ONLY on an actual connectivity transition,
        # not from a polling timer or on every ordinary sync status string.
        previous=getattr(self,"_error_was_online",False)
        self._error_was_online=bool(online)
        if online and not previous:
            connect_device(lambda:self.device)
        self.setWindowTitle('ALFA ERP '+('Yönetici' if OWNER_EDITION else 'Personel')+
                            ' v'+VERSION+' · '+
                            ('Bulut bağlı' if online else 'Bağlantı bekleniyor'))
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
        self.live.boost()
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

    def notify_admin_error(self,count):
        """One user-visible notification per real incoming cloud event."""
        msg=f"⚠ {count} yeni bilgisayar hata raporu · Ayarlar → Hata Merkezi"
        self.statusBar().showMessage(msg,18000)
        tray=getattr(self,"_error_tray",None)
        if tray and tray.isVisible():
            tray.showMessage("ALFA ERP · Yeni hata raporu",msg,
                             QSystemTrayIcon.MessageIcon.Warning,12000)

    def order_created(self):
        """Do not interrupt repeat order entry with automatic navigation."""
        if not hasattr(self,'_order_saved_toast'):
            toast=QLabel(self.centralWidget())
            toast.setObjectName('OrderSavedToast')
            toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
            toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            toast.setStyleSheet(
                'QLabel#OrderSavedToast {background:#155740;color:#f4fff9;'
                'border:1px solid #55d6a7;border-radius:10px;'
                'font-size:14px;font-weight:800;padding:13px 21px;}')
            self._order_saved_toast=toast
            self._order_saved_timer=QTimer(self)
            self._order_saved_timer.setSingleShot(True)
            self._order_saved_timer.timeout.connect(toast.hide)
        toast=self._order_saved_toast
        toast.setText('✓  Siparişiniz oluşturuldu.')
        toast.adjustSize()
        host=self.centralWidget()
        toast.move(max(12,host.width()-toast.width()-24),
                   max(12,host.height()-toast.height()-24))
        toast.show()
        toast.raise_()
        self._order_saved_timer.start(3500)

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
        record_error(error_type,error,tb,source="gui")
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
    # Background worker exceptions are caught as sanitized crashes too.
    import threading
    def background_exception(args):
        record_error(args.exc_type,args.exc_value,args.exc_traceback,source="thread")
    threading.excepthook=background_exception


def start():
    local=os.environ.get('ALFA_ERP_DATA_DIR') or str(
        Path(os.environ.get('LOCALAPPDATA') or Path.home())/'AlfaERP')
    install_reporter(VERSION,"owner" if OWNER_EDITION else "staff",data_dir=local)
    _install_error_diagnostics()
    app=QApplication(sys.argv)
    app.setApplicationName('ALFA ERP')
    app.setApplicationVersion(VERSION)
    app.setProperty('alfa_edition',"owner" if OWNER_EDITION else "staff")
    app.setStyle('Fusion')
    app.setStyleSheet(QSS)
    from ekran_baslangic import launch_with_splash
    return launch_with_splash(app,lambda:AlfaMain(admin_cloud=None),
                              version=VERSION,owner=OWNER_EDITION,
                              on_error=record_error)


def release_smoke_test():
    """Packaged EXE startup probe; never connects to production Firebase."""
    import tempfile
    from ekran_baslangic import StartupSplash
    class OfflineDevice:
        paired=False
        token=None
        uid=None
    original=globals()['Workstation']
    original_data=os.environ.get('ALFA_ERP_DATA_DIR')
    globals()['Workstation']=OfflineDevice
    os.environ['QT_QPA_PLATFORM']='offscreen'
    report={}
    window=None
    try:
        with tempfile.TemporaryDirectory(prefix='alfa_firebase_smoke_') as folder:
            os.environ['ALFA_ERP_DATA_DIR']=folder
            app=QApplication.instance() or QApplication(['alfa-firebase-smoke'])
            app.setStyle('Fusion')
            app.setStyleSheet(QSS)
            splash=StartupSplash(owner=OWNER_EDITION,version=VERSION)
            splash.show()
            splash.update_step('storage','Doğrulandı.')
            app.processEvents()
            if splash.progress.value()!=1:
                raise RuntimeError('Startup indicator failed')
            splash.close()
            window=AlfaMain(admin_cloud=None)
            app.processEvents()
            if window.stack.count()!=5 or not window.db.katalog:
                raise RuntimeError('ERP pages or book catalog unavailable')
            report={'ok':True,'version':VERSION,'pages':5,
                    'books':len(window.db.katalog),
                    'edition':'owner' if OWNER_EDITION else 'staff'}
            code=0
    except Exception as exc:
        report={'ok':False,'error':str(exc)[:320]}
        code=2
    finally:
        if window is not None:
            window.close()
        globals()['Workstation']=original
        if original_data is None:os.environ.pop('ALFA_ERP_DATA_DIR',None)
        else:os.environ['ALFA_ERP_DATA_DIR']=original_data
    output=os.environ.get('ALFA_SMOKE_RESULT_PATH')
    if output:
        Path(output).write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
    return code


if __name__=='__main__':
    sys.exit(release_smoke_test() if '--self-test' in sys.argv else start())
