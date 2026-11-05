"""In-app release announcements and safe manual staff error reporting.

Local changelog costs zero Firebase reads. Latest stable release notes are
shown only when the existing daily GitHub check has already returned them.
"""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QTextEdit,
    QPushButton,QComboBox,QMessageBox
)
from alfa_hatalar import report_manual_error
from guncelleme_arayuzu import UpdateDialog

V110_NOTES = """# ALFA ERP v1.1.0 · İlk resmî güncelleme

**Envanter ve katalog**
- Yönetici, eski satışları neden belirterek iptal edebilir. Satış kaydı silinmez;
  orijinal alım partisine stok geri verilir. İptaller net cirodan çıkarılır.
- Ürünler silinmeden arşivlenebilir ve geri getirilebilir.
- Satış formu parti, adet ve fiyat alanlarıyla pillbox kartlarına ayrıldı.

**Siparişler ve güvenilirlik**
- Yoğun eşzamanlı düzenlemede geçici ETag yarışları artık kalıcı iş hatası
  yerine korunmuş sırada tekrar denenir.
- Sipariş havuzundan silinen bir kaydın eski bulut yanıtında geçici görünmesi
  engellendi.

**Arayüz, temalar, duyurular**
- Üst panelde Yönetici/Personel adı ve sürümü.
- Personelde ayrı Ayarlar düğmesi yerine açık/koyu tema geçişi.
- Personel için kategorili Hata Bildir ekranı.
- Günlük arka plan sürüm kontrolü ve yeni sürüm bulunduğunda bildirim.
- Siparişlere Genel Bakış, Cihaz Yetkisi ve Sipariş Geldi pencerelerinde
  açık tema kontrast düzeltmeleri.
- GitHub sürüm notları ve uygulama içi Duyuru Merkezi.

**Veri güvenliği:** Sipariş, satış, alım partisi ve hata kayıtları
otomatik olarak silinmez. Geçmişte reddedilen işlemler için İşlem Günlüğü
arşivi korunur.
"""


def _skin(dialog):
    theme=str(QApplication.instance().property('alfa_theme') or 'koyu')
    if theme=='acik':
        bg,panel,fg,secondary,border,accent=('#f6f1e8','#fffaf3','#243a51',
                                            '#536980','#c7b69f','#d4e6f1')
    elif theme=='kontrast':
        bg,panel,fg,secondary,border,accent=('#060b11','#15283d','#ffffff',
                                            '#e6f5ff','#91adcb','#294d72')
    else:
        bg,panel,fg,secondary,border,accent=('#102033','#1b3045','#f5f9ff',
                                            '#bdcfe0','#557592','#254a69')
    dialog.setStyleSheet(f"""
        QDialog {{background:{bg};color:{fg};}}
        QLabel {{color:{fg};background:transparent;}}
        QTextEdit {{color:{fg};background:{panel};border:1px solid {border};
            border-radius:9px;padding:11px;}}
        QComboBox {{background:{panel};color:{fg};border:1px solid {border};
            padding:8px;}}
        QPushButton {{background:{accent};color:{fg};border:1px solid {border};
            border-radius:8px;padding:9px 15px;font-weight:750;}}
        QPushButton:hover {{border:2px solid {border};}}
    """)


class AnnouncementsDialog(QDialog):
    def __init__(self,version,edition,storage,release=None,parent=None):
        super().__init__(parent)
        self.setWindowTitle("ALFA ERP · Duyuru ve Güncelleme Merkezi")
        self.setObjectName("AlfaAnnouncementsDialog")
        self.resize(680,560)
        self.version=str(version)
        self.edition=str(edition)
        self.storage=Path(storage)
        self.release=release
        _skin(self)
        root=QVBoxLayout(self)
        heading=QLabel(f"DUYURULAR  ·  ALFA ERP v{self.version}")
        heading.setStyleSheet('font-size:18px;font-weight:900;')
        root.addWidget(heading)
        if release and release.get('available'):
            notice=QLabel("● Yeni kararlı sürüm bulundu: v"+
                          str(release.get('version','')))
        else:
            notice=QLabel("Güncel sürüm notları · yalnızca onaylı GitHub sürümleri")
        notice.setWordWrap(True)
        root.addWidget(notice)
        self.notes=QTextEdit(self)
        self.notes.setReadOnly(True)
        if release and release.get('available') and release.get('notes'):
            self.notes.setPlainText(
                'YAYIMLANAN YENİ SÜRÜM NOTLARI\n\n'+
                str(release.get('notes') or '')[:3200]+
                '\n\n────────────────────\n\n'+V110_NOTES)
        else:
            self.notes.setMarkdown(V110_NOTES)
        root.addWidget(self.notes,1)
        row=QHBoxLayout()
        updates=QPushButton("↻ Güncelleme Merkezi")
        updates.clicked.connect(self.open_update_center)
        row.addWidget(updates)
        row.addStretch()
        close=QPushButton("Kapat")
        close.clicked.connect(self.close)
        row.addWidget(close)
        root.addLayout(row)

    def open_update_center(self):
        self.update_dialog=UpdateDialog(self.version,self.edition,
                                        self.storage,self)
        self.update_dialog.check_now()
        self.update_dialog.exec()


class ManualReportDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("ALFA ERP · Hata Bildir")
        self.resize(430,280)
        _skin(self)
        root=QVBoxLayout(self)
        heading=QLabel("PERSONEL HATA BİLDİRİMİ")
        heading.setStyleSheet('font-size:17px;font-weight:850;')
        root.addWidget(heading)
        note=QLabel("Sorun türünü seçip gönder. Müşteri bilgileri, sipariş içeriği,"
                    " parolalar ve serbest metin yüklenmez. Rapor buluta"
                    " erişilemiyorsa yerel güvenli kuyrukta saklanır.")
        note.setWordWrap(True);root.addWidget(note)
        self.category=QComboBox()
        for key,name in (
            ('orders','Sipariş / Havuz'),
            ('inventory','Envanter / Satış'),
            ('sync','Bulut / Eşitleme'),
            ('theme','Arayüz / Açık tema'),
            ('other','Diğer teknik sorun'),
        ):
            self.category.addItem(name,key)
        root.addWidget(self.category)
        row=QHBoxLayout()
        send=QPushButton("Hata raporunu gönder")
        send.clicked.connect(self.submit)
        row.addWidget(send)
        cancel=QPushButton("Vazgeç");cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        root.addLayout(row)

    def submit(self):
        if report_manual_error(str(self.category.currentData())):
            QMessageBox.information(self,'Hata bildirimi',
                'Rapor yerel kuyruğa güvenle kaydedildi. Bağlantı varsa'
                ' Yönetici Hata Merkezi’ne iletilir.')
            self.accept()
        else:
            QMessageBox.warning(self,'Hata bildirimi',
                'Rapor kaydedilemedi veya aynı tür kısa süre önce bildirildi.')
