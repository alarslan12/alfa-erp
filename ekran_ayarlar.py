"""ALFA ERP desktop settings: appearance, notification tones and local PDF covers."""
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QComboBox,
    QFileDialog, QMessageBox, QStackedWidget, QLabel, QPushButton, QLineEdit, QCheckBox, QScrollArea, QSplitter
)
from ayar_yonetimi import theme_styles, apply_visual_preferences
from tema import QSS
from pdf_kitap import PdfKutuphane
from pdf_kapak import refresh_pdf_covers
from bildirim_sesleri import play_order_sound
from guncelleme_arayuzu import UpdateDialog
from widgets import (
    button, text, refresh_cover_placeholders, refresh_all_cover_labels
)
from katalog_excel_aktar import preview_excel_catalog


class CoverWorker(QThread):
    progress=Signal(int,int)
    completed=Signal(dict)
    failed=Signal(str)

    def __init__(self,data_dir,codes,parent=None):
        super().__init__(parent)
        self.data_dir=Path(data_dir)
        self.codes=tuple(codes)

    def run(self):
        def progress(done,total):
            if self.isInterruptionRequested():
                raise InterruptedError()
            if done==total or done%20==0:
                self.progress.emit(done,total)
        try:
            outcome=refresh_pdf_covers(self.data_dir,self.codes,progress=progress)
            if not self.isInterruptionRequested():
                self.completed.emit(outcome)
        except InterruptedError:
            pass
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc)[:260])


class StaffExcelUploadJob(QThread):
    completed=Signal(dict)
    failed=Signal(str)
    def __init__(self,client,books,parent=None):
        super().__init__(parent)
        self.client,self.books=client,books
    def run(self):
        try:
            from rtdb_owner_admin import staff_catalog_import
            self.completed.emit(staff_catalog_import(self.client,self.books))
        except Exception as exc:
            self.failed.emit(str(exc)[:270])


