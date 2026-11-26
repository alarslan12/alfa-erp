"""ALFA ERP desktop settings: appearance, notification tones and local PDF covers."""
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QComboBox,
    QFileDialog, QMessageBox, QStackedWidget, QLabel, QPushButton, QLineEdit, QCheckBox, QScrollArea
)
from ayar_yonetimi import theme_styles, apply_visual_preferences
from tema import QSS
from pdf_kitap import PdfKutuphane
from pdf_kapak import refresh_pdf_covers
from bildirim_sesleri import SOUND_CHOICES, play_order_sound
from guncelleme_arayuzu import (UpdateDialog,CheckWorker,should_check_today,mark_checked)
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
        self._update_check_worker=None
        self._excel_job=None
        self._excel_rows=[]
        root=QVBoxLayout(self)
        root.addWidget(text('ÇALIŞMA AYARLARI','SettingsTitle'))
        self.nav=[]
        nav=QHBoxLayout()
        for i,label in enumerate(('Uygulama Ayarları','Bildirimler ve Güncelleme')):
            tab=button(label,'SettingsNav')
            tab.setCheckable(True)
            tab.clicked.connect(lambda checked=False,x=i:self.show_tab(x))
            nav.addWidget(tab)
            self.nav.append(tab)
        nav.addStretch()
        root.addLayout(nav)
        self.stack=QStackedWidget()
        root.addWidget(self.stack)

        # Existing appearance tab, adding sound selection in the SAME page
        # (keeps owner settings' tab indices and navigation unchanged).
        page=QWidget()
        col=QVBoxLayout(page)
        application_page=page
        application_col=col
        card=QFrame();card.setObjectName('SettingsCard')
        controls=QVBoxLayout(card)
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
        col=QVBoxLayout(notification_page)

        sound_card=QFrame();sound_card.setObjectName('SettingsCard')
        sound_col=QVBoxLayout(sound_card)
        sound_col.addWidget(text('Yeni sipariş bildirim sesi','SettingsHeading'))
        explain=QLabel('Personel bildirici çalışırken de geçerlidir. '
            'Farklı tonları dinleyebilir veya her siparişte değişen sesi seçebilirsin.')
        explain.setObjectName('SettingsHint')
        explain.setWordWrap(True)
        sound_col.addWidget(explain)
        sound_row=QHBoxLayout()
        self.sound=QComboBox()
        for mode,label in SOUND_CHOICES:
            self.sound.addItem(label,mode)
        chosen=str(config.get('bildirim_sesi','klasik'))
        index=self.sound.findData(chosen)
        self.sound.setCurrentIndex(max(0,index))
        self.sound.currentIndexChanged.connect(self.save_sound)
        sound_row.addWidget(self.sound,1)
        preview=button('▶  Sesi dinle','Accent')
        preview.clicked.connect(self.preview_sound)
        sound_row.addWidget(preview)
        sound_col.addLayout(sound_row)
        sound_col.addWidget(text('Sesler cihazda oynatılır; bulut ses API bağlantısı kullanılmaz.','SettingsHint',wrap=True))
        col.addWidget(sound_card)
        update_card=QFrame();update_card.setObjectName('SettingsCard')
        update_layout=QVBoxLayout(update_card)
        update_layout.addWidget(text('Güncelleme Merkezi','SettingsHeading'))
        self.update_notice=QLabel(
            'Kararlı güncellemeler GitHub Releases üzerinden kontrol edilir. '
            'İndirme ve yükleme için onayın gerekir.')
        self.update_notice.setObjectName('SettingsHint')
        self.update_notice.setWordWrap(True)
        update_layout.addWidget(self.update_notice)
        open_update=button('↻ Güncelleme Merkezi’ni aç','Accent')
        open_update.clicked.connect(self.open_update_center)
        update_layout.addWidget(open_update)
        col.addWidget(update_card)
        col.addStretch()
        # PDF and Excel catalog controls share the first settings tab.
        columns=QHBoxLayout()
        columns.setSpacing(14)
        application_col.addLayout(columns)
        pdf_page=QWidget()
        col=QVBoxLayout(pdf_page)
        col.setContentsMargins(0,0,0,0)
        card=QFrame();card.setObjectName('SettingsCard')
        controls=QVBoxLayout(card)
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
        col.addWidget(card)
        col.addStretch()
        columns.addWidget(pdf_page,1)
        columns.addWidget(self._excel_settings_page(),1)
        application_col.addWidget(appearance_card)
        application_col.addStretch()
        application_scroll=QScrollArea()
        application_scroll.setWidgetResizable(True)
        application_scroll.setWidget(application_page)
        self.stack.addWidget(application_scroll)
        self.stack.addWidget(notification_page)

        self.show_tab(0)
        # Only filesystem mtime checks on later app launches; no PDF pages
        # are rendered again unless changed or newly added.
        app=QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._stop_cover_worker)
            app.aboutToQuit.connect(self._stop_update_worker)
        if self.pdf.folder:
            QTimer.singleShot(2400,self.generate_pdf_covers)
        # One background release check at most once per 24h. No periodic timer.
        QTimer.singleShot(11000,self.check_updates_on_startup)

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

    def set_theme(self,key):
        self.config.set('tema',key)
        apply_visual_preferences(self.config)
        refresh_cover_placeholders()
        self.show_tab(0)

    def set_colorblind_mode(self,enabled):
        self.config.set('colorblind_mode',bool(enabled))
        apply_visual_preferences(self.config)

    def save_sound(self,*_):
        mode=str(self.sound.currentData() or 'klasik')
        self.config.set('bildirim_sesi',mode)

    def preview_sound(self):
        mode=str(self.sound.currentData() or 'klasik')
        if not play_order_sound(mode,self.config.data_dir):
            QMessageBox.information(self,'Bildirim sesi',
                'Bu bilgisayarda Windows ses çıkışı kullanılamıyor.')

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
        self.pdf_status.setText(result)
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
        page=QWidget()
        col=QVBoxLayout(page)
        card=QFrame();card.setObjectName("SettingsCard")
        layout=QVBoxLayout(card)
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
        col.addWidget(card);col.addStretch()
        return page

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

    def check_updates_on_startup(self):
        version,edition=self._update_identity()
        if self._update_check_worker is not None:
            return
        if not should_check_today(self.config.data_dir,edition):
            return
        try:mark_checked(self.config.data_dir,edition)
        except (OSError,ValueError):
            return
        job=CheckWorker(version,edition,self)
        self._update_check_worker=job
        outcome={"value":None}
        job.done.connect(lambda result:outcome.update(value=result))
        def finished():
            job.wait()
            self._update_check_worker=None
            result=outcome["value"]
            if result and result.get("available"):
                newer=str(result.get("version") or "?")
                self.update_notice.setText(
                    f"Yeni kararlı sürüm: V{newer} · Güncelleme Merkezi'nden indir.")
                parent=self.window()
                if hasattr(parent,"statusBar"):
                    parent.statusBar().showMessage(
                        f"ALFA ERP V{newer} güncellemesi mevcut · Ayarlar → Güncelleme Merkezi",
                        16000)
        job.finished.connect(finished)
        job.finished.connect(job.deleteLater)
        job.start()

    def _stop_update_worker(self):
        job=self._update_check_worker
        if job is not None:
            try:
                if job.isRunning():
                    job.requestInterruption()
                    job.wait()
            except RuntimeError:
                pass

    def _stop_cover_worker(self):
        worker=self._cover_worker
        if worker is not None:
            try:
                if worker.isRunning():
                    worker.requestInterruption()
                    worker.wait()
            except RuntimeError:
                pass
