"""Single owner settings page inside the normal ERP. No second admin dashboard."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import tempfile,uuid
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
    QPushButton,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem,QAbstractItemView)
from PySide6.QtCore import Qt,QThread,Signal
from ekran_ayarlar import SettingsPage
from database import ERPDatabase
from widgets import button
from yonetici_giris import admin_request

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
        def done(value):
            self.jobs.discard(work);on_success(value)
        def fail(msg):
            self.jobs.discard(work)
            if on_error:on_error(msg)
            else:QMessageBox.warning(self,'Yönetici',msg)
        work.success.connect(done);work.failure.connect(fail)
        work.finished.connect(work.deleteLater);work.start()

    def catalog_page(self):
        page=QWidget();col=QVBoxLayout(page)
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
        self._job(lambda:admin_request(self.cloud,'admin_catalog',books=self.catalog_rows),
             lambda r:(self.catalog_note.setText(f"Katalog güncellendi · {r.get('count')} kitap"),
                       self.upload_btn.setEnabled(True)),
             lambda err:(self.catalog_note.setText(err),self.upload_btn.setEnabled(True)))

    def devices_page(self):
        page=QWidget();col=QVBoxLayout(page)
        col.addWidget(QLabel('Personel bilgisayarları · tek kullanımlık eşleştirme'))
        top=QHBoxLayout();new=QPushButton('Yeni cihaz kodu');new.clicked.connect(self.create_code)
        reload=QPushButton('Yenile');reload.clicked.connect(self.refresh_devices)
        package=QPushButton('Hazır Setup ile personel paketi hazırla')
        package.clicked.connect(self.export_staff_package)
        top.addWidget(new);top.addWidget(reload);top.addWidget(package);col.addLayout(top)
        self.code_note=QLineEdit();self.code_note.setReadOnly(True)
        self.code_note.setPlaceholderText('Yeni cihaz için tek kullanımlık kod')
        col.addWidget(self.code_note)
        self.device_table=QTableWidget(0,3)
        self.device_table.setHorizontalHeaderLabels(['Bilgisayar','Durum','Son bağlantı'])
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        col.addWidget(self.device_table)
        revoke=QPushButton('Seçili cihaz erişimini iptal et');revoke.clicked.connect(self.revoke)
        col.addWidget(revoke);return page

    def export_staff_package(self):
        """Bundle a prebuilt generic installer with a fresh one-time pairing code.

        A separate Windows build is NOT required for each new workstation.
        """
        installer,_=QFileDialog.getOpenFileName(self,'Hazır personel Setup.exe seç',
            str(Path.home()/'Downloads'),'Windows kurulum dosyası (*.exe)')
        if not installer:return
        destination,_=QFileDialog.getSaveFileName(self,'Bilgisayara özel kurulum paketini kaydet',
            str(Path.home()/'Desktop'/'ALFA_ERP_Personel_Kurulum.zip'),'ZIP (*.zip)')
        if not destination:return
        def finish(data):
            try:
                from personel_paketi import create_staff_installer_bundle
                create_staff_installer_bundle(destination,installer,data['code'])
                QMessageBox.information(self,'Kurulum hazır',
                    'Hazır Setup.exe ve bir defalık cihaz dosyası ZIP içine konuldu.\n'
                    'Personel bilgisayarında ZIP çıkarılıp Setup.exe çalıştırılır.\n'
                    'Yeniden derleme yapılmaz.')
            except Exception as exc:
                QMessageBox.warning(self,'Kurulum paketi',str(exc))
        self._job(lambda:admin_request(self.cloud,'admin_setup_code'),finish)

    def create_code(self):
        self._job(lambda:admin_request(self.cloud,'admin_setup_code'),
            lambda d:self.code_note.setText(d['code']))

    def refresh_devices(self):
        def display(d):
            rows=d.get('devices',[]);self.device_table.setRowCount(len(rows))
            for i,r in enumerate(rows):
                for j,val in enumerate([r.get('device_name',''),
                    'Aktif' if r.get('active') else 'İptal',str(r.get('last_seen_at') or '—')[:19]]):
                    self.device_table.setItem(i,j,QTableWidgetItem(str(val)))
                self.device_table.item(i,0).setData(Qt.ItemDataRole.UserRole,r['id'])
        self._job(lambda:admin_request(self.cloud,'admin_devices'),display)

    def revoke(self):
        row=self.device_table.currentRow()
        if row<0:return
        if QMessageBox.question(self,'Cihaz erişimi','Seçili bilgisayar devre dışı bırakılsın mı?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        id=self.device_table.item(row,0).data(Qt.ItemDataRole.UserRole)
        self._job(lambda:admin_request(self.cloud,'admin_revoke',id=id),
                  lambda _r:self.refresh_devices())

    def audit_page(self):
        page=QWidget();col=QVBoxLayout(page)
        head=QHBoxLayout();head.addWidget(QLabel('Bulut işlem günlüğü · tek kayıt kaynağı'))
        refresh=QPushButton('Yenile');refresh.clicked.connect(self.refresh_audit)
        head.addWidget(refresh);col.addLayout(head)
        self.audit_table=QTableWidget(0,4)
        self.audit_table.setHorizontalHeaderLabels(['Tarih','Bilgisayar/Kaynak','İşlem','Detay'])
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        self.audit_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        col.addWidget(self.audit_table);return page

    def refresh_audit(self):
        def display(payload):
            entries=[]
            for x in payload.get('device_activity',[]):
                entries.append((str(x.get('created_at','')),
                  str(x.get('device_name','')),
                  str(x.get('action','')),
                  ', '.join(x.get('order_ids') or [])[:100]))
            for x in payload.get('audit_events',[]):
                entries.append((str(x.get('created_at','')),
                  str(x.get('entity_name','')),
                  str(x.get('action','')),
                  ', '.join(x.get('changed_fields') or [])[:100]))
            entries.sort(reverse=True);entries=entries[:400]
            self.audit_table.setRowCount(len(entries))
            for i,row in enumerate(entries):
                for j,val in enumerate(row):self.audit_table.setItem(i,j,QTableWidgetItem(val))
        self._job(lambda:admin_request(self.cloud,'admin_audit'),display)

    def show_tab(self,index):
        super().show_tab(index)
        if index==3:self.refresh_devices()
        if index==4:self.refresh_audit()
