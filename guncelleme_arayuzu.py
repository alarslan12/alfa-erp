"""ALFA ERP owner/staff update-center UI.

A single silent GitHub check runs no more than once per 24 hours per edition;
user-triggered checks and downloads are asynchronous. There is NO recurring
timer, no GitHub API token embedded in the Windows installer, and no install
until an operator explicitly approves it. No data files are deleted.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from PySide6.QtCore import Qt,QThread,Signal,QTimer
from PySide6.QtWidgets import (
    QApplication,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QMessageBox,QProgressBar,QTextEdit,QFrame
)

from surum_gecmisi import release_history_markdown
from alfa_guncelleme import (
    check_for_update,download_update,launch_update,UpdateError,
)


class CheckWorker(QThread):
    done=Signal(object)
    failed=Signal(str)
    def __init__(self,version,edition,parent=None):
        super().__init__(parent)
        self.version=version
        self.edition=edition
    def run(self):
        try:self.done.emit(check_for_update(self.version,self.edition))
        except Exception as exc:self.failed.emit(str(exc)[:230])


class DownloadWorker(QThread):
    done=Signal(object)
    failed=Signal(str)
    progress=Signal(int)
    def __init__(self,release,data_dir,parent=None):
        super().__init__(parent)
        self.release=release
        self.data_dir=data_dir
    def run(self):
        def progress(downloaded,total):
            if total:
                self.progress.emit(min(100,int(downloaded/total*100)))
        try:self.done.emit(download_update(
            self.release,self.data_dir,progress=progress))
        except Exception as exc:self.failed.emit(str(exc)[:250])


class UpdateDialog(QDialog):
    def __init__(self,version,edition,storage,parent=None):
        super().__init__(parent)
        self.version=str(version)
        self.edition=edition
        self.storage=Path(storage)
        self.release=None
        self.verified=None
        self._workers=set()
        self.setWindowTitle("ALFA ERP · Güncelleme Merkezi")
        self.resize(650,480)
        root=QVBoxLayout(self)
        title=QLabel("GÜNCELLEME MERKEZİ")
        title.setObjectName("OwnerHeading")
        root.addWidget(title)
        self.message=QLabel("Kurulu sürüm: "+self.version+" · yeni sürüm kontrol edilmedi")
        self.message.setWordWrap(True)
        # The helper outlives the ERP process. Its last failure must be
        # visible on the next launch rather than disappearing in the tray.
        previous=self.storage/"updates"/"last_update_error.txt"
        if previous.is_file():
            try:
                failure=previous.read_text(encoding="utf-8-sig").strip()[:260]
                if failure:
                    self.message.setText("Önceki güncelleme tamamlanamadı: "+failure)
            except OSError:
                pass
        root.addWidget(self.message)
        info=QLabel("Yalnızca GitHub'da kalıcı yayımlanmış kararlı sürümler "
            "kabul edilir. Kurulum SHA-256 ile doğrulanır. "
            "Sipariş kuyruğu doluyken güncelleme başlatılamaz.")
        info.setWordWrap(True)
        root.addWidget(info)
        self.notes=QTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setMarkdown(release_history_markdown(self.version))
        root.addWidget(self.notes,1)
        self.progress=QProgressBar()
        self.progress.setRange(0,100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)
        controls=QHBoxLayout()
        self.check=QPushButton("↻ Güncellemeyi kontrol et")
        self.check.clicked.connect(self.check_now)
        controls.addWidget(self.check)
        self.download=QPushButton("İndir ve doğrula")
        self.download.setEnabled(False)
        self.download.clicked.connect(self.download_now)
        controls.addWidget(self.download)
        self.install=QPushButton("Güncelle ve yeniden başlat")
        self.install.setObjectName("Accent")
        self.install.setEnabled(False)
        self.install.clicked.connect(self.install_now)
        controls.addWidget(self.install)
        root.addLayout(controls)
        bottom=QHBoxLayout()
        bottom.addStretch()
        close=QPushButton("Kapat")
        close.clicked.connect(self.close)
        bottom.addWidget(close)
        root.addLayout(bottom)
        app=QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._shutdown_jobs)

    def _worker(self,worker,on_done,on_fail):
        if self._workers:return
        self._workers.add(worker)
        result={"ok":False,"payload":None,"error":None}
        worker.done.connect(lambda x:result.update(ok=True,payload=x))
        worker.failed.connect(lambda x:result.update(error=x))
        def finished():
            worker.wait()
            self._workers.discard(worker)
            self.check.setEnabled(True)
            if result["ok"]:
                on_done(result["payload"])
            else:
                on_fail(result["error"] or "Güncelleme işlemi başarısız")
        worker.finished.connect(finished)
        worker.finished.connect(worker.deleteLater)
        self.check.setEnabled(False)
        self.download.setEnabled(False)
        worker.start()

    def check_now(self):
        self.release=None
        self.verified=None
        self.download.setEnabled(False)
        self.install.setEnabled(False)
        self.message.setText("GitHub kararlı sürümleri kontrol ediliyor…")
        def accepted(result):
            if not result.get("available"):
                self.message.setText("Güncelsin · Kurulu sürüm: "+self.version+
                                     " · Son yayımlanan: "+str(result.get("latest")))
                self.notes.setMarkdown(release_history_markdown(self.version))
                return
            self.release=result
            self.message.setText("Yeni kararlı sürüm bulundu: "+str(result["version"]))
            self.notes.setMarkdown(
                "## Yeni sürüm · v"+str(result.get("version") or "")+"\n\n"+
                (str(result.get("notes") or "") or "Bu sürüm için ek not bulunmuyor.")+
                "\n\n---\n\n"+release_history_markdown(self.version))
            self.download.setEnabled(True)
        def failed(message):
            self.message.setText("Güncelleme kontrolü: "+message)
        self._worker(CheckWorker(self.version,self.edition,self),accepted,failed)

    def download_now(self):
        if not self.release:return
        self.message.setText("Kurulum indiriliyor ve SHA-256 doğrulanıyor…")
        self.progress.setValue(0)
        self.progress.setVisible(True)
        worker=DownloadWorker(self.release,self.storage,self)
        worker.progress.connect(self.progress.setValue)
        def accepted(verified):
            self.verified=verified
            self.progress.setValue(100)
            self.message.setText(
                "Doğrulandı · "+str(verified.get("version"))+
                " · Kurulum için onay gerekiyor")
            self.install.setEnabled(True)
        def failed(message):
            self.progress.setVisible(False)
            self.message.setText("İndirme başarısız: "+message)
            self.download.setEnabled(True)
        self._worker(worker,accepted,failed)

    def _main_application(self):
        """Find the real QMainWindow, even when opened via Duyurular popup.

        A child AnnouncementDialog is itself a top-level window, so .window()
        can be that dialog instead of the ERP. The old implementation then
        skipped the pending-outbox guard and did not close the real app.
        """
        current=self.parent()
        while current is not None:
            if getattr(current,"db",None) is not None and hasattr(current,"live"):
                return current
            current=current.parent()
        for window in QApplication.topLevelWidgets():
            if getattr(window,"db",None) is not None and hasattr(window,"live"):
                return window
        return None

    def install_now(self):
        if not self.verified:return
        main=self._main_application()
        if main is None:
            QMessageBox.warning(self,"Güncelleme",
                "Ana ALFA ERP penceresi bulunamadı. Uygulamayı yeniden açıp deneyin.")
            return
        database=main.db
        pending=int(getattr(database,"pending_count",0) or 0)
        live=getattr(main,"live",None)
        if pending:
            QMessageBox.warning(self,"Güncelleme",
                f"Önce buluta gönderilmeyi bekleyen {pending} işlem tamamlanmalı.")
            return
        if live and (getattr(live,"push_task",None) or getattr(live,"pull_task",None)):
            QMessageBox.warning(self,"Güncelleme",
                "Şu anda eşitleme sürüyor. İşlem bitince yeniden deneyin.")
            return
        yes=QMessageBox.question(self,"Kurulumu başlat",
            "ALFA ERP kapanacak. Ardından Windows kurulum sihirbazı açılacak "
            "(Yönetici erişimi Firebase rolüyle doğrulanır). Kurulum tamamlanırsa "
            "uygulama otomatik yeniden başlatılacak. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if yes!=QMessageBox.StandardButton.Yes:return
        try:
            launch_update(self.verified,self.storage,sys.executable,pending=pending)
        except (UpdateError,OSError,RuntimeError) as exc:
            QMessageBox.warning(self,"Güncelleme başlatılamadı",str(exc))
            return
        # QDialog.exec() creates a nested event loop. Calling app.quit()
        # directly from inside the modal loop may not close the main
        # application, leaving PowerShell waiting for its parent PID.
        self.accept()
        def close_real_erp():
            if not main.close():
                QMessageBox.warning(main,"Güncelleme",
                    "ALFA ERP kapanamadı. Kurulum başlatılmadı. "
                    "Önce tüm açık pencereleri kapatıp yeniden deneyin.")
                return
            QApplication.instance().quit()
        QTimer.singleShot(0,close_real_erp)

    def closeEvent(self,event):
        if self._workers:
            QMessageBox.information(self,"Güncelleme",
                "İndirme veya sürüm kontrolü tamamlanırken pencere kapatılamaz.")
            event.ignore()
            return
        super().closeEvent(event)

    def _shutdown_jobs(self):
        for job in list(self._workers):
            if job.isRunning():
                job.requestInterruption()
                job.wait()


def _state_path(storage,edition):
    return Path(storage)/("last_update_check_"+edition+".json")


def should_check_today(storage,edition):
    """Purely local 24-hour throttle, without any always-running timer."""
    path=_state_path(storage,edition)
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
        return time.time()-float(value.get("at") or 0)>=24*3600
    except (OSError,ValueError,TypeError):
        return True


def mark_checked(storage,edition):
    directory=Path(storage)
    directory.mkdir(parents=True,exist_ok=True)
    dest=_state_path(storage,edition)
    temporary=dest.with_suffix(".tmp")
    temporary.write_text(json.dumps({"at":time.time()}),encoding="utf-8")
    os.replace(temporary,dest)
