"""Modal order update review and transient cover preview."""
import copy
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QVBoxLayout,
    QHBoxLayout, QLabel, QCheckBox, QPushButton, QScrollArea, QWidget)
from widgets import cover_label
from siparis_uyari import revision, initial_note_notice

def plain(value, parent=None):
    w = QLabel(str(value), parent)
    w.setTextFormat(Qt.TextFormat.PlainText)
    w.setWordWrap(True)
    return w

class ChangedBook(QLabel):
    def __init__(self, label, code, name, db, covers, parent=None):
        super().__init__(label, parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.code, self.name, self.db, self.covers = code, name, db, covers
        self._preview = None

    def enterEvent(self, event):
        super().enterEvent(event)
        self._hide_preview()
        book = self.db.katalog.get(self.code) or getattr(self.db,"archived_catalog",{}).get(self.code) or {"kod":self.code,"isim":self.name,"sayfa":0}
        popup = QFrame(self, Qt.WindowType.ToolTip)
        popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        popup.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        popup.setStyleSheet("QFrame {background:#182b40;border:1px solid #eab85a;border-radius:8px;} QLabel {color:#f5f7fb;border:0;background:transparent;}")
        lay = QVBoxLayout(popup)
        lay.addWidget(cover_label(book, self.covers, 155, 216), 0, Qt.AlignmentFlag.AlignHCenter)
        title = plain("#"+self.code+" · "+str(book.get("isim") or self.name))
        title.setFixedWidth(190)
        lay.addWidget(title)
        popup.adjustSize()
        pos = QCursor.pos()+QPoint(16,19)
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        if screen:
            bounds = screen.availableGeometry()
            pos.setX(max(bounds.left(),min(pos.x(),bounds.right()-popup.width())))
            pos.setY(max(bounds.top(),min(pos.y(),bounds.bottom()-popup.height())))
        popup.move(pos)
        self._preview = popup
        popup.show()

    def _hide_preview(self):
        if self._preview is not None:
            self._preview.hide()
            self._preview.deleteLater()
            self._preview = None

    def leaveEvent(self,event):
        self._hide_preview()
        super().leaveEvent(event)

    def hideEvent(self,event):
        self._hide_preview()
        super().hideEvent(event)

class OrderNoticeDialog(QDialog):
    def __init__(self, db, covers, order, parent=None, open_detail=False):
        super().__init__(parent)
        self.db, self.order = db, order
        self.expected = revision(order)
        self.rendered_changes = copy.deepcopy((order.get("order_notice") or {}).get("changes") or {})
        initial = initial_note_notice(order)
        self.setWindowTitle("ALFA ERP · Sipariş notu" if initial else "ALFA ERP · Sipariş güncellemesi")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(510, 330) if initial else self.resize(650, 550)
        self.setMinimumSize(420, 290)
        root = QVBoxLayout(self)
        root.setContentsMargins(18,18,18,18)
        root.setSpacing(10)
        heading = plain("⚠  SİPARİŞ #"+str(order.get("bulut_siparis_no") or order["id"])+
                        (" · SİPARİŞ NOTU" if initial else " · GÜNCELLEME VAR"))
        heading.setStyleSheet("font-size:17px;font-weight:900;color:#ad6b00;background:#ffefcb;padding:12px;border-radius:8px;")
        root.addWidget(heading)
        root.addWidget(plain("Siparişe eklenen notu okuyup onaylayın." if initial else
                            "Aşağıdaki değişiklikleri kontrol edin. Kitap kodlarının üzerine gelerek kapaklarını görebilirsiniz."))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setSpacing(9)
        changes = (order.get("order_notice") or {}).get("changes") or {}
        for key in ([] if initial else sorted(changes)):
            item = changes[key]
            if not isinstance(item,dict):
                continue
            if item.get("type") == "book":
                before, after = int(item.get("old") or 0), int(item.get("new") or 0)
                code, kind = str(item.get("code") or ""), str(item.get("kind") or "")
                action = "Eklendi" if not before else ("Çıkarıldı" if not after else "Adet değişti")
                line = ChangedBook(f"{action}  ·  #{code}  ·  {kind}  ·  {before} → {after} adet",
                                   code,str(item.get("name") or code),db,covers)
                line.setStyleSheet("font-weight:850;font-size:13px;padding:9px;border-radius:6px;background:"+
                                  ("#fde0dd;color:#a52b2b;" if after<before else "#d9f5e8;color:#126d45;"))
                lay.addWidget(line)
            else:
                lay.addWidget(plain(str(item.get("label") or "Değişiklik")))
                old = plain("Önce: "+str(item.get("old") or "—"))
                old.setStyleSheet("font-size:12px;color:#a52b2b;background:#fde0dd;padding:7px;border-radius:5px;")
                lay.addWidget(old)
                new = plain("Yeni: "+str(item.get("new") or "—"))
                new.setStyleSheet("font-weight:800;font-size:14px;color:#126d45;background:#d9f5e8;padding:9px;border-radius:5px;")
                lay.addWidget(new)
        if order.get("order_note") and (initial or not any(
                isinstance(item,dict) and item.get("label") in ("Sipariş notu","Yeni sipariş notu")
                for item in changes.values())):
            note = plain(str(order["order_note"]) if initial else "Güncel sipariş notu: "+str(order["order_note"]))
            note.setStyleSheet("font-weight:750;color:#794a00;background:#fff1cc;padding:9px;border-radius:6px;")
            lay.addWidget(note)
        lay.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        self.checked = QCheckBox("Okudum, anladım.")
        root.addWidget(self.checked)
        self.status = plain("")
        root.addWidget(self.status)
        row = QHBoxLayout()
        self.back = QPushButton("Vazgeç")
        self.back.clicked.connect(self.reject)
        self.ok = QPushButton("Onayla ve siparişi aç" if open_detail else "Onayla ve kapat")
        self.ok.setEnabled(False)
        self.ok.setStyleSheet("QPushButton {font-weight:800;padding:9px;background:#b45f05;color:white;} QPushButton:disabled {background:#888;color:#eee;}")
        self.checked.toggled.connect(self.ok.setEnabled)
        self.ok.clicked.connect(self._confirm)
        row.addWidget(self.back); row.addStretch(); row.addWidget(self.ok)
        root.addLayout(row)

    def _confirm(self):
        if not self.checked.isChecked():
            return
        try:
            if (revision(self.order)!=self.expected or self.order not in self.db.siparisler or
                self.rendered_changes != (self.order.get("order_notice") or {}).get("changes")):
                raise ValueError("Sipariş değişti. Pencereyi kapatıp yeni uyarıyı açın.")
            self.db.queue_notice_ack(self.order,self.expected)
        except Exception as exc:
            self.status.setText(str(exc))
            return
        # No dialog-owned thread, nested network operation or callback after
        # accept. The regular Sync worker sends the durable receipt later.
        self.accept()
