"""Owner-only error inbox presentation; all rows come from a bounded SSE feed."""
from __future__ import annotations

from datetime import datetime
import re
from PySide6.QtCore import Qt, Signal, QItemSelectionModel
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,
    QTableWidgetItem,QHeaderView,QAbstractItemView,QDialog,QTextEdit,
    QMessageBox,QLineEdit,QComboBox
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
    review_requested=Signal(list)
    remove_requested=Signal(list)
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
        self.search=QLineEdit()
        self.search.setPlaceholderText("Hata kodu, bilgisayar veya kaynak…")
        self.search.textChanged.connect(self._render)
        actions.addWidget(self.search,1)
        self.filter=QComboBox()
        self.filter.addItems(["Tümü","İncelenmemiş","İncelenen"])
        self.filter.currentIndexChanged.connect(self._render)
        actions.addWidget(self.filter)
        refresh=QPushButton("↻ Elle yenile")
        refresh.setObjectName("OwnerPrimary")
        refresh.clicked.connect(self.refresh_requested.emit)
        actions.addWidget(refresh)
        select=QPushButton('Tümünü seç');select.clicked.connect(self.table_select_all)
        actions.addWidget(select)
        root.addLayout(actions)
        self.table=QTableWidget(0,7)
        self.table.setObjectName("OwnerErrorTable")
        self.table.setHorizontalHeaderLabels(
            ["Zaman","Bilgisayar","Sürüm","Hata türü","Kod","Durum","Kaynak"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
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
        detail=QPushButton("Rapor ayrıntısı")
        detail.setObjectName("OwnerPrimary")
        detail.clicked.connect(self.open_details)
        review=QPushButton("Seçilenleri incele")
        review.setObjectName("OwnerPrimary")
        review.clicked.connect(self.mark_reviewed)
        remove=QPushButton("Seçilenleri sil")
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
        self._render()
        return sum(key not in self._acks for key in self._by_id)

    def _render(self,*_):
        if not hasattr(self,"_by_id"):
            return
        selected=set(self._selected_ids())
        needle=self.search.text().strip().casefold()
        mode=self.filter.currentIndex()
        rows=[]
        for key,entry in sorted(self._by_id.items(),key=lambda v:v[0],reverse=True):
            reviewed=key in self._acks
            if (mode==1 and reviewed) or (mode==2 and not reviewed):
                continue
            haystack=" ".join(str(entry.get(k) or "") for k in
                             ("type","device_name","source","version","fingerprint","created_at")).casefold()
            if needle and needle not in haystack:
                continue
            rows.append((key,entry))
        self.table.clearSelection()
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
                (re.search(r"(\d{3})$",str(entry.get("type") or "")).group(1)
                 if re.search(r"(\d{3})$",str(entry.get("type") or "")) else "—"),
                "İncelendi" if reviewed else "Yeni",
                ("Personel" if entry.get("edition")=="staff" else "Yönetici")+
                " · "+str(entry.get("source") or "—")[:30],
            ]
            for col,value in enumerate(values):
                cell=QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole,report_id)
                if not reviewed and col==5:
                    from PySide6.QtGui import QColor
                    cell.setForeground(QColor("#ffbc62"))
                self.table.setItem(row,col,cell)
            if report_id in selected:
                self.table.selectionModel().select(self.table.model().index(row,0),
                    QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
        self.summary.setText(
            f"{len(rows)}/{len(self._by_id)} rapor · {unseen} incelenmemiş")

    def table_select_all(self):
        self.table.selectAll()

    def _selected_ids(self):
        return [str(self.table.item(i.row(),0).data(Qt.ItemDataRole.UserRole))
                for i in self.table.selectionModel().selectedRows()
                if self.table.item(i.row(),0) is not None]

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
        kind=str(entry.get("type") or "")
        code=re.search(r"(\d{3})$",kind)
        descriptions={
            "409":("İşlem çakışması","Sunucu siparişi ya da sürümünü değiştirmiş olabilir. "
                   "Reddedilen işlem yerel çakışma arşivinde tutulur. "
                   "Güncel siparişi kontrol etmeden tekrar uygulamayın."),
            "403":("Erişim reddedildi","Yetkili owner rolünü ve yayımlanmış Firebase kurallarını kontrol edin."),
            "401":("Oturum doğrulanamadı","Cihaz oturumunu ve Firebase bağlantısını kontrol edin."),
            "422":("İş kuralı doğrulaması","İşlem mevcut sipariş durumuna veya veri kuralına uygun olmayabilir."),
            "429":("İstek sınırı","Geçici yoğunluk; uygulamanın yeniden denemesine izin verin."),
            "503":("Geçici hizmet hatası","İşlemi zorla tekrar göndermeyin; bağlantı ve kuyruk durumunu kontrol edin."),
        }
        number=code.group(1) if code else ""
        stages={'commit':'Sipariş kayıt/düzenleme','status':'Sipariş durum geçişi',
                'progress':'Hazırlama / kolileme','notice_ack':'Sipariş notu onayı',
                'shipping_fee':'Kargo ücreti','return_state':'İade işlemi'}
        stage=next((label for key,label in stages.items()
                    if "RejectedWrite_"+key+"Error" in kind),"Bu raporda belirtilmemiş")
        heading,help_text=descriptions.get(number,("Teknik olay",
            "Kesin neden için olay kaynağı ve varsa Python yığınını inceleyin."))
        trace="\n".join(f"{x.get('file','?')}:{x.get('line','?')} → {x.get('function','?')}"
                        for x in frames if isinstance(x,dict))
        details.setPlainText(
            "OLAY SINIFI: "+heading+"\n"
            +"HTTP KODU: "+(number or "Kayıtlı değil")+"\n"
            +"İŞLEM AŞAMASI: "+stage+"\n"
            +"OLASI NEDEN / KONTROL: "+help_text+"\n\n"
            +"TEKNİK YIĞIN\n"+(trace or "Bu olay için Python yığını kaydedilmemiş.")+
            "\n\nNot: Raporlar gizlilik nedeniyle müşteri verisi ve ham hata metni içermez.")
        col.addWidget(details,1)
        close=QPushButton("Kapat")
        close.clicked.connect(dialog.accept)
        col.addWidget(close)
        dialog.exec()

    def mark_reviewed(self):
        ids=[key for key in self._selected_ids() if key not in self._acks]
        if not ids:
            QMessageBox.information(self,"Hata Merkezi","İncelenmemiş rapor seç.")
            return
        self.review_requested.emit(ids)

    def delete_selected(self):
        ids=self._selected_ids()
        if not ids:
            QMessageBox.information(self,"Hata Merkezi","Önce hata kaydı seç.")
            return
        if QMessageBox.question(
            self,"Hata raporlarını kalıcı sil",
            str(len(ids))+" seçili hata raporu Firebase'den kalıcı olarak silinsin mi?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
        )==QMessageBox.StandardButton.Yes:
            self.remove_requested.emit(ids)

    def purge_reviewed(self):
        # Only reviewed reports in the current filtered list.
        ids=[str(self.table.item(row,0).data(Qt.ItemDataRole.UserRole))
             for row in range(self.table.rowCount())
             if self.table.item(row,0) is not None
             and str(self.table.item(row,0).data(Qt.ItemDataRole.UserRole)) in self._acks]
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
