"""Single owner settings page inside the normal ERP. No second admin dashboard."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import tempfile,uuid
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
    QPushButton,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem,QAbstractItemView,
    QFrame,QHeaderView,QDialog,QTextEdit)
from PySide6.QtCore import Qt,QThread,Signal
from ekran_ayarlar import SettingsPage
from database import ERPDatabase
from widgets import button
from yonetici_giris import admin_request
from yonetici_gunluk import AuditFeed

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
        # The standard settings only had two tabs; keep those, add three owner tools.
        nav=self.layout().itemAt(1).layout()
        for title,page in [('Excel kataloğu',self.catalog_page()),
                           ('Bilgisayarlar',self.devices_page()),
                           ('İşlem günlüğü',self.audit_page())]:
            idx=self.stack.count()
            b=button(title,'SettingsNav');b.setCheckable(True)
            b.clicked.connect(lambda _=False,i=idx:self.show_tab(i))
            nav.insertWidget(len(self.nav),b)
            self.nav.append(b);self.stack.addWidget(page)
        self.show_tab(0)

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
        path,_=QFileDialog.getOpenFileName(self,'Katalog Excel seç',str(Path.home()),'Excel (*.xlsx)')
        if not path:return
        try:
            with tempfile.TemporaryDirectory(prefix='alfa_catalog_') as tmp:
                parsed=ERPDatabase(path,data_dir=tmp)
                books=[{'code':str(b['kod']),'name':str(b['isim']),
                        'group_name':str(b['grup']),'page_count':int(b['sayfa']),
                        'supports_color':bool(b['renkli_opsiyon'])} for b in parsed.kitaplar]
            if not books or len(books)>2000:raise ValueError('Excel 1–2000 kitap içermeli.')
            self.catalog_rows=books;self.upload_btn.setEnabled(True)
            self.catalog_note.setText(f'{Path(path).name} · {len(books)} kitap hazır')
        except Exception as exc:self.catalog_note.setText(str(exc))

    def upload_catalog(self):
        if QMessageBox.question(self,'Katalog güncelleme',
            f'{len(self.catalog_rows)} kitap bulutta güncellensin mi?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.upload_btn.setEnabled(False);self.catalog_note.setText('Buluta yükleniyor…')
        self._job(lambda:admin_request(None,'admin_catalog',books=self.catalog_rows),
             lambda r:(self.catalog_note.setText(f"Katalog güncellendi · {r.get('count')} kitap"),
                       self.upload_btn.setEnabled(True)),
             lambda err:(self.catalog_note.setText(err),self.upload_btn.setEnabled(True)))

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
        col.addWidget(revoke);return page

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
        def display(d):
            rows=d.get('devices',[]);self.device_table.setRowCount(len(rows))
            for i,r in enumerate(rows):
                for j,val in enumerate([r.get('device_name',''),
                    'Aktif' if r.get('active') else 'İptal',str(r.get('last_seen_at') or '—')[:19]]):
                    self.device_table.setItem(i,j,QTableWidgetItem(str(val)))
                self.device_table.item(i,0).setData(Qt.ItemDataRole.UserRole,r['id'])
        self._job(lambda:admin_request(None,'admin_devices'),display)

    def revoke(self):
        row=self.device_table.currentRow()
        if row<0:return
        if QMessageBox.question(self,'Cihaz erişimi','Seçili bilgisayar devre dışı bırakılsın mı?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        id=self.device_table.item(row,0).data(Qt.ItemDataRole.UserRole)
        self._job(lambda:admin_request(None,'admin_revoke',id=id),
                  lambda _r:self.refresh_devices())

    def audit_page(self):
        page=QWidget();page.setObjectName('OwnerToolPage')
        layout=QVBoxLayout(page);layout.setContentsMargins(12,12,12,8)
        actions=QHBoxLayout();actions.addStretch(1)
        review=QPushButton('⚠ Eski bulut hatalarını incele')
        review.setObjectName('OwnerDanger');review.clicked.connect(self.review_cloud_conflicts)
        actions.addWidget(review)
        refresh=QPushButton('↻ İşlem günlüğünü yenile')
        refresh.setObjectName('OwnerPrimary');refresh.clicked.connect(self.refresh_audit)
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

    def refresh_audit(self):
        self._job(lambda:admin_request(None,'admin_audit'),
                  lambda payload:self.audit_feed.set_entries(payload,self.db.siparisler))

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
        QPushButton#OwnerFilter, QPushButton#OwnerPrimary, QPushButton#OwnerDanger {
            background:%(button)s;color:%(text)s;border:1px solid %(border)s;
            border-radius:9px;min-height:34px;padding:5px 13px;font-weight:700;
        }
        QPushButton#OwnerPrimary {background:%(action)s;}
        QPushButton#OwnerDanger {background:%(danger)s;}
        QPushButton#OwnerFilter:hover, QPushButton#OwnerPrimary:hover,
        QPushButton#OwnerDanger:hover {border-color:%(major)s;background:%(hover)s;}
        QPushButton#OwnerFilter:checked {border:2px solid %(major)s;background:%(selection)s;}
        QTableWidget#OwnerDeviceTable {
            background:%(card)s;color:%(text)s;
            alternate-background-color:%(input)s;gridline-color:%(border)s;
            border:1px solid %(border)s;border-radius:10px;
            selection-background-color:%(selection)s;selection-color:%(text)s;
        }
        QTableWidget#OwnerDeviceTable QHeaderView::section {
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
