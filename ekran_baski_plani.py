"""ALFA ERP: operator-controlled book/PDF print plan.

All actions are LOCAL SQLite metadata. Creating a plan never calls a
printer driver, uploads PDFs or initiates physical printing.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDialog, QDialogButtonBox, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QSpinBox, QFileDialog, QMessageBox, QInputDialog
)

from alfa_print_plan import (
    PrintPlanRepository, PrintPlanError, STATE_NAMES
)


def _style(widget):
    theme=str(QApplication.instance().property("alfa_theme") or "koyu")
    colors={
        "acik":("#fffaf2","#f0e7db","#284158","#4a6679","#c4b296","#dce9f3"),
        "koyu":("#152538","#1d344b","#f4f8ff","#bfd3e4","#597b98","#284d6e"),
        "kontrast":("#070c13","#17293d","#ffffff","#e6f5ff","#93aecb","#335779")
    }
    bg,panel,fg,muted,edge,accent=colors.get(theme,colors["koyu"])
    widget.setStyleSheet(f"""
        QWidget#PrintPlanPanel {{background:{bg};color:{fg};}}
        QLabel {{color:{fg};background:transparent;}}
        QLabel#PrintPlanNote {{color:{muted};}}
        QPushButton,QSpinBox,QComboBox,QLineEdit {{
            background:{panel};color:{fg};border:1px solid {edge};
            border-radius:7px;padding:7px;
        }}
        QPushButton:hover {{border:2px solid {accent};}}
        QTableWidget {{color:{fg};background:{panel};
            alternate-background-color:{bg};gridline-color:{edge};}}
        QHeaderView::section {{background:{accent};color:{fg};padding:7px;}}
        QDialog {{color:{fg};background:{bg};}}
    """)


class PrintPlanPanel(QWidget):
    """A production plan, NOT the live Windows spool queue."""

    def __init__(self, data_dir, parent=None):
        super().__init__(parent)
        self.setObjectName("PrintPlanPanel")
        self.data_dir=Path(data_dir)
        self.repo=PrintPlanRepository(self.data_dir)
        self._printers=[]
        self._live_jobs=[]
        self._tasks=[]
        self._selected_id=None
        self._last_sig=""
        root=QVBoxLayout(self)
        root.setContentsMargins(9,9,9,10);root.setSpacing(10)

        lead=QLabel("KİTAP BASKI PLANI · YAZICI BAŞINA HAFIZALI SIRA")
        lead.setStyleSheet("font-size:15px;font-weight:900")
        root.addWidget(lead)

        intro=QLabel(
            "Bu plan yazıcıya kendi başına iş göndermez. Bir PDF'yi bir yazıcıya "
            "gönderdikten sonra Windows kuyruğundaki iş ile eşleştirin. "
            "Kuyruk kaybolsa bile plan ve baskı türü burada saklanır. "
            "Fiziksel bitiş yalnız operatör onayıyla işaretlenir."
        )
        intro.setObjectName("PrintPlanNote")
        intro.setWordWrap(True)
        root.addWidget(intro)

        toolbar=QHBoxLayout()
        self.printer_filter=QComboBox()
        self.printer_filter.addItem("Tüm yazıcılar","")
        self.printer_filter.currentIndexChanged.connect(self.render)
        toolbar.addWidget(self.printer_filter)
        self.add_button=QPushButton("＋ Baskı planla")
        self.add_button.clicked.connect(self.create_task)
        toolbar.addWidget(self.add_button)
        self.up_button=QPushButton("↑")
        self.up_button.setToolTip("Aynı yazıcıya ait planlanmış işi öne al")
        self.up_button.clicked.connect(lambda:self.move(-1))
        toolbar.addWidget(self.up_button)
        self.down_button=QPushButton("↓")
        self.down_button.setToolTip("Aynı yazıcıya ait planlanmış işi geriye al")
        self.down_button.clicked.connect(lambda:self.move(1))
        toolbar.addWidget(self.down_button)
        self.link_button=QPushButton("Windows işiyle eşleştir")
        self.link_button.clicked.connect(self.link_job)
        toolbar.addWidget(self.link_button)
        root.addLayout(toolbar)

        self.table=QTableWidget(0,8)
        self.table.setHorizontalHeaderLabels([
            "Sıra","Yazıcı","Kitap / PDF","Baskı türü",
            "Kopya · PDF sayfa aralığı","Durum",
            "Son Windows sayacı","Windows kuyruk ID"
        ])
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(
            2,QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        root.addWidget(self.table,1)

        footer=QHBoxLayout()
        self.summary=QLabel("Henüz baskı planı eklenmedi.")
        self.summary.setObjectName("PrintPlanNote")
        footer.addWidget(self.summary,1)
        self.detail_button=QPushButton("İş geçmişi")
        self.detail_button.clicked.connect(self.inspect_task)
        footer.addWidget(self.detail_button)
        self.resume_button=QPushButton("↻ Kesilen baskıya devam")
        self.resume_button.setToolTip(
            "Windows'un son sayacını gösterir; kontrol ettiğin son sağlam "
            "PDF sayfasından yeni baskı planı oluşturur, otomatik basmaz.")
        self.resume_button.clicked.connect(self.resume_task)
        footer.addWidget(self.resume_button)
        self.verify_button=QPushButton("✓ Fiziksel baskıyı teyit et")
        self.verify_button.clicked.connect(self.verify_task)
        footer.addWidget(self.verify_button)
        self.cancel_button=QPushButton("Planı iptal et")
        self.cancel_button.clicked.connect(self.cancel_task)
        footer.addWidget(self.cancel_button)
        root.addLayout(footer)

        app=QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._close)
        self.set_theme()
        self.reload()

    def _close(self):
        if self.repo is not None:
            self.repo.close()
            self.repo=None

    def set_theme(self):
        _style(self)

    def set_snapshot(self,printers,tasks=None):
        self._printers=[dict(p) for p in printers]
        self._live_jobs=[
            dict(job) for printer in printers if not printer.get("error")
            for job in printer.get("jobs",())
        ]
        current=str(self.printer_filter.currentData() or "")
        names=sorted({p["name"] for p in printers})
        if set(names)!=set(self.printer_filter.itemText(i)
                           for i in range(1,self.printer_filter.count())):
            self.printer_filter.blockSignals(True)
            self.printer_filter.clear()
            self.printer_filter.addItem("Tüm yazıcılar","")
            for name in names:
                self.printer_filter.addItem(name,name)
            self.printer_filter.setCurrentIndex(
                max(0,self.printer_filter.findData(current)))
            self.printer_filter.blockSignals(False)
        if tasks is not None:
            self._tasks=[dict(t) for t in tasks]
            self.render()
        else:
            self.reload()

    def reload(self):
        try:
            self._tasks=self.repo.list(500)
            self.render()
        except (OSError,sqlite3.Error) as exc:
            QMessageBox.warning(self,"Baskı planı",str(exc)[:220])

    def _selected(self):
        row=self.table.currentRow()
        item=self.table.item(row,0) if row>=0 else None
        task_id=str(item.data(Qt.ItemDataRole.UserRole)) if item else None
        return next((t for t in self._tasks if t["task_id"]==task_id),None)

    def _selection_changed(self):
        task=self._selected()
        if task is not None:
            self._selected_id=task["task_id"]
        planned=bool(task and task["state"]=="planned")
        self.up_button.setEnabled(planned)
        self.down_button.setEnabled(planned)
        self.link_button.setEnabled(planned)
        self.cancel_button.setEnabled(planned)
        self.verify_button.setEnabled(bool(
            task and task["state"] in ("queued","verify")))
        can_resume=bool(
            task and task["state"]=="verify" and
            int(task["copies"])==1 and
            not any(t.get("parent_task_id")==task["task_id"]
                    for t in self._tasks))
        self.resume_button.setEnabled(can_resume)
        self.resume_button.setToolTip(
            "Yalnız tek kopyalık, kuyruktan kaybolmuş işlerde. "
            "Windows'un sayacı fiziksel sayfa teyidi değildir. "
            "Çoklu kopyalar ayrı ayrı kontrol edilip planlanmalıdır.")
        self.detail_button.setEnabled(bool(task))

    def render(self):
        chosen=str(self.printer_filter.currentData() or "")
        selected=self._selected_id
        rows=[t for t in self._tasks
              if not chosen or t["printer"]==chosen]
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        restore_row=-1
        for i,t in enumerate(rows):
            if t["task_id"]==selected:
                restore_row=i
            mode="Siyah-beyaz" if t["mode"]=="SB" else "Renkli"
            pages=(f"{t['page_start']}-{t['page_end']}"
                   if t["page_end"] else
                   "Tüm sayfalar" if t["page_start"]==1
                   else f"{t['page_start']}. sayfadan itibaren")
            name=t["book"]+(f"\n{t['book_code']}" if t["book_code"] else "")
            job=(str(t["linked_job_key"])[:12]+"…"
                 if t.get("linked_job_key") else "Henüz eşleşmedi")
            reported=int(t.get("last_reported_pages") or 0)
            last_counter=(f"{reported} (fiziksel değil)" if
                          t.get("last_reported_at") else "Bilinmiyor")
            values=[
                str(t["sort_index"]),t["printer"],name,mode,
                f"{t['copies']} kopya · {pages}",
                STATE_NAMES.get(t["state"],t["state"]),
                last_counter,job
            ]
            for j,val in enumerate(values):
                item=QTableWidgetItem(str(val))
                if j==0:
                    item.setData(Qt.ItemDataRole.UserRole,t["task_id"])
                if j==2:
                    item.setToolTip(str(t.get("pdf_path") or
                                        "Yerel PDF yolu eklenmedi"))
                if j==6:
                    item.setToolTip(
                        "Windows PagesPrinted sayacı. Son fiziksel "
                        "çıkan PDF sayfası olmayabilir; kâğıdı kontrol edin.")
                self.table.setItem(i,j,item)
        self.table.blockSignals(False)
        if restore_row>=0:
            self.table.selectRow(restore_row)
        else:
            self._selected_id=None
        counts={state:sum(t["state"]==state for t in self._tasks)
                for state in STATE_NAMES}
        self.summary.setText(
            f"{len(self._tasks)} plan · {counts['planned']} sırada · "
            f"{counts['queued']} Windows kuyruğunda · "
            f"{counts['verify']} fiziksel kontrol bekliyor"
        )
        self._selection_changed()

    def create_task(self):
        if not self._printers:
            QMessageBox.information(self,"Baskı planı",
                "Önce bu bilgisayarın erişebildiği bir Windows yazıcısı olmalı.")
            return
        dlg=QDialog(self)
        dlg.setWindowTitle("Kitap / PDF baskı planı oluştur")
        dlg.resize(565,390)
        layout=QVBoxLayout(dlg)
        banner=QLabel(
            "Bu ekran yalnız hafızalı plan oluşturur, PDF'yi bastırmaz. "
            "Windows kuyruğuna gönderdikten sonra işi eşleştireceksin."
        )
        banner.setWordWrap(True)
        layout.addWidget(banner)
        form=QFormLayout()
        printer=QComboBox()
        for name in sorted({p["name"] for p in self._printers}):
            printer.addItem(name,name)
        selected=str(self.printer_filter.currentData() or "")
        if selected:
            printer.setCurrentIndex(max(0,printer.findData(selected)))
        book=QLineEdit()
        book.setPlaceholderText("Kitap veya belge adı")
        code=QLineEdit()
        code.setPlaceholderText("İsteğe bağlı kitap kodu")
        mode=QComboBox()
        mode.addItem("Siyah-beyaz","SB")
        mode.addItem("Renkli","RENK")
        copies=QSpinBox()
        copies.setRange(1,100)
        first=QSpinBox();first.setRange(1,100000)
        last=QSpinBox();last.setRange(0,100000)
        last.setSpecialValueText("Tüm sayfalar")
        pdf=QLineEdit()
        pdf.setReadOnly(True)
        pick=QPushButton("PDF seç (isteğe bağlı)")
        def choose():
            path,_=QFileDialog.getOpenFileName(
                dlg,"Kaynak PDF",str(Path.home()),"PDF dosyaları (*.pdf)")
            if path:
                pdf.setText(path)
                if not book.text().strip():
                    book.setText(Path(path).stem[:160])
        pick.clicked.connect(choose)
        pdf_row=QHBoxLayout()
        pdf_row.addWidget(pdf,1)
        pdf_row.addWidget(pick)
        form.addRow("Hedef yazıcı",printer)
        form.addRow("Kitap adı",book)
        form.addRow("Kitap kodu",code)
        form.addRow("Baskı modu",mode)
        form.addRow("Kopya",copies)
        form.addRow("Başlangıç sayfası",first)
        form.addRow("Son sayfa (0=tümü)",last)
        form.addRow("Kaynak PDF",pdf_row)
        layout.addLayout(form)
        actions=QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        actions.accepted.connect(dlg.accept)
        actions.rejected.connect(dlg.reject)
        layout.addWidget(actions)
        if dlg.exec()!=QDialog.DialogCode.Accepted:
            return
        try:
            task_id=self.repo.create(
                printer=str(printer.currentData()),
                book=book.text(),book_code=code.text(),
                mode=str(mode.currentData()),copies=copies.value(),
                page_start=first.value(),page_end=last.value(),
                pdf_path=pdf.text()
            )
            self._selected_id=task_id
            self.reload()
        except (PrintPlanError,OSError,sqlite3.Error) as exc:
            QMessageBox.warning(self,"Baskı planlanamadı",str(exc)[:260])

    def move(self,direction):
        task=self._selected()
        if not task:return
        try:
            self._selected_id=task["task_id"]
            self.repo.move(task["task_id"],direction)
            self.reload()
        except (PrintPlanError,sqlite3.Error) as exc:
            QMessageBox.warning(self,"Baskı sırası",str(exc)[:220])

    def link_job(self):
        task=self._selected()
        if not task or task["state"]!="planned":return
        linked={t.get("linked_job_key") for t in self._tasks}
        choices=[job for job in self._live_jobs
                 if job["printer"]==task["printer"] and
                 job["key"] not in linked]
        if not choices:
            QMessageBox.information(self,"Windows işi eşleştirme",
                "Bu yazıcının canlı kuyruğunda henüz eşleşmemiş iş bulunamadı. "
                "PDF'yi Windows'tan yazdırmaya gönderdikten sonra yeniden deneyin.")
            return
        lines=[
            f"Windows #{j['native_id']} · {j.get('document','')} "
            f"· {j['pages']}/{j['total'] or '?'} sayfa"
            for j in choices
        ]
        choice,ok=QInputDialog.getItem(
            self,"Gerçek Windows kuyruğu işi",
            "Planlanan kitabı bu Windows işiyle eşleştirin:",lines,0,False)
        if not ok or choice not in lines:return
        index=lines.index(choice)
        job=choices[index]
        confirm=QMessageBox.question(
            self,"Yazdırma işini eşleştir",
            f"PLAN: {task['book']} ({task['mode']})\n"
            f"YAZICI: {task['printer']}\n"
            f"WINDOWS: #{job['native_id']} {job['document']}\n\n"
            "İş adının aynı olması doğru kitap olduğu anlamına gelmez. "
            "Eşleştirmeyi kontrol ettin mi?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )
        if confirm!=QMessageBox.StandardButton.Yes:return
        try:
            self.repo.link_job(task["task_id"],job["key"])
            self._selected_id=task["task_id"]
            self.reload()
        except (PrintPlanError,sqlite3.Error) as exc:
            QMessageBox.warning(self,"Windows eşleştirme",str(exc)[:250])

    def verify_task(self):
        task=self._selected()
        if not task:return
        answer=QMessageBox.question(
            self,"Fiziksel baskı onayı",
            f"{task['book']} · {task['copies']} kopya\n\n"
            "Kâğıtları gözle veya cihazın güvenilir çıktı kaydıyla gerçekten "
            "kontrol ettin mi? Windows sayacı veya kuyruktan kaybolma "
            "tek başına yeterli değildir.",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )
        if answer!=QMessageBox.StandardButton.Yes:return
        note,ok=QInputDialog.getText(
            self,"Fiziksel teyit notu",
            "Örn. 2 kopya, tüm sayfalar gözle kontrol edildi:")
        if not ok or not note.strip():return
        try:
            self.repo.verify(task["task_id"],note)
            self._selected_id=task["task_id"]
            self.reload()
        except (PrintPlanError,sqlite3.Error) as exc:
            QMessageBox.warning(self,"Baskı teyidi",str(exc)[:220])

    def resume_task(self):
        task=self._selected()
        if not task or task["state"]!="verify":return
        reported=int(task.get("last_reported_pages") or 0)
        observed=(f"{reported} sayfa" if task.get("last_reported_at")
                  else "Bilinmiyor")
        estimated=""
        if task.get("last_reported_at") and reported>0 and int(task["copies"])==1:
            # Illustrative mapping ONLY, and explicitly not treated as
            # physical truth for duplex, N-up or other driver settings.
            possible=int(task["page_start"])+reported-1
            end=int(task["page_end"] or 0)
            if not end or possible<=end:
                estimated=(f"\nYalnız bire-bir sıralı baskı varsayımıyla "
                           f"olası PDF sayfası: {possible} (KESİN DEĞİL).")
        details=(
            f"Kitap: {task['book']}\nYazıcı: {task['printer']}\n"
            f"Baskı türü: {task['mode']} · Kopya: {task['copies']}\n"
            f"Windows'un en son sayacı: {observed}.{estimated}\n\n"
            "Windows sayacı gerçek kâğıt çıktısını kanıtlamaz.\n"
            "Yazıcının arabelleğinde hâlâ devam eden iş olmadığını kontrol et.\n"
            "Çıkan kâğıtları inceleyip SON TAM VE SAĞLAM PDF SAYFASINI "
            "kendin teyit et. O sayfadan sonraki sayfa için ayrı bir "
            "baskı planı oluşacak; otomatik yazdırma YAPILMAYACAK."
        )
        choice=QMessageBox.question(
            self,"Kesilen baskıya devam · Son sayfa kontrolü",
            details,
            QMessageBox.StandardButton.Yes|
            QMessageBox.StandardButton.No)
        if choice!=QMessageBox.StandardButton.Yes:return
        first=int(task["page_start"])
        upper=int(task["page_end"] or 0)
        maximum=upper if upper else 100000
        confirmed,ok=QInputDialog.getInt(
            self,"Son sağlam basılan PDF sayfası",
            f"Son tamamlanmış PDF sayfası ({first-1}=hiç çıkmadı):",
            first-1,first-1,maximum,1)
        if not ok:return
        next_page=confirmed+1
        confirm=QMessageBox.question(
            self,"Devam sayfasını onayla",
            f"Son sağlam PDF sayfası: {confirmed}\n"
            f"YENİ BASKI BAŞLANGICI: PDF SAYFA {next_page}\n"
            f"Mevcut yazıcı: {task['printer']}\n"
            f"Kopya: {task['copies']}\n\n"
            "Kâğıtları ve PDF sayfa numaralarını doğruladın mı? "
            "Çift baskı olmaması için yazıcının eski işi "
            "sürdürmediğinden emin ol.",
            QMessageBox.StandardButton.Yes|
            QMessageBox.StandardButton.No)
        if confirm!=QMessageBox.StandardButton.Yes:return
        note,ok=QInputDialog.getText(
            self,"Baskıya devam · Kontrol notu",
            "Hangi sayfaları kontrol ettin? Kesilme nedeni/tespit:")
        if not ok or not note.strip():return
        try:
            created=self.repo.create_resume(task["task_id"],confirmed,note)
            self._selected_id=created["task_id"]
            self.reload()
            QMessageBox.information(
                self,"Yeni devam planı kaydedildi",
                f"{task['book']}\n"
                f"Başlangıç PDF sayfası: {created['resume_from']}\n"
                f"Yazıcı: {task['printer']}\n\n"
                "Bu bir plan kaydıdır; PDF otomatik gönderilmedi. "
                "Kaynak PDF'yi belirtilen sayfadan yazdırıp "
                "Windows kuyruğundaki yeni iş ile eşleştir.")
        except (PrintPlanError,sqlite3.Error,ValueError) as exc:
            QMessageBox.warning(self,"Devam planı oluşturulamadı",str(exc)[:260])

    def cancel_task(self):
        task=self._selected()
        if not task:return
        reason,ok=QInputDialog.getText(
            self,"Planı iptal et",
            "Bu yalnızca yerel planı iptal eder; Windows yazıcı işini "
            "iptal etmez. İptal nedeni:")
        if not ok or not reason.strip():return
        try:
            self.repo.cancel_plan(task["task_id"],reason)
            self._selected_id=task["task_id"]
            self.reload()
        except (PrintPlanError,sqlite3.Error) as exc:
            QMessageBox.warning(self,"Plan iptali",str(exc)[:220])

    def inspect_task(self):
        task=self._selected()
        if not task:return
        try:
            events=self.repo.task_events(task["task_id"],40)
        except (PrintPlanError,sqlite3.Error) as exc:
            QMessageBox.warning(self,"Baskı geçmişi",str(exc)[:220])
            return
        lines=[
            f"Kitap: {task['book']}",
            f"Kitap kodu: {task['book_code'] or '—'}",
            f"Yazıcı: {task['printer']}",
            f"PDF: {task['pdf_path'] or 'Seçilmedi'}",
            f"Mod: {task['mode']} · Kopya: {task['copies']}",
            "Durum: "+STATE_NAMES.get(task["state"],task["state"]),
            "Windows iş anahtarı: "+str(task["linked_job_key"] or "Henüz yok"),
            "Son Windows sayacı: "+
                (str(task.get("last_reported_pages") or 0)+" sayfa (fiziksel teyit DEĞİL)"
                 if task.get("last_reported_at") else "Bilinmiyor"),
            "Windows sayaç zamanı: "+str(task.get("last_reported_at") or "—"),
            "Kontrol edilmiş son PDF sayfası: "+
                (str(task["confirmed_last_page"]) if
                 task.get("confirmed_last_page") is not None else "Henüz yok"),
            "Devam edilen iş: "+str(task.get("parent_task_id") or "—"),
            "Son not: "+str(task["note"] or "—"),
            "\nOlaylar:",
        ]
        lines.extend(
            f"{event['at']} · {event['kind']} · {event['detail']}"
            for event in events
        )
        QMessageBox.information(
            self,"Yerel baskı kaydı","\n".join(lines)[:3600])
