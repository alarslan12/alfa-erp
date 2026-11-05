"""ALFA ERP desktop settings: appearance, notification tones and local PDF covers."""
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QComboBox,
    QFileDialog, QMessageBox, QStackedWidget, QLabel
)
from ayar_yonetimi import theme_styles
from tema import QSS
from pdf_kitap import PdfKutuphane
from pdf_kapak import refresh_pdf_covers
from bildirim_sesleri import SOUND_CHOICES, play_order_sound
from guncelleme_arayuzu import (UpdateDialog,CheckWorker,should_check_today,mark_checked)
from widgets import (
    button, text, refresh_cover_placeholders, refresh_all_cover_labels
)


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


class SettingsPage(QWidget):
    def __init__(self,db,config):
        super().__init__()
        self.db=db
        self.config=config
        self.pdf=PdfKutuphane(Path(db.siparis_dosyasi).parent)
        self._cover_worker=None
        self._update_check_worker=None
        root=QVBoxLayout(self)
        root.addWidget(text('ÇALIŞMA AYARLARI','SettingsTitle'))
        self.nav=[]
        nav=QHBoxLayout()
        for i,label in enumerate(('Görünüm ve bildirimler','Kitap PDF klasörü')):
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
        col.addWidget(card)

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
        self.stack.addWidget(page)

        # Existing PDF folder selection, now also drives incremental covers.
        page=QWidget()
        col=QVBoxLayout(page)
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
        self.stack.addWidget(page)

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
        QApplication.instance().setProperty('alfa_theme',key)
        QApplication.instance().setStyleSheet(QSS+theme_styles(key))
        refresh_cover_placeholders()
        self.show_tab(0)

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
            self.show_tab(1)
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
        codes=[str(book.get('kod') or '') for book in self.db.kitaplar]
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
            f"PDF eşleşmesi: {counts.get('matched',0)} · "
            f"Yeni/güncel kapak: {counts.get('created',0)} · "
            f"Önbellekten: {counts.get('unchanged',0)} · "
            f"Elle eklenmiş kapak: {counts.get('manual',0)} · "
            f"Eşleşmeyen: {counts.get('missing',0)} · "
            f"Hata: {counts.get('errors',0)}")
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

    def _update_identity(self):
        app=QApplication.instance()
        version=app.applicationVersion() or "1.1.0"
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