class SettingsPage(QWidget):
    def __init__(self,db,config):
        super().__init__()
        self.db=db
        self.config=config
        self.pdf=PdfKutuphane(Path(db.siparis_dosyasi).parent)
        self._cover_worker=None
        self._excel_job=None
        self._excel_rows=[]
        root=QVBoxLayout(self)
        root.setContentsMargins(12,8,12,12);root.setSpacing(10)
        root.addWidget(text('ÇALIŞMA AYARLARI','SettingsTitle'))
        self.nav=[]
        nav_frame=QFrame();nav_frame.setObjectName('SettingsNavShell')
        nav=QHBoxLayout(nav_frame);nav.setContentsMargins(6,6,6,6);nav.setSpacing(6)
        self.settings_nav=nav
        for i,label in enumerate(('Uygulama Ayarları','Bildirimler & Cihazlar')):
            tab=button(label,'SettingsNav')
            self.style_nav(tab)
            tab.setCheckable(True)
            tab.clicked.connect(lambda checked=False,x=i:self.show_tab(x))
            nav.addWidget(tab)
            self.nav.append(tab)
        nav.addStretch()
        root.addWidget(nav_frame)
        self.stack=QStackedWidget()
        root.addWidget(self.stack,1)

        # Existing appearance tab, adding sound selection in the SAME page
        # (keeps owner settings' tab indices and navigation unchanged).
        page=QWidget()
        col=QVBoxLayout(page)
        col.setContentsMargins(0,0,0,0);col.setSpacing(12)
        application_page=page
        application_col=col
        card=QFrame();card.setObjectName('SettingsCard')
        controls=QVBoxLayout(card)
        controls.setContentsMargins(16,14,16,14);controls.setSpacing(10)
        controls.addWidget(text('Görünüm','SettingsHeading'))
        theme_row=QHBoxLayout()
        self.themes=[]
        for key,label in [('koyu','Koyu'),('acik','Açık'),('kontrast','Yüksek kontrast')]:
            action=button(label,'SettingsThemeOption')
            action.setCheckable(True)
            action.clicked.connect(lambda checked=False,k=key:self.set_theme(k))
            theme_row.addWidget(action)
            self.themes.append((key,action))
        controls.addLayout(theme_row)
        self.colorblind_check=QCheckBox('Renk körlüğü modu · yüksek görünürlük')
        self.colorblind_check.setChecked(self.config.get('colorblind_mode',False) is True)
        self.colorblind_check.setToolTip('Kırmızı-yeşil ayrımına alternatif: kolilenen ve tamamlananlar elektrik mavisi; okunmamış uyarılar parlak sarı.')
        self.colorblind_check.toggled.connect(self.set_colorblind_mode)
        controls.addWidget(self.colorblind_check)
        controls.addWidget(text('✓ Kolilendi / tamamlandı: cyan   ·   ⚠ Not / güncelleme: sarı','SettingsHint',wrap=True))
        self.show_unknown_pages=QCheckBox('Sayfa sayısı olmayan kitapları katalogda göster')
        self.show_unknown_pages.setToolTip('Varsayılan: gizli. Bu seçenek yalnızca katalog görünümünü değiştirir; Firebase kitaplarını silmez.')
        self.show_unknown_pages.setChecked(
            bool(self.config.get('show_books_without_pages', False)))
        self.show_unknown_pages.toggled.connect(self._set_unknown_page_visibility)
        controls.addWidget(self.show_unknown_pages)
        appearance_card=card
        notification_page=QWidget()
        col=QVBoxLayout(notification_page);col.setContentsMargins(0,0,0,0)
        self.notification_split=QSplitter(Qt.Orientation.Horizontal)
        self.notification_split.setChildrenCollapsible(False)
        self.notification_split.setHandleWidth(12)
        col.addWidget(self.notification_split,1)
        sound_card=QFrame();sound_card.setObjectName('SettingsCard')
        sound_col=QVBoxLayout(sound_card)
        sound_col.setContentsMargins(16,16,16,16);sound_col.setSpacing(10)
        sound_col.addWidget(text('Sipariş anonsları','SettingsHeading'))
        sound_col.addWidget(text('Her yeni siparişte dört Ozan anonsundan biri rastgele çalar. Düğmeler yalnızca ses testi içindir.','SettingsHint',wrap=True))
        sound_col.addWidget(text('● Otomatik · Rastgele Ozan','SettingsStatusPill'))
        from bildirim_dogal_ses import ANNOUNCEMENTS, announcement_asset
        for i,phrase in enumerate(ANNOUNCEMENTS):
            row=QFrame();row.setObjectName('SettingsInset')
            line=QHBoxLayout(row);line.setContentsMargins(12,8,12,8);line.setSpacing(10)
            label=QVBoxLayout();label.setSpacing(3)
            label.addWidget(text(f'Ozan {i+1}','SettingsHeading'))
            label.addWidget(text(phrase,'SettingsHint',wrap=True))
            line.addLayout(label,1)
            preview=button('▶ Dinle','SettingsControl')
            preview.setFixedHeight(36)
            preview.setAccessibleName(f'Ozan {i+1} anonsunu dinle')
            preview.clicked.connect(lambda _=False,n=i+1:self.preview_sound(f'ozan_{n}'))
            line.addWidget(preview)
            sound_col.addWidget(row)
        random_preview=button('▶ Rastgele dinle','Accent')
        random_preview.setFixedHeight(38)
        random_preview.clicked.connect(lambda _=False:self.preview_sound())
        sound_col.addWidget(random_preview)
        available=sum(announcement_asset(i).is_file() for i in range(4))
        sound_col.addWidget(text(f'{available}/4 yerel Ozan anonsu · İnternet gerekmez.','SettingsHint',wrap=True))
        sound_col.addStretch()
        self.notification_split.addWidget(sound_card)
        self.notification_split.addWidget(self._own_device_card())
        self.notification_split.setStretchFactor(0,1)
        self.notification_split.setStretchFactor(1,2)
        # PDF and Excel catalog controls share the first settings tab.
        columns=QHBoxLayout()
        columns.setSpacing(14)
        application_col.addLayout(columns)
        card=QFrame();card.setObjectName('SettingsCard')
        controls=QVBoxLayout(card);controls.setContentsMargins(16,14,16,14);controls.setSpacing(10)
        controls.addWidget(text('PDF kütüphanesi ve otomatik kitap kapakları','SettingsHeading'))
        note=QLabel('PDF dosya adında kitap kodu bulunması yeterli: '
            '31.pdf, kitap_31.pdf veya 31-endodonti.pdf. '
            'Yalnızca ilk sayfa JPEG kapağa dönüştürülür. '
            'Elle eklediğin kapaklar korunur; PDF dosyaları internete yüklenmez.')
        note.setObjectName('SettingsHint')
        note.setWordWrap(True)
        controls.addWidget(note)
        self.path=text('','SettingsHint',wrap=True)
        controls.addWidget(self.path)
        pdf_row=QHBoxLayout()
        pick=button('PDF klasörü seç','Accent')
        pick.clicked.connect(self.select_pdf)
        reload=button('Tara ve kapakları güncelle','SmallAction')
        reload.clicked.connect(self.rescan_pdf)
        pdf_row.addWidget(pick)
        pdf_row.addWidget(reload)
        controls.addLayout(pdf_row)
        self.pdf_status=QLabel('PDF kapağı üretimi henüz yapılmadı.')
        self.pdf_status.setObjectName('SettingsHint')
        self.pdf_status.setWordWrap(True)
        controls.addWidget(self.pdf_status)
        controls.addStretch()
        columns.addWidget(card,1)
        columns.addWidget(self._excel_settings_page(),1)
        application_col.addWidget(appearance_card)
        application_col.addStretch()
        application_scroll=QScrollArea()
        application_scroll.setWidgetResizable(True)
        application_scroll.setFrameShape(QFrame.Shape.NoFrame)
        application_scroll.setWidget(application_page)
        self.stack.addWidget(application_scroll)
        notification_scroll=QScrollArea()
        notification_scroll.setWidgetResizable(True)
        notification_scroll.setFrameShape(QFrame.Shape.NoFrame)
        notification_scroll.setWidget(notification_page)
        self.stack.addWidget(notification_scroll)

        self.show_tab(0)
        # Only filesystem mtime checks on later app launches; no PDF pages
        # are rendered again unless changed or newly added.
        app=QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._stop_cover_worker)
        if self.pdf.folder:
            QTimer.singleShot(2400,self.generate_pdf_covers)
        # Release checks are owned by the main window HUD.

    def _set_unknown_page_visibility(self,checked):
        self.config.set('show_books_without_pages',bool(checked))
        catalog=getattr(self.window(),'catalog',None)
        if catalog is not None:
            catalog.reset_results()

    def show_tab(self,index):
        self.current_tab=index
        self.stack.setCurrentIndex(index)
        for i,tab in enumerate(self.nav):
            tab.setChecked(i==index)
        for key,tab in self.themes:
            tab.setChecked(self.config.get('tema','koyu')==key)
        self.path.setText('PDF klasörü: '+str(self.pdf.folder or 'Henüz seçilmedi'))
        if index==1:
            self.refresh_own_device()

    def set_theme(self,key):
        self.config.set('tema',key)
        apply_visual_preferences(self.config)
        refresh_cover_placeholders()
        self.show_tab(0)

    def set_colorblind_mode(self,enabled):
        self.config.set('colorblind_mode',bool(enabled))
        apply_visual_preferences(self.config)

    @staticmethod
    def style_nav(tab):
        tab.setFixedHeight(40)
        tab.setMinimumWidth(144)

    def _own_device_card(self):
        card=QFrame();card.setObjectName('SettingsCard')
        layout=QVBoxLayout(card);layout.setContentsMargins(16,16,16,16);layout.setSpacing(12)
        layout.addWidget(text('Bu bilgisayar','SettingsHeading'))
        self.device_summary=text('Cihaz bağlantısı hazırlanıyor…','SettingsStatusPill',wrap=True)
        layout.addWidget(self.device_summary)
        self.device_uid=text('','SettingsHint',wrap=True)
        self.device_uid.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.device_uid)
        access=button('🛡 Cihaz yetkisini aç','SettingsControl')
        access.setFixedHeight(38)
        access.clicked.connect(lambda _=False:self._open_own_device())
        layout.addWidget(access)
        layout.addStretch()
        return card

    def _open_own_device(self):
        main=self.window()
        if hasattr(main,'connect_cloud'):
            main.connect_cloud()
        self.refresh_own_device()

    def refresh_own_device(self):
        client=getattr(self.window(),'device',None)
        if client is None or self.device_summary is None:
            return
        self.device_summary.setText('● Cihaz eşleştirildi' if client.paired else '○ Yetkilendirme gerekli')
        self.device_uid.setText('Cihaz kimliği (UID): '+str(getattr(client,'uid','') or 'Henüz oluşturulmadı'))

    def preview_sound(self,mode='ozan_karisik'):
        def failed():
            QTimer.singleShot(0,lambda:QMessageBox.information(
                self,'Bildirim sesi','Ozan ses dosyası oynatılamadı. Ses çıkışını kontrol edin.'))
        if not play_order_sound(mode,self.config.data_dir,on_error=failed):
            failed()

    def select_pdf(self):
        folder=QFileDialog.getExistingDirectory(
            self,'PDF klasörünü seç',str(self.pdf.folder or Path.home()))
        if not folder:
            return
        try:
            self.pdf.set_folder(folder)
            self.show_tab(0)
            self.generate_pdf_covers()
        except Exception as exc:
            QMessageBox.warning(self,'PDF',str(exc))

    def rescan_pdf(self):
        self.generate_pdf_covers()

    def generate_pdf_covers(self):
        if self._cover_worker and self._cover_worker.isRunning():
            self.pdf_status.setText('PDF kapak taraması zaten devam ediyor.')
            return
        if not self.pdf.folder:
            self.pdf_status.setText('Kapak oluşturmak için PDF klasörü seç.')
            return
        codes=[{'kod':str(book.get('kod') or ''),
                'isim':str(book.get('isim') or '')} for book in self.db.kitaplar]
        self.pdf_status.setText(
            f'{len(codes)} kitap kodu için PDF kapakları kontrol ediliyor…')
        worker=CoverWorker(self.pdf.data_dir,codes,self)
        self._cover_worker=worker
        worker.progress.connect(self._cover_progress)
        worker.completed.connect(self._covers_done)
        worker.failed.connect(self._covers_failed)
        worker.finished.connect(lambda w=worker:self._cover_finished(w))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _cover_progress(self,done,total):
        self.pdf_status.setText(f'PDF klasörü kontrol ediliyor: {done}/{total}')

    def _covers_done(self,counts):
        result=(
            f"PDF klasörü: {counts.get('pdf_found',0)} dosya · "
            f"Eşleşen kitap: {counts.get('matched',0)} · "
            f"Yeni/güncel kapak: {counts.get('created',0)} · "
            f"Önbellekten: {counts.get('unchanged',0)} · "
            f"Elle eklenmiş kapak: {counts.get('manual',0)} · "
            f"Eşleşmeyen PDF: {counts.get('unmatched_pdf',0)} · "
            f"Katalogda PDF bulunmayan: {counts.get('missing',0)} · "
            f"PDF işleme hatası: {counts.get('errors',0)}")
        examples=counts.get('unmatched_pdf_examples') or []
        if examples:
            result += " · Örnek: "+", ".join(examples[:3])
        self.pdf_status.setToolTip(
            "Eşleşmeyen PDF'ler: "+(", ".join(examples) or "Yok")+
            "\nİşleme sorunları: "+(", ".join(counts.get('error_examples') or []) or "Yok")+
            "\nTam rapor: "+str(self.pdf.data_dir/"alfa_pdf_eslestirme_raporu.json"))
        self.pdf_status.setText(
            f"{counts.get('pdf_found',0)} PDF  ·  {counts.get('matched',0)} eşleşen kitap\n"
            f"{counts.get('created',0)} güncellenen  ·  {counts.get('unchanged',0)} önbellek  ·  "
            f"{counts.get('manual',0)} elle eklenen\n"
            f"{counts.get('unmatched_pdf',0)} eşleşmeyen  ·  {counts.get('missing',0)} eksik PDF  ·  "
            f"{counts.get('errors',0)} hata")
        self.pdf_status.setToolTip(result+"\n"+self.pdf_status.toolTip())
        main=self.window()
        covers=getattr(main,'covers',None)
        if covers:
            covers.refresh()
            refresh_all_cover_labels()

    def _covers_failed(self,message):
        self.pdf_status.setText('PDF kapak taraması tamamlanamadı: '+message)

    def _cover_finished(self,worker):
        if self._cover_worker is worker:
            self._cover_worker=None

    def _excel_settings_page(self):
        return self._staff_excel_page()

    def _staff_excel_page(self):
        card=QFrame();card.setObjectName("SettingsCard")
        layout=QVBoxLayout(card);layout.setContentsMargins(16,14,16,14);layout.setSpacing(10)
        layout.addWidget(text("Excel kitap kataloğu","SettingsHeading"))
        note=QLabel(
            "Onaylı personel cihazı Excel kataloğunu ortak Firebase kitap "
            "listesine aktarır. İşlem tüm bilgisayarların ve mobil kataloğun "
            "kitaplarını günceller; siparişleri silmez. İnternet bağlantısı gerekir.")
        note.setWordWrap(True)
        layout.addWidget(note)
        controls=QHBoxLayout()
        pick=button("Excel seç (.xlsx)","Accent")
        pick.clicked.connect(self._staff_select_excel)
        controls.addWidget(pick)
        self.excel_upload=button("Buluta aktar","Accent")
        self.excel_upload.setEnabled(False)
        self.excel_upload.clicked.connect(self._staff_send_excel)
        controls.addWidget(self.excel_upload)
        layout.addLayout(controls)
        self.excel_note=QLabel("Excel henüz seçilmedi.")
        self.excel_note.setWordWrap(True)
        layout.addWidget(self.excel_note)
        layout.addStretch()
        return card

    def _staff_select_excel(self):
        source,_=QFileDialog.getOpenFileName(
            self,"Excel kitap kataloğu seç",str(Path.home()),"Excel (*.xlsx)")
        if not source:return
        try:
            self._excel_rows=preview_excel_catalog(source)
            self.excel_note.setText(
                Path(source).name+" · "+str(len(self._excel_rows))+" kitap hazır.")
            self.excel_upload.setEnabled(True)
        except Exception as exc:
            self._excel_rows=[]
            self.excel_upload.setEnabled(False)
            self.excel_note.setText("Excel okunamadı: "+str(exc)[:250])

    def _staff_send_excel(self):
        if not self._excel_rows or self._excel_job is not None:return
        if QMessageBox.question(
            self,"Ortak Excel kataloğu",
            str(len(self._excel_rows))+
            " kitap Firebase'de güncellensin mi? Eski katalog satırları "
            "pasifleştirilebilir. Siparişlere dokunulmaz.",
            QMessageBox.StandardButton.Yes|
            QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
            return
        client=getattr(self.window(),"device",None)
        if client is None or not client.paired:
            self.excel_note.setText("Önce cihazını Firebase'e yetkilendir.")
            return
        self.excel_upload.setEnabled(False)
        self.excel_note.setText("Ortak Firebase kataloğu güncelleniyor…")
        job=StaffExcelUploadJob(client,list(self._excel_rows),self)
        self._excel_job=job
        outcome={"error":None,"result":None}
        job.completed.connect(lambda value:outcome.update(result=value))
        job.failed.connect(lambda value:outcome.update(error=value))
        def done():
            job.wait()
            self._excel_job=None
            self.excel_upload.setEnabled(True)
            if outcome["error"]:
                self.excel_note.setText("Aktarım yapılamadı: "+outcome["error"])
                return
            count=(outcome["result"] or {}).get("count",0)
            self.excel_note.setText(
                str(count)+" kitap Firebase'e aktarıldı; katalog yenileniyor.")
            live=getattr(self.window(),"live",None)
            if live is not None:
                live.force_pull=True
                QTimer.singleShot(150,live.pull)
        job.finished.connect(done)
        job.finished.connect(job.deleteLater)
        job.start()

    def _update_identity(self):
        app=QApplication.instance()
        version=app.applicationVersion() or "1.1.1"
        edition=str(app.property("alfa_edition") or "staff")
        return version,edition

    def open_update_center(self):
        version,edition=self._update_identity()
        dialog=UpdateDialog(version,edition,self.config.data_dir,self)
        dialog.exec()

    def _stop_cover_worker(self):
        worker=self._cover_worker
        if worker is not None:
            try:
                if worker.isRunning():
                    worker.requestInterruption()
                    worker.wait()
            except RuntimeError:
                pass
