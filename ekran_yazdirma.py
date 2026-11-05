"""ALFA ERP / Yazdırma Kontrol Merkezi — local, read-only first phase.

This shows the Windows spool queue, NOT a guaranteed physical printer counter.
No printer command, PDF content or customer/order data is sent to Firebase.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QScrollArea, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QListWidget, QAbstractItemView,
    QInputDialog, QMessageBox, QSpinBox, QSystemTrayIcon
)

from alfa_print_monitor import PrintJournal, PrintMonitor, ACTIVE, MIB


STATUS_LABELS = {
    "bekliyor":"Bekliyor",
    "aktarılıyor":"Spool'a aktarılıyor",
    "yazdırılıyor":"Windows: yazdırılıyor",
    "duraklatıldı":"Duraklatıldı",
    "müdahale":"Müdahale gerekli",
    "çevrimdışı":"Windows: yazıcı çevrimdışı",
    "kağıt_yok":"Kağıt yok",
    "bloklandı":"Yazıcı sürücüsü işi engelledi",
    "hata":"Hata",
    "spool_tamam":"Windows aktardı (fiziksel teyit yok)",
    "siliniyor":"Kuyruktan siliniyor",
    "silindi":"Windows: silindi",
    "kuyrukta_yok":"Kuyruktan kayboldu (sonuç bilinmiyor)",
}


def _palette():
    theme=str(QApplication.instance().property("alfa_theme") or "koyu")
    return {
        "acik":("#f5efe6","#fffaf3","#253c50","#50687b",
                "#cbbba2","#dce9f1","#9b5f13","#a34141"),
        "koyu":("#102033","#1c3147","#f3f8fe","#bbcedf",
                "#536f89","#254969","#f4c27b","#ff9b9b"),
        "kontrast":("#05090f","#152439","#ffffff","#e3effa",
                    "#9cb7d1","#284c70","#ffdb83","#ff8989"),
    }.get(theme,("#102033","#1c3147","#f3f8fe","#bbcedf",
                 "#536f89","#254969","#f4c27b","#ff9b9b"))


class PrinterCard(QFrame):
    def __init__(self, printer, label_job, parent=None):
        super().__init__(parent)
        self.setObjectName("PrintMonitorPrinterCard")
        self.setMinimumWidth(300)
        self.setMinimumHeight(210)
        name=printer["name"]
        bg,panel,fg,muted,edge,button,amber,red=_palette()
        self.setStyleSheet(f"""
            QFrame#PrintMonitorPrinterCard {{
                background:{panel};border:1px solid {edge};border-radius:14px;
            }}
            QLabel {{color:{fg};background:transparent;border:none;}}
            QLabel#PrintJobSubtitle {{color:{muted};font-size:11px;}}
            QLabel#PrintJobWarning {{color:{red};font-weight:800;}}
            QPushButton {{background:{button};color:{fg};border:1px solid {edge};
                border-radius:7px;padding:4px 9px;font-weight:650;}}
        """)
        root=QVBoxLayout(self)
        root.setContentsMargins(12,12,12,12)
        root.setSpacing(8)
        heading=QHBoxLayout()
        icon=QLabel("🖨")
        icon.setStyleSheet("font-size:18px")
        heading.addWidget(icon)
        title=QLabel(name)
        title.setWordWrap(True)
        title.setStyleSheet(f"font-weight:900;font-size:13px;color:{fg};")
        heading.addWidget(title,1)
        heading.addWidget(QLabel(str(len(printer["jobs"]))+" iş"))
        root.addLayout(heading)
        if printer["error"]:
            problem=QLabel("Kuyruğa erişilemiyor: "+printer["error"])
            problem.setObjectName("PrintJobWarning")
            problem.setWordWrap(True)
            root.addWidget(problem)
            root.addStretch(1)
            return
        if not printer["jobs"]:
            empty=QLabel("Kuyruk boş · Önceki işler Geçmiş sekmesinde saklanır.")
            empty.setObjectName("PrintJobSubtitle")
            empty.setWordWrap(True)
            root.addWidget(empty)
            root.addStretch(1)
            return
        jobs=sorted(printer["jobs"],key=lambda j:(j["position"],j["native_id"]))
        for idx,job in enumerate(jobs[:7]):
            line=QFrame()
            line.setObjectName("PrintJobRow")
            line.setStyleSheet(f"QFrame#PrintJobRow {{background:{bg};"
                               f"border:1px solid {edge};border-radius:9px;}}")
            col=QVBoxLayout(line)
            col.setContentsMargins(9,7,9,7);col.setSpacing(3)
            label=job.get("book_label") or job.get("document") or "Belge adı yok"
            top=QHBoxLayout()
            title=QLabel(f"#{job['native_id']}  {label}")
            title.setToolTip(job.get("document") or "")
            title.setWordWrap(True)
            title.setStyleSheet("font-weight:800")
            top.addWidget(title,1)
            edit=QPushButton("Etiketle")
            edit.setToolTip("Kitap adı ve SB/Renkli bilgisini yerel izleme günlüğüne kaydet")
            edit.clicked.connect(lambda _=False,j=dict(job):label_job(j))
            top.addWidget(edit)
            col.addLayout(top)
            state=job["state"]
            mode=job.get("mode_label") or job.get("color") or "Bilinmiyor"
            state_label=STATUS_LABELS.get(state,state)
            status=QLabel(f"{idx+1}. sıra  ·  {state_label}  ·  {mode}")
            status.setObjectName("PrintJobSubtitle")
            if state in ("hata","müdahale","çevrimdışı","kağıt_yok","bloklandı"):
                status.setStyleSheet(f"color:{red};font-weight:850")
            status.setWordWrap(True)
            col.addWidget(status)
            pages=job["pages"]
            total=job["total"]
            page_text=(f"Windows sayacı: {pages}/{total} sayfa" if total else
                       f"Windows sayacı: {pages} sayfa · toplam bilinmiyor")
            # Do not infer PDF page number, actual sheet count or physical output.
            summary=QLabel(f"{page_text}  ·  Spool {job['bytes']/MIB:.1f} MiB")
            summary.setToolTip("Spooler sayacı, fiziksel olarak çıkan son sayfa değildir.")
            summary.setObjectName("PrintJobSubtitle")
            col.addWidget(summary)
            root.addWidget(line)
        if len(jobs)>7:
            rest=QLabel(f"+ {len(jobs)-7} iş daha · tam liste kuyrukta korunuyor")
            rest.setObjectName("PrintJobSubtitle")
            root.addWidget(rest)
        root.addStretch(1)


class PrintSurveillanceView(QWidget):
    """Dashboard with persistent vertical/horizontal/grid printer mapping."""

    notify=Signal(str)

    def __init__(self,data_dir,parent=None):
        super().__init__(parent)
        self.setObjectName("PrintSurveillanceView")
        self.data_dir=Path(data_dir)
        self.config_file=self.data_dir/"print_monitor"/"layout.json"
        self.layout_mode="grid"
        self.printer_order=[]
        self.size_warning_mb=250
        self._last_signature=""
        self._last_snapshot=None
        self._worker=None
        self._tray=None
        self._read_layout()

        outer=QVBoxLayout(self)
        outer.setContentsMargins(10,8,10,10);outer.setSpacing(9)
        head=QHBoxLayout()
        title=QLabel("YAZDIRMA KONTROL MERKEZİ")
        title.setObjectName("PrintMonitorTitle")
        title.setStyleSheet("font-size:16px;font-weight:900")
        head.addWidget(title)
        head.addStretch()
        head.addWidget(QLabel("Düzen:"))
        self.layout_select=QComboBox()
        for key,label in (
            ("grid","▦ Kutucuklar"),
            ("vertical","↕ Dikey sıra"),
            ("horizontal","↔ Yatay sıra"),
        ):
            self.layout_select.addItem(label,key)
        self.layout_select.setCurrentIndex(
            max(0,self.layout_select.findData(self.layout_mode)))
        self.layout_select.currentIndexChanged.connect(self._mode_changed)
        head.addWidget(self.layout_select)
        order=QPushButton("Yazıcıları yerleştir")
        order.clicked.connect(self._configure_order)
        head.addWidget(order)
        outer.addLayout(head)

        explain=QLabel(
            "Windows yazdırma kuyruğunu izler. Sayfa sayacı ve 'tamamlandı' durumu "
            "fiziksel baskı garantisi değildir. PDF içeriği, iş adları ve geçmiş "
            "yalnız bu bilgisayarda tutulur."
        )
        explain.setWordWrap(True)
        explain.setObjectName("PrintMonitorDisclaimer")
        outer.addWidget(explain)
        options=QHBoxLayout()
        self.status=QLabel("Windows yazıcıları okunuyor…")
        options.addWidget(self.status,1)
        options.addWidget(QLabel("Büyük spool uyarısı:"))
        self.threshold=QSpinBox()
        self.threshold.setRange(20,2048)
        self.threshold.setSuffix(" MiB")
        self.threshold.setValue(self.size_warning_mb)
        self.threshold.valueChanged.connect(self._threshold_changed)
        options.addWidget(self.threshold)
        outer.addLayout(options)

        self.tabs=QTabWidget()
        self.scroll=QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.board=QWidget()
        self.board_layout=QGridLayout(self.board)
        self.board_layout.setContentsMargins(0,0,0,0)
        self.board_layout.setSpacing(10)
        self.scroll.setWidget(self.board)
        self.tabs.addTab(self.scroll,"Canlı yazıcılar")

        self.history=QTableWidget(0,7)
        self.history.setObjectName("PrintMonitorHistory")
        self.history.setHorizontalHeaderLabels([
            "Son görülen","Yazıcı","Belge / Kitap","Durum",
            "Windows sayfa","Tür","Spool MiB"
        ])
        self.history.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.history.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history.setAlternatingRowColors(True)
        self.history.verticalHeader().hide()
        self.history.horizontalHeader().setSectionResizeMode(
            2,QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.history,"Geçmiş · kapanıştan sonra saklanır")

        self.events=QTableWidget(0,4)
        self.events.setHorizontalHeaderLabels([
            "Zaman","Yazıcı","Olay","Açıklama"])
        self.events.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.events.verticalHeader().hide()
        self.events.horizontalHeader().setSectionResizeMode(
            3,QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.events,"Olay günlüğü")
        outer.addWidget(self.tabs,1)
        self.set_theme()
        if os.name=="nt":
            # Monitoring starts with ERP even if user doesn't open this tab.
            # No Firebase calls, spooler commands, or paid Windows services.
            self._worker=PrintMonitor(self.data_dir,self)
            self._worker.size_warning_mb=self.size_warning_mb
            self._worker.updated.connect(self._snapshot)
            self._worker.warning.connect(self._warning)
            self._worker.failed.connect(self._failure)
            self._worker.start()
            app=QApplication.instance()
            if app:
                app.aboutToQuit.connect(self.stop)
        else:
            self.status.setText("Yazdırma izleme yalnız Windows'ta çalışır.")

    def set_theme(self):
        bg,panel,fg,muted,edge,button,amber,red=_palette()
        self.setStyleSheet(f"""
            QWidget#PrintSurveillanceView {{background:{bg};color:{fg};}}
            QLabel {{color:{fg};background:transparent;}}
            QLabel#PrintMonitorDisclaimer {{color:{muted};}}
            QPushButton,QComboBox,QSpinBox {{background:{panel};color:{fg};
                border:1px solid {edge};border-radius:7px;padding:6px 8px;}}
            QTabWidget::pane {{background:{bg};border:1px solid {edge};}}
            QTabBar::tab {{background:{panel};color:{fg};
                padding:8px 15px;border:1px solid {edge};}}
            QTabBar::tab:selected {{background:{button};font-weight:800;}}
            QTableWidget {{background:{panel};color:{fg};
                alternate-background-color:{bg};gridline-color:{edge};}}
            QHeaderView::section {{background:{button};color:{fg};}}
        """)
        if self._last_snapshot:
            self._render_cards(self._last_snapshot["printers"])

    def _read_layout(self):
        try:
            value=json.loads(self.config_file.read_text(encoding="utf-8"))
            mode=value.get("layout","grid")
            if mode in ("grid","vertical","horizontal"):
                self.layout_mode=mode
            self.printer_order=[str(x)[:250] for x in value.get("printer_order",[])
                                if isinstance(x,str)][:100]
            self.size_warning_mb=max(20,min(2048,int(
                value.get("large_spool_mb",250))))
        except (OSError,ValueError,TypeError,AttributeError):
            pass

    def _save_layout(self):
        self.config_file.parent.mkdir(parents=True,exist_ok=True)
        data={"layout":self.layout_mode,
              "printer_order":self.printer_order[:100],
              "large_spool_mb":self.size_warning_mb}
        tmp=self.config_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,self.config_file)

    def _mode_changed(self):
        self.layout_mode=str(self.layout_select.currentData() or "grid")
        self._save_layout()
        if self._last_snapshot:
            self._render_cards(self._last_snapshot["printers"])

    def _threshold_changed(self,value):
        self.size_warning_mb=int(value)
        if self._worker:
            self._worker.size_warning_mb=self.size_warning_mb
        self._save_layout()

    def _configure_order(self):
        printers=self._last_snapshot["printers"] if self._last_snapshot else []
        names={p["name"] for p in printers}
        if not names:
            QMessageBox.information(self,"Yazıcı yerleşimi",
                                    "Henüz erişilebilir yazıcı bulunamadı.")
            return
        self.printer_order=[p for p in self.printer_order if p in names]+[
            p for p in sorted(names) if p not in self.printer_order]
        dialog=QDialog(self)
        dialog.setWindowTitle("Yazıcı yerleşimini düzenle")
        dialog.resize(450,450)
        layout=QVBoxLayout(dialog)
        tip=QLabel("Yazıcıları sürükleyip sırala. Düzen (kutucuk / dikey / yatay) "
                   "seçimiyle birlikte bu bilgisayarda saklanır.")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        order=QListWidget()
        order.addItems(self.printer_order)
        order.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        order.setDefaultDropAction(Qt.DropAction.MoveAction)
        layout.addWidget(order,1)
        actions=QHBoxLayout()
        accept=QPushButton("Yerleşimi kaydet")
        accept.clicked.connect(dialog.accept)
        cancel=QPushButton("Vazgeç")
        cancel.clicked.connect(dialog.reject)
        actions.addWidget(accept);actions.addWidget(cancel)
        layout.addLayout(actions)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.printer_order=[order.item(i).text()
                                for i in range(order.count())]
            self._save_layout()
            self._render_cards(printers)

    def _snapshot(self,result):
        self._last_snapshot=result
        printers=result["printers"]
        count=sum(len(p["jobs"]) for p in printers)
        blocked=sum(1 for p in printers if p["error"])
        self.status.setText(
            f"{len(printers)} yazıcı · {count} kuyruk işi · "
            f"{blocked} erişim sorunu · güncellendi {result['captured_at'][11:19]} UTC")
        # Only redraw changed states, not every 3-second heartbeat.
        payload=json.dumps(printers,ensure_ascii=False,sort_keys=True)
        if payload!=self._last_signature:
            self._last_signature=payload
            self._render_cards(printers)
            self._render_history(result["recent"])
            self._render_events(result["events"])

    def _render_cards(self,printers):
        while self.board_layout.count():
            item=self.board_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        order={name:i for i,name in enumerate(self.printer_order)}
        printers=sorted(printers,key=lambda p:(order.get(p["name"],9999),
                                               p["name"].casefold()))
        cols=1 if self.layout_mode=="vertical" else (
            len(printers) if self.layout_mode=="horizontal" else
            (3 if self.scroll.viewport().width()>=1250 else 2
             if self.scroll.viewport().width()>=720 else 1))
        cols=max(1,cols)
        if self.layout_mode=="horizontal":
            self.board.setMinimumWidth(max(self.scroll.viewport().width(),
                                           330*len(printers)))
        else:
            self.board.setMinimumWidth(0)
        for i,printer in enumerate(printers):
            card=PrinterCard(printer,self._label_job,self.board)
            self.board_layout.addWidget(card,i//cols,i%cols,
                                        Qt.AlignmentFlag.AlignTop)
        self.board_layout.setRowStretch((len(printers)+cols-1)//cols,1)
        if not printers:
            self.board_layout.addWidget(QLabel(
                "Bu Windows hesabında kurulu/bağlı yazıcı yok veya "
                "Print Spooler hizmeti kullanılamıyor."),0,0)

    def _render_history(self,rows):
        self.history.setRowCount(len(rows))
        for i,row in enumerate(rows):
            text=[
                str(row.get("last_seen") or "")[0:19].replace("T"," "),
                str(row.get("printer") or ""),
                str(row.get("book_label") or row.get("document") or ""),
                STATUS_LABELS.get(row.get("state"),str(row.get("state") or "")),
                str(row.get("pages") or 0)+"/"+
                    (str(row.get("total")) if row.get("total") else "?"),
                str(row.get("mode_label") or row.get("color") or "Bilinmiyor"),
                "%.1f"%(int(row.get("bytes") or 0)/MIB),
            ]
            for j,value in enumerate(text):
                self.history.setItem(i,j,QTableWidgetItem(value))

    def _render_events(self,rows):
        self.events.setRowCount(len(rows))
        for i,row in enumerate(rows):
            values=[
                str(row.get("at") or "")[:19].replace("T"," "),
                str(row.get("printer") or ""),str(row.get("kind") or ""),
                str(row.get("detail") or ""),
            ]
            for j,value in enumerate(values):
                self.events.setItem(i,j,QTableWidgetItem(value))

    def _label_job(self,job):
        book,ok=QInputDialog.getText(
            self,"Kitabı tanımla",
            "Yazdırma işi için kitap adı veya kodu (yalnız yerel kayıt):",
            text=str(job.get("book_label") or job.get("document") or "")[:100])
        if not ok:
            return
        modes=["Bilinmiyor","Siyah-beyaz (SB)","Renkli (RNK)"]
        current=str(job.get("mode_label") or "BELIRSIZ")
        idx={"BELIRSIZ":0,"SB":1,"RENK":2}.get(current,0)
        chosen,ok=QInputDialog.getItem(
            self,"Baskı türü","Bu işe atanacak baskı türü:",modes,idx,False)
        if not ok:
            return
        mode={"Bilinmiyor":"BELIRSIZ",
              "Siyah-beyaz (SB)":"SB","Renkli (RNK)":"RENK"}[chosen]
        try:
            journal=PrintJournal(self.data_dir)
            try:
                journal.set_label(job["key"],book,mode)
            finally:
                journal.close()
            job["book_label"]=book
            job["mode_label"]=mode
            if self._last_snapshot:
                self._last_signature=""
                self._render_cards(self._last_snapshot["printers"])
        except (OSError,sqlite3.Error,ValueError) as exc:
            QMessageBox.warning(self,"Yerel kitap etiketi",str(exc)[:220])

    def _warning(self,detail):
        self.notify.emit(detail)
        if QSystemTrayIcon.isSystemTrayAvailable():
            if self._tray is None:
                self._tray=QSystemTrayIcon(self.window().windowIcon(),self)
                self._tray.setToolTip("ALFA ERP · Yazdırma alarmları")
                self._tray.show()
            self._tray.showMessage("ALFA ERP · Yazdırma uyarısı",
                                   detail[:220],QSystemTrayIcon.MessageIcon.Warning,7000)

    def _failure(self,message):
        self.status.setText("Yazdırma izleme: "+str(message)[:200])

    def stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            # Some disconnected network print servers can block Win32 RPC.
            # Avoid endless GUI shutdown waiting; do not terminate spooler.
            self._worker.wait(3500)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.layout_mode=="grid" and self._last_snapshot:
            cols=3 if self.scroll.viewport().width()>=1250 else 2 if (
                self.scroll.viewport().width()>=720) else 1
            if getattr(self,"_last_columns",None)!=cols:
                self._last_columns=cols
                QTimer.singleShot(0,lambda:self._render_cards(
                    self._last_snapshot["printers"]) if self._last_snapshot else None)
