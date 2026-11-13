"""Owner-only error inbox presentation; all rows come from a bounded SSE feed."""
from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,
    QTableWidgetItem,QHeaderView,QAbstractItemView,QDialog,QTextEdit,
    QMessageBox
)


def local_time(value):
    try:
        return datetime.fromisoformat(
            str(value).replace("Z","+00:00")).astimezone().strftime(
                "%d.%m.%Y %H:%M:%S")
    except (ValueError,TypeError,OverflowError):
        return str(value or "—")[:32]


class ErrorInbox(QWidget):
    refresh_requested=Signal()
    review_requested=Signal(str)
    remove_requested=Signal(str)
    purge_reviewed_requested=Signal(list)

    def __init__(self,parent=None):
        super().__init__(parent)
        root=QVBoxLayout(self)
        root.setContentsMargins(10,10,10,10)
        title=QLabel("HATA MERKEZİ · CİHAZ RAPORLARI")
        title.setObjectName("OwnerHeading")
        root.addWidget(title)
        hint=QLabel(
            "Personel/Yönetici cihazlarında beklenmedik hata olduğunda rapor "
            "bir kez gönderilir. Bu ekran Firebase olay akışını dinler; "
            "sürekli sorgulama yapmaz. Raporlarda müşteri/sipariş içeriği yoktur.")
        hint.setObjectName("OwnerMuted")
        hint.setWordWrap(True);root.addWidget(hint)
        actions=QHBoxLayout()
        self.summary=QLabel("Hata kayıtları henüz yüklenmedi.")
        self.summary.setObjectName("OwnerBody")
        actions.addWidget(self.summary,1)
        refresh=QPushButton("↻ Elle yenile")
        refresh.setObjectName("OwnerPrimary")
        refresh.clicked.connect(self.refresh_requested.emit)
        actions.addWidget(refresh)
        root.addLayout(actions)
        self.table=QTableWidget(0,6)
        self.table.setObjectName("OwnerErrorTable")
        self.table.setHorizontalHeaderLabels(
            ["Zaman","Bilgisayar","Sürüm","Hata türü","Durum","Kaynak"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(36)
        head=self.table.horizontalHeader()
        head.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(lambda _index:self.open_details())
        root.addWidget(self.table,1)
        bottom=QHBoxLayout()
        detail=QPushButton("Seçili raporun ayrıntıları")
        detail.setObjectName("OwnerPrimary")
        detail.clicked.connect(self.open_details)
        review=QPushButton("Seçili rapor · İncelendi")
        review.setObjectName("OwnerPrimary")
        review.clicked.connect(self.mark_reviewed)
        remove=QPushButton("Seçili raporu sil")
        remove.setObjectName("OwnerDanger")
        remove.clicked.connect(self.delete_selected)
        purge=QPushButton("İncelenenleri temizle")
        purge.setObjectName("OwnerDanger")
        purge.clicked.connect(self.purge_reviewed)
        bottom.addWidget(detail);bottom.addWidget(review)
        bottom.addWidget(remove);bottom.addWidget(purge);bottom.addStretch()
        root.addLayout(bottom)
        self._by_id={}
        self._acks={}

    def set_entries(self,reports,acks):
        self._by_id={
            str(key):dict(value) for key,value in (reports or {}).items()
            if isinstance(value,dict) and len(str(key))<=90}
        self._acks=acks if isinstance(acks,dict) else {}
        rows=sorted(self._by_id.items(),key=lambda v:v[0],reverse=True)
        self.table.setRowCount(len(rows))
        unseen=0
        for row,(report_id,entry) in enumerate(rows):
            reviewed=report_id in self._acks
            if not reviewed:unseen+=1
            values=[
                local_time(entry.get("created_at")),
                str(entry.get("device_name") or "?")[:80],
                str(entry.get("version") or "?")[:24],
                str(entry.get("type") or "?")[:80],
                "İncelendi" if reviewed else "Yeni",
                "Personel" if entry.get("edition")=="staff" else "Yönetici",
            ]
            for col,value in enumerate(values):
                cell=QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole,report_id)
                if not reviewed and col==4:
                    from PySide6.QtGui import QColor
                    cell.setForeground(QColor("#ffbc62"))
                self.table.setItem(row,col,cell)
        self.summary.setText(
            f"{len(rows)} son hata kaydı · {unseen} incelenmemiş"
            " · canlı bildirim açıkken otomatik yenilenir")
        return unseen

    def _selected(self):
        row=self.table.currentRow()
        if row<0:return None,None
        cell=self.table.item(row,0)
        if cell is None:return None,None
        report_id=str(cell.data(Qt.ItemDataRole.UserRole) or "")
        return report_id,self._by_id.get(report_id)

    def open_details(self):
        report_id,entry=self._selected()
        if entry is None:
            QMessageBox.information(self,"Hata Merkezi","Önce rapor seç.")
            return
        dialog=QDialog(self)
        dialog.setWindowTitle("ALFA hata raporu · "+report_id[:25])
        dialog.resize(650,500)
        col=QVBoxLayout(dialog)
        title=QLabel(str(entry.get("type") or "Beklenmedik hata"))
        title.setObjectName("OwnerHeading")
        col.addWidget(title)
        meta=QLabel(
            "Bilgisayar: "+str(entry.get("device_name") or "?")+
            "\nZaman: "+local_time(entry.get("created_at"))+
            "\nSürüm: "+str(entry.get("version") or "?")+
            "\nKaynak: "+str(entry.get("source") or "?")+
            "\nParmak izi: "+str(entry.get("fingerprint") or "?"))
        meta.setWordWrap(True);col.addWidget(meta)
        frames=entry.get("frames") or []
        details=QTextEdit()
        details.setReadOnly(True)
        details.setPlainText(
            "\n".join(f"{x.get('file','?')}:{x.get('line','?')} "
                      f"→ {x.get('function','?')}"
                      for x in frames if isinstance(x,dict))
            or "Yerel/native hata: Python yığın bilgisi bulunmuyor.")
        col.addWidget(details,1)
        close=QPushButton("Kapat")
        close.clicked.connect(dialog.accept)
        col.addWidget(close)
        dialog.exec()

    def mark_reviewed(self):
        report_id,entry=self._selected()
        if entry is None:
            QMessageBox.information(self,"Hata Merkezi","Önce rapor seç.")
            return
        if report_id in self._acks:return
        self.review_requested.emit(report_id)

    def delete_selected(self):
        report_id,entry=self._selected()
        if entry is None:
            QMessageBox.information(self,"Hata Merkezi","Önce hata kaydı seç.")
            return
        if QMessageBox.question(
            self,"Hata raporunu kalıcı sil",
            "Seçili hata raporu Firebase'den kalıcı olarak silinsin mi?\n"+
            str(entry.get("type") or "Hata")[:70],
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
        )==QMessageBox.StandardButton.Yes:
            self.remove_requested.emit(report_id)

    def purge_reviewed(self):
        ids=[key for key in self._by_id if key in self._acks]
        if not ids:
            QMessageBox.information(self,"Hata Merkezi",
                                    "Görünen kayıtlar içinde incelenmiş hata yok.")
            return
        if QMessageBox.question(
            self,"İncelenen hataları temizle",
            str(len(ids))+" incelenmiş hata raporu ve onay kaydı "
            "Firebase'den silinsin mi? İncelenmemiş raporlara dokunulmaz.",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
        )==QMessageBox.StandardButton.Yes:
            self.purge_reviewed_requested.emit(ids)
