"""Single owner settings page inside the normal ERP. No second admin dashboard."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import tempfile,uuid,time,webbrowser
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
    QPushButton,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem,QAbstractItemView,
    QFrame,QHeaderView,QDialog,QTextEdit,QCheckBox)
from PySide6.QtCore import Qt,QThread,Signal
from ekran_ayarlar import SettingsPage
from database import ERPDatabase
from widgets import button
from rtdb_owner_admin import admin_request
from yonetici_gunluk import AuditFeed
from hata_merkezi_ui import ErrorInbox
from bulut_canli import RtdbWatch

class RequestJob(QThread):
    success=Signal(object)
    failure=Signal(str)
    def __init__(self,fn,parent=None):
        super().__init__(parent);self.fn=fn
    def run(self):
        try:self.success.emit(self.fn())
        except Exception as exc:self.failure.emit(str(exc)[:320])

class OwnerSettingsPage(SettingsPage):
    def __init__(self,db,config,cloud):
        super().__init__(db,config)
        self.setObjectName('OwnerSettings')
        self.cloud=cloud
        self.jobs=set()
        self._audit_last_loaded=0.0
        self._error_watch=None
        self._error_client=None
        self._error_loading=False
        self._error_first_snapshot=False
        self._error_known=set()
        self._error_refresh_again=False
        self._all_device_rows=[]
        # Settings remain one built-in owner page; no separate admin app.
        nav=self.layout().itemAt(1).layout()
        for title,page in [('Excel kataloğu',self.catalog_page()),
                           ('Bilgisayarlar',self.devices_page()),
                           ('İşlem günlüğü',self.audit_page()),
                           ('Sistem sağlığı',self.health_page()),
                           ('Hata Merkezi',self.error_page())]:
            idx=self.stack.count()
            b=button(title,'SettingsNav');b.setCheckable(True)
            b.clicked.connect(lambda _=False,i=idx:self.show_tab(i))
            nav.insertWidget(len(self.nav),b)
            self.nav.append(b);self.stack.addWidget(page)
        self.show_tab(0)

    def _admin(self,action,**kwargs):
        # Reuse main application's locked Workstation session. Creating
        # a fresh Workstation for every admin click caused redundant token
        # refreshes and confusing owner errors.
        main=self.window()
        client=getattr(main,'device',None)
        if client is None:
            raise RuntimeError('Firebase yönetici bağlantısı bulunamadı.')
        return admin_request(client,action,**kwargs)

    def _job(self,fn,on_success,on_error=None):
        work=RequestJob(fn,self);self.jobs.add(work)
        outcome={'ok':False,'value':None,'error':None}
        work.success.connect(lambda value:outcome.update(ok=True,value=value))
        work.failure.connect(lambda msg:outcome.update(error=msg))
        def finished():
            # A dialog may be opened by a result callback. Ensure QThread
            # is fully stopped before invoking GUI callbacks or releasing it.
            work.wait()
            self.jobs.discard(work)
            try:
                if outcome['ok']:on_success(outcome['value'])
                elif on_error:on_error(outcome['error'] or 'Yönetici işlemi başarısız')
                else:QMessageBox.warning(self,'Yönetici',
                    outcome['error'] or 'Yönetici işlemi başarısız')
            except Exception as exc:
                QMessageBox.warning(self,'Yönetici',str(exc)[:240])
        work.finished.connect(finished)
        work.finished.connect(work.deleteLater)
        work.start()

    def catalog_page(self):
        page=QWidget();page.setObjectName('OwnerToolPage');col=QVBoxLayout(page)
        col.addWidget(QLabel('Excel katalog güncellemesi · tüm bilgisayarlar ve mobil katalog'))
        row=QHBoxLayout();pick=QPushButton('Excel seç');pick.clicked.connect(self.pick_catalog)
        row.addWidget(pick);self.upload_btn=QPushButton('Buluta güncelle')
        self.upload_btn.setEnabled(False);self.upload_btn.clicked.connect(self.upload_catalog)
        row.addWidget(self.upload_btn);col.addLayout(row)
        self.catalog_note=QLabel('Yüklenecek Excel seçilmedi.');self.catalog_note.setWordWrap(True)
        col.addWidget(self.catalog_note);col.addStretch();self.catalog_rows=[]
        return page

    def pick_catalog(self):
        path,_=QFileDialog.getOpenFileName(
            self,'Katalog Excel seç',str(Path.home()),'Excel (*.xlsx)')
        if not path:return
        try:
            from katalog_excel_aktar import preview_excel_catalog
            books=preview_excel_catalog(path)
            self.catalog_rows=books
            self.upload_btn.setEnabled(True)
            self.catalog_note.setText(f'{Path(path).name} · {len(books)} kitap hazır')
        except Exception as exc:
            self.upload_btn.setEnabled(False)
            self.catalog_rows=[]
            self.catalog_note.setText(str(exc)[:250])

    def upload_catalog(self):
        if QMessageBox.question(self,'Katalog güncelleme',
            f'{len(self.catalog_rows)} kitap bulutta güncellensin mi?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.upload_btn.setEnabled(False);self.catalog_note.setText('Buluta yükleniyor…')
        self._job(lambda:self._admin('admin_catalog',books=self.catalog_rows),
             self._catalog_uploaded,
             lambda err:(self.catalog_note.setText(
                 'Firebase katalog yüklenemedi: '+str(err)[:250]),
                 self.upload_btn.setEnabled(True)))

    def _catalog_uploaded(self,result):
        count=int(result.get('count') or 0)
        verified=bool(result.get('verified'))
        self.catalog_note.setText(
            (f'Firebase doğrulandı · {count} kitap, '+
             str(result.get('updated',0))+' güncellenen kayıt')
            if verified else 'Katalog sunucuda doğrulanamadı. Yeniden deneyin.')
        self.upload_btn.setEnabled(True)
        if verified:
            main=self.window()
            live=getattr(main,'live',None)
            if live is not None:
                live.force_pull=True
                live.pull()

    def devices_page(self):
        page=QWidget();page.setObjectName('OwnerToolPage');col=QVBoxLayout(page)
        heading=QLabel('BAĞLI BİLGİSAYARLAR');heading.setObjectName('OwnerHeading')
        col.addWidget(heading)
        sub=QLabel('Cihazları görüntüle, yeni personel bilgisayarı ekle veya erişimi iptal et.')
        sub.setObjectName('OwnerMuted');sub.setWordWrap(True);col.addWidget(sub)
        top=QHBoxLayout();new=QPushButton('Personel cihazını onayla')
        new.setObjectName('OwnerPrimary');new.clicked.connect(self.create_code)
        reload=QPushButton('Yenile');reload.clicked.connect(self.refresh_devices)
        package=QPushButton('Kurulum yönergesi')
        package.clicked.connect(self.export_staff_package)
        top.addWidget(new);top.addWidget(reload);top.addWidget(package);col.addLayout(top)
        self.show_inactive=QCheckBox("Pasif cihazları göster")
        self.show_inactive.setChecked(False)
        self.show_inactive.toggled.connect(self._render_devices)
        col.addWidget(self.show_inactive)
        self.code_note=QLineEdit();self.code_note.setObjectName('OwnerCode')
        self.code_note.setReadOnly(True)
        self.code_note.setPlaceholderText('Firebase cihaz kimliği (UID) ile yetkilendirme')
        col.addWidget(self.code_note)
        self.device_table=QTableWidget(0,3)
        self.device_table.setObjectName('OwnerDeviceTable')
        self.device_table.setHorizontalHeaderLabels(['Bilgisayar','Durum','Son bağlantı'])
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.horizontalHeader().setMinimumSectionSize(100)
        self.device_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.device_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
        self.device_table.setAlternatingRowColors(True)
        self.device_table.setShowGrid(False)
        self.device_table.verticalHeader().hide()
        self.device_table.verticalHeader().setDefaultSectionSize(46)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.device_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.device_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        col.addWidget(self.device_table)
        revoke=QPushButton('Seçili cihaz erişimini iptal et')
        revoke.setObjectName('OwnerDanger');revoke.clicked.connect(self.revoke)
        clean=QPushButton("Pasif cihaz kayıtlarını temizle")
        clean.setObjectName('OwnerDanger')
        clean.clicked.connect(self.prune_devices)
        col.addWidget(revoke);col.addWidget(clean)
        return page

    def export_staff_package(self):
        QMessageBox.information(self,'Firebase personel kurulumu',
            'Artık her bilgisayar için ayrı ZIP veya 48 karakterli eşleştirme kodu yok.\\n'
            'Aynı Personel Setup.exe kurulur. Personel bilgisayarında Cihaz yetkisi '
            'düğmesiyle UID oluşturulur ve buradan onaylanır.')

    def create_code(self):
        from firebase_pair_ui import PairDialog
        client=getattr(self.window(),'device',None)
        if client is None:
            QMessageBox.warning(self,'Firebase','Cihaz bağlantısı bulunamadı.')
            return
        dialog=PairDialog(client=client,owner=True,parent=self)
        dialog.exec()
        self.refresh_devices()

    def refresh_devices(self):
        def show(payload):
            self._all_device_rows=payload.get("devices") or []
            self._render_devices()
        self._job(lambda:self._admin('admin_devices'),show)

    def _render_devices(self,*_):
        data=self._all_device_rows
        active=[r for r in data if r.get("active")]
        inactive=[r for r in data if not r.get("active")]
        visible=active+(inactive if self.show_inactive.isChecked() else [])
        self.device_table.setRowCount(len(visible))
        for i,r in enumerate(visible):
            for col,value in enumerate([
                r.get("device_name") or r.get("id") or "",
                ("Yönetici" if r.get("device_role")=="owner" else "Personel")+
                (" · Aktif" if r.get("active") else " · İptal"),
                str(r.get("last_seen_at") or "—")[:19]]):
                self.device_table.setItem(i,col,QTableWidgetItem(str(value)))
            self.device_table.item(i,0).setData(Qt.ItemDataRole.UserRole,r["id"])
        self.code_note.setText(
            str(len(active))+" aktif cihaz · "+str(len(inactive))+
            " pasif kayıt"+(" (gizli)" if inactive and not self.show_inactive.isChecked() else ""))

    def revoke(self):
        row=self.device_table.currentRow()
        if row<0:return
        uid=self.device_table.item(row,0).data(Qt.ItemDataRole.UserRole)
        target=next((x for x in self._all_device_rows if x.get("id")==uid),None)
        if not target or not target.get("active"):
            QMessageBox.information(self,"Cihaz yetkisi","Bu cihaz zaten pasif.")
            return
        if uid==getattr(getattr(self.window(),"device",None),"uid",None):
            QMessageBox.warning(self,"Cihaz yetkisi","Kendi Yönetici cihazın iptal edilemez.")
            return
        if QMessageBox.question(
            self,"Cihaz erişimini iptal et",
            str(target.get("device_name") or uid)+" cihazının Firebase erişimi iptal edilsin mi?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
        )!=QMessageBox.StandardButton.Yes:return
        self._job(lambda:self._admin("admin_revoke",id=uid),
                  lambda _result:self.refresh_devices())

    def prune_devices(self):
        inactive=[r for r in self._all_device_rows if not r.get("active")]
        if not inactive:
            QMessageBox.information(self,"Cihaz kayıtları",
                                    "Temizlenecek pasif cihaz kaydı yok.")
            return
        if QMessageBox.question(
            self,"Pasif cihazları kalıcı temizle",
            str(min(len(inactive),80))+" pasif cihazın Firebase üyeliği silinsin mi?\n"
            "Kayıtlar listeden kaldırılır. İptal edilen cihaz tekrar "
            "erişebilmek için yeniden owner/personel onayı gerektirir. "
            "Mevcut aktif cihazlara dokunulmaz.",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
        )!=QMessageBox.StandardButton.Yes:return
        self._job(lambda:self._admin("admin_prune_devices"),
                  lambda result:(self.refresh_devices(),
                       QMessageBox.information(self,"Cihaz kayıtları",
                           str(result.get("removed",0))+" pasif kayıt temizlendi.")))

    def audit_page(self):
        page=QWidget();page.setObjectName('OwnerToolPage')
        layout=QVBoxLayout(page);layout.setContentsMargins(12,12,12,8)
        actions=QHBoxLayout();actions.addStretch(1)
        review=QPushButton('⚠ Eski bulut hatalarını incele')
        review.setObjectName('OwnerDanger');review.clicked.connect(self.review_cloud_conflicts)
        actions.addWidget(review)
        refresh=QPushButton('↻ İşlem günlüğünü yenile')
        refresh.setObjectName('OwnerPrimary');refresh.clicked.connect(lambda:self.refresh_audit(force=True))
        actions.addWidget(refresh);layout.addLayout(actions)
        self.audit_feed=AuditFeed(page);layout.addWidget(self.audit_feed,1)
        return page

    def review_cloud_conflicts(self):
        """Show archived failures without automatically retrying unsafe operations."""
        from datetime import datetime
        entries=self.db.unreviewed_cloud_conflicts
        if not entries:
            QMessageBox.information(self,'Bulut işlemleri',
                'İncelenmeyi bekleyen eski işlem çakışması yok.')
            return
        dialog=QDialog(self);dialog.setWindowTitle('Arşivlenmiş bulut işlem hataları')
        dialog.resize(690,520)
        column=QVBoxLayout(dialog)
        info=QLabel(
            f'{len(entries)} eski işlem reddi kayıt altında. Bu kayıtlar şu anda '
            'buluta gönderilmiyor. Aşağıdaki işlemleri inceleyerek gerekirse '
            'güncel sipariş üzerinde yeniden uygulayın.'
        );info.setWordWrap(True);column.addWidget(info)
        box=QTextEdit();box.setReadOnly(True)
        lines=[]
        for index,entry in enumerate(reversed(entries),1):
            batch=entry.get('batch') or {}
            kind=str(batch.get('kind') or 'bilinmiyor')
            events=batch.get('events') or batch.get('edits') or []
            names=', '.join(str(x.get('order_id') or x.get('local_id') or '')[:12]
                             for x in events[:6])
            lines.append(
                f"{index}. {entry.get('at','—')} · {kind.upper()} · {names}\n"
                f"    {entry.get('reason','Bilinmeyen çakışma')}\n")
        box.setPlainText('\n'.join(lines));column.addWidget(box,1)
        buttons=QHBoxLayout()
        close=QPushButton('Kapat');close.clicked.connect(dialog.reject)
        approve=QPushButton('İnceledim · arşivde sakla')
        approve.setObjectName('OwnerPrimary')
        def review():
            if QMessageBox.question(dialog,'Arşiv kayıtları',
                'Bu hatalar gözden geçirildi olarak işaretlensin mi? '
                'Kayıtlar silinmeyecek ve tekrar otomatik gönderilmeyecek.',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
            )!=QMessageBox.StandardButton.Yes:return
            self.db.mark_cloud_conflicts_reviewed()
            main=self.window()
            if hasattr(main,'_cloud_status'):
                main._cloud_status(True,'Bulut bağlı · eski hatalar arşivde')
            dialog.accept()
        approve.clicked.connect(review)
        buttons.addStretch();buttons.addWidget(close);buttons.addWidget(approve)
        column.addLayout(buttons)
        dialog.exec()

    def refresh_audit(self,force=False):
        # Do not repeatedly download every order's audit history when a user
        # switches between Settings tabs. Manual refresh always bypasses TTL.
        if not force and time.monotonic()-self._audit_last_loaded < 120:
            return
        if getattr(self,'_audit_loading',False):
            return
        self._audit_loading=True
        def success(payload):
            self._audit_loading=False
            self._audit_last_loaded=time.monotonic()
            self.audit_feed.set_entries(payload,self.db.siparisler)
        def failed(message):
            self._audit_loading=False
            self._audit_last_loaded=0.0
            QMessageBox.warning(self,'İşlem günlüğü',message)
        self._job(lambda:self._admin('admin_audit'),success,failed)

    def error_page(self):
        self.error_inbox=ErrorInbox(self)
        self.error_inbox.refresh_requested.connect(
            lambda:self.refresh_error_reports(force=True))
        self.error_inbox.review_requested.connect(self.review_error_report)
        self.error_inbox.remove_requested.connect(self.delete_error_report)
        self.error_inbox.purge_reviewed_requested.connect(self.purge_reviewed_errors)
        return self.error_inbox

    def enable_error_stream(self,client):
        """One owner-only SSE connection, not a recurring query timer."""
        self._error_client=client
        if not client or not client.paired or self._error_watch is not None:
            return
        self._error_watch=RtdbWatch(
            client,"error_reports",self,
            query={"orderBy":'"$key"',"limitToLast":70})
        self._error_watch.changed.connect(self._on_error_stream_event)
        self._error_watch.start()
        from PySide6.QtWidgets import QApplication
        app=QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._error_watch.stop)
        # SSE itself sends an initial bounded "put" and triggers first load.

    def _on_error_stream_event(self):
        self.refresh_error_reports()

    def refresh_error_reports(self,force=False):
        """One small owner read on SSE event, manual click or page open."""
        client=self._error_client or getattr(self.window(),"device",None)
        if client is None or not client.paired:
            self.error_inbox.summary.setText(
                "Hata Merkezi için Yönetici cihazının Firebase bağlantısı gerekli.")
            return
        self.enable_error_stream(client)
        if self._error_loading:
            self._error_refresh_again=True
            return
        self._error_loading=True
        self._error_refresh_again=False
        def fetch():
            return {"reports":client.read_error_reports(70),
                    "acks":client.read_error_acks()}
        def accepted(result):
            self._error_loading=False
            reports=result.get("reports") or {}
            ids=set(str(x) for x in reports)
            new=ids-self._error_known if self._error_first_snapshot else set()
            self._error_first_snapshot=True
            self._error_known=ids  # bounded to visible report window
            pending=self.error_inbox.set_entries(
                reports,result.get("acks") or {})
            if self.nav and len(self.nav)>6:
                self.nav[6].setText(
                    "⚠ Hata Merkezi ("+str(pending)+")" if pending else "Hata Merkezi")
            if new:
                parent=self.window()
                if hasattr(parent,"notify_admin_error"):
                    parent.notify_admin_error(len(new))
                elif hasattr(parent,"statusBar"):
                    parent.statusBar().showMessage(
                        f"⚠ {len(new)} yeni cihaz hatası · Ayarlar → Hata Merkezi",18000)
            if self._error_refresh_again:
                self._error_refresh_again=False
                self.refresh_error_reports(force=True)
        def failed(message):
            self._error_loading=False
            self.error_inbox.summary.setText(
                "Hata raporları alınamadı: "+str(message)[:160]+
                " · Firebase Rules henüz dağıtılmadıysa önce yetkilendir.")
        self._job(fetch,accepted,failed)

    def review_error_report(self,report_id):
        client=self._error_client or getattr(self.window(),"device",None)
        if client is None or not client.paired:
            QMessageBox.warning(self,"Hata Merkezi","Yönetici cihazı bağlı değil.")
            return
        self._job(
            lambda:client.review_error_report(report_id),
            lambda _response:self.refresh_error_reports(force=True))

    def delete_error_report(self,report_id):
        self._job(
            lambda:self._admin("admin_delete_error",id=report_id),
            lambda _result:self.refresh_error_reports(force=True))

    def purge_reviewed_errors(self,ids):
        self._job(
            lambda:self._admin("admin_purge_reviewed_errors",ids=ids),
            lambda result:(self.refresh_error_reports(force=True),
                QMessageBox.information(
                    self,"Hata Merkezi",
                    str(result.get("removed",0))+" incelenmiş rapor temizlendi.")))

    def health_page(self):
        """Lightweight on-demand diagnostics. No Firebase polling added."""
        page=QWidget();page.setObjectName('OwnerToolPage')
        root=QVBoxLayout(page);root.setContentsMargins(16,16,16,16);root.setSpacing(12)
        heading=QLabel('SİSTEM SAĞLIĞI VE KOTA TAKİBİ')
        heading.setObjectName('OwnerHeading');root.addWidget(heading)
        explanation=QLabel(
            'Bu ekranda uygulamanın mevcut eşitleme durumu gösterilir. '
            'Firebase saklama/indirme ve GitHub kota tüketiminin GERÇEK '
            'değerleri yalnızca ilgili resmî konsoldan okunur. '
            'Ek ağ trafiği oluşturan otomatik kota taraması yapılmaz.')
        explanation.setObjectName('OwnerMuted')
        explanation.setWordWrap(True);root.addWidget(explanation)
        self.health_label=QLabel('')
        self.health_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.health_label.setWordWrap(True)
        self.health_label.setObjectName('OwnerBody')
        root.addWidget(self.health_label)
        limits=QLabel(
            'Firebase Spark ücretsiz sınırlar: Realtime Database '
            '1 GB veri saklama, 10 GB/ay indirme, 100 eşzamanlı bağlantı. '
            'Hosting 10 GB saklama, 360 MB/gün aktarım. '
            'Bu sınırlar TÜKETİMİ değil, plan limitlerini gösterir.')
        limits.setObjectName('OwnerMuted');limits.setWordWrap(True)
        root.addWidget(limits)
        row=QHBoxLayout()
        refresh=QPushButton('↻ Yerel durumu yenile')
        refresh.setObjectName('OwnerPrimary')
        refresh.clicked.connect(self.refresh_health)
        row.addWidget(refresh);row.addStretch(1)
        root.addLayout(row)
        destinations=(
            ('Firebase · Veritabanı kullanımı',
             'https://console.firebase.google.com/project/alfa-erp-8700c/database'),
            ('Firebase · Hosting kullanımı',
             'https://console.firebase.google.com/project/alfa-erp-8700c/hosting'),
            ('Firebase · Proje faturası ve kullanım',
             'https://console.firebase.google.com/project/alfa-erp-8700c/usage'),
            ('GitHub · Derlemeler',
             'https://github.com/alarslan12/alfa-erp/actions'),
            ('GitHub · Sürüm dosyaları',
             'https://github.com/alarslan12/alfa-erp/releases'),
        )
        for label,url in destinations:
            link=QPushButton('↗  '+label)
            link.setObjectName('OwnerPrimary')
            link.clicked.connect(lambda _checked=False,u=url:webbrowser.open(u))
            root.addWidget(link)
        root.addStretch()
        return page

    def refresh_health(self):
        db=self.db
        live=getattr(self.window(),'live',None)
        connected=bool(live and getattr(live,'_last_status',None)
                       and live._last_status[0])
        status='Bağlı' if connected else 'Bağlantı bekleniyor'
        pending=db.pending_count
        conflicts=len(db.unreviewed_cloud_conflicts)
        pulse=getattr(live,'last_pulse',None) or {}
        revisions=('Sipariş: '+str(pulse.get('orders_revision','—'))+
                   ' / Katalog: '+str(pulse.get('catalog_revision','—'))+
                   ' / Envanter: '+str(pulse.get('inventory_revision','—')))
        lines=[
            'Firebase bağlantısı: '+status,
            'Yerel katalog: '+str(len(db.katalog))+' kitap',
            'Yerelde görünen sipariş: '+str(len(db.siparisler)),
            'Gönderilmeyi bekleyen işlem: '+str(pending),
            'İncelenmemiş işlem çakışması: '+str(conflicts),
            'Veritabanı revizyonları: '+revisions,
            'Gerçek Firebase kota tüketimi: resmî Usage konsolunda',
        ]
        self.health_label.setText('\n'.join(lines))

    def _apply_owner_theme(self):
        # Three palettes keep the same hierarchy and contrast in every theme.
        palettes={
            'koyu':dict(bg='#111f30',card='#1c3045',input='#17283a',
              text='#edf5fd',muted='#b3c5d6',border='#455d77',
              head='#253d54',hover='#29465f',selection='#36566f',
              major='#f0c27b',minor='#84d9c2',button='#28485f',
              action='#327e94',danger='#723d46'),
            'acik':dict(bg='#f6f1e8',card='#fffaf3',input='#fbf7ef',
              text='#24384f',muted='#526679',border='#cbbca7',
              head='#ecdfce',hover='#f0e3d0',selection='#e5d3b6',
              major='#96571e',minor='#166c62',button='#f0e4d2',
              action='#e1b878',danger='#f0d5cf'),
            'kontrast':dict(bg='#080f1b',card='#152840',input='#102037',
              text='#ffffff',muted='#deedff',border='#91adcb',
              head='#233f5b',hover='#2d5577',selection='#355a7a',
              major='#ffe28e',minor='#80ffdc',button='#2a4b68',
              action='#355f7b',danger='#87424b')
        }
        p=palettes.get(self.config.get('tema','koyu'),palettes['koyu'])
        self.setStyleSheet("""
        QWidget#OwnerToolPage, QWidget#OwnerAuditHost {
            background:%(bg)s;color:%(text)s;
        }
        QWidget#OwnerToolPage QLabel {color:%(text)s;}
        QLabel#OwnerHeading {color:%(text)s;font-size:16px;font-weight:900;padding:5px 0;}
        QLabel#OwnerMuted {color:%(muted)s;font-size:11px;}
        QLabel#OwnerAuditTitle {color:%(text)s;font-size:13px;font-weight:850;}
        QLabel#OwnerBody {color:%(text)s;font-size:12px;}
        QFrame#OwnerAuditCard {
            background:%(card)s;border:1px solid %(border)s;
            border-radius:12px;
        }
        QFrame#OwnerAuditCard:hover {border-color:%(major)s;background:%(hover)s;}
        QLabel#OwnerAuditIcon {
            background:%(head)s;border:1px solid %(border)s;
            border-radius:11px;font-size:19px;font-weight:900;color:%(text)s;
        }
        QLabel#OwnerAuditIcon[level="major"] {color:%(major)s;}
        QLabel#OwnerAuditIcon[level="minor"] {color:%(minor)s;}
        QLabel#OwnerLevel {
            color:%(text)s;background:%(head)s;
            padding:4px 9px;border:1px solid %(border)s;
            border-radius:8px;font-size:10px;font-weight:850;
        }
        QLabel#OwnerLevel[level="major"] {color:%(major)s;}
        QLabel#OwnerLevel[level="minor"] {color:%(minor)s;}
        QPushButton#OwnerFilter, QPushButton#OwnerPrimary, QPushButton#OwnerDanger, QPushButton#OwnerAuditExpand {
            background:%(button)s;color:%(text)s;border:1px solid %(border)s;
            border-radius:9px;min-height:34px;padding:5px 13px;font-weight:700;
        }
        QPushButton#OwnerPrimary {background:%(action)s;}
        QPushButton#OwnerDanger {background:%(danger)s;}
        QPushButton#OwnerFilter:hover, QPushButton#OwnerPrimary:hover,
        QPushButton#OwnerDanger:hover {border-color:%(major)s;background:%(hover)s;}
        QPushButton#OwnerFilter:checked {border:2px solid %(major)s;background:%(selection)s;}
        QTableWidget#OwnerDeviceTable, QTableWidget#OwnerErrorTable {
            background:%(card)s;color:%(text)s;
            alternate-background-color:%(input)s;gridline-color:%(border)s;
            border:1px solid %(border)s;border-radius:10px;
            selection-background-color:%(selection)s;selection-color:%(text)s;
        }
        QTableWidget#OwnerDeviceTable QHeaderView::section, QTableWidget#OwnerErrorTable QHeaderView::section {
            background:%(head)s;color:%(text)s;
            padding:11px;border:0;border-bottom:1px solid %(border)s;font-weight:800;
        }
        QLineEdit#OwnerCode {
            background:%(input)s;color:%(text)s;
            border:1px solid %(border)s;padding:10px;border-radius:8px;
        }
        QScrollArea#OwnerAuditScroll {
            background:%(bg)s;border:0;
        }
        """ % p)

    def show_tab(self,index):
        super().show_tab(index)
        self._apply_owner_theme()
        if index==3:self.refresh_devices()
        if index==4:self.refresh_audit()
        if index==5:self.refresh_health()
        if index==6:self.refresh_error_reports()
