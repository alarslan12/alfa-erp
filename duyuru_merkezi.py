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

V201_NOTES = """# ALFACOPYCENTER v2.0.1 · Sipariş eşitleme düzeltmesi

- Personel ve Yönetici uygulamaları doğrudan **Firebase sipariş değişikliklerini**
  dinler; ayrı revizyon sayacı güncellenmese de sipariş yenilenir.
- Çok hızlı Hazırlandı / Kolilendi tıklamaları tekleştirilir, eşzamanlı
  cihazların zaten işlediği miktarlar tekrar eklenmez.
- İşlem yapılan siparişin hedef sayısına önceden ulaşılmışsa bulut işlemi
  güvenle doğrulanır ve aynı olay bir daha tekrar uygulanmaz.
- İnternet isteği devam ederken gelen yeni sipariş bildirimi kaybolmaz;
  ilk istek tamamlanınca yeni bulut kontrolü kuyruğa alınır.
- Sağ üstte geçmiş çakışma mesajı artık kalıcı değildir. **Yeni hata**
  kısa süre (8 saniye) görünür; sonra gerçek Bulut bağlı / çevrimdışı
  durumu gösterilir. Raporlar İşlem Günlüğü ve Hata Merkezi'nde saklanır.
- Yanına **↻** anlık bulut siparişlerini kontrol düğmesi eklendi.
  Bekleyen işlem kuyruğuna veya eski sipariş arşivine müdahale etmez.

**Veri güvenliği:** Mevcut siparişler, kuyruklar, eski hata kayıtları,
personel/yönetici yetkileri ve tasarım arşivi silinmez.
"""


V200_NOTES = """# ALFACOPYCENTER v2.0.0 · Dört Uygulama Paketi

- Tek Windows kurulumu: Yönetici ERP, Personel ERP,
  Banner Studio Pro v3.3 ve Yazdırma Kontrol Merkezi v2.0.
- Her uygulamanın ayrı ALFACOPYCENTER logosu ve masaüstü kısayolu.
- Banner Studio: yerel tasarım arşivi, Excel/ZIP kitap kapağı içe aktarma,
  tek/set fiyatı, 1–30 kapak şablonu ve HD dışa aktarma.
- Yazdırma Kontrol Merkezi: Windows WinSpool kuyruk takibi,
  yerel SQLite geçmişi, kitap/PDF baskı planı, duraksama uyarıları,
  son Windows sayacı ve manuel teyit edilmiş PDF devam sayfası.
- Yerel IPP ve Epson/Canon SNMP/Windows sürücü tanıma modülleri;
  cihazdan alınan sayaç fiziksel son PDF sayfası olarak sunulmaz.
- İsteğe bağlı oturum açılışında arka plan izleme ajanı.
  Sadece mevcut Windows kullanıcısının yazıcı izinleriyle çalışır.
  Windows hizmeti, spooler silme veya yönetici ayrıcalığı istemez.
- Yönetici kurulumu parola ve Firebase owner rolü gerektirir;
  sipariş/veri/arşiv kayıtları silinmez.

**Sınırlar:** PC kapalıyken, Windows oturumu kapalıyken veya yazıcı
durum verisi sunmuyorken eksiksiz fiziksel baskı izleme garanti
edilemez. Bu sürüm otomatik yeniden yazdırma yapmaz.
"""


V111_NOTES = """# ALFA ERP v1.1.1 · Güncelleme Merkezi düzeltmesi

- Güncelleme başlatıldığında modal pencere kapatılır ve gerçek ERP
  ana penceresi güvenli biçimde sonlandırılır.
- Duyurular ekranından güncelleme yapılırken de bekleyen bulut sipariş
  kuyruğu ve devam eden eşitleme işlemleri kontrol edilir.
- Windows kurulum yardımcısı kurulum sihirbazını açık şekilde başlatır;
  başarılı kurulumdan sonra ilgili Personel/Yönetici EXE'sini yeniden açar.
- Kurulum başarısız olursa neden yerel güncelleme kaydına yazılır ve
  bir sonraki Güncelleme Merkezi açılışında gösterilir.
- Şifre korumalı Yönetici kurulumu ve SHA-256 doğrulaması korunur.

**Önemli:** v1.0/v1.1 güncelleyicisi bu hatayı içerdiğinden, v1.1.1'e
ilk geçişte resmî GitHub Setup.exe'yi elle çalıştırmak daha güvenlidir.
Yerel siparişler, stoklar ve cihaz yetkisi silinmez.
"""


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
        bundled=(V201_NOTES+'\n\n'+V200_NOTES+'\n\n'+V111_NOTES+'\n\n'+V110_NOTES
                 if str(version)=='2.0.1' else
                 V200_NOTES+'\n\n'+V111_NOTES+'\n\n'+V110_NOTES
                 if str(version).startswith('2.') else
                 V111_NOTES+'\n\n'+V110_NOTES
                 if str(version)=='1.1.1' else V110_NOTES)
        if release and release.get('available') and release.get('notes'):
            self.notes.setPlainText(
                'YAYIMLANAN YENİ SÜRÜM NOTLARI\n\n'+
                str(release.get('notes') or '')[:3200]+
                '\n\n────────────────────\n\n'+bundled)
        else:
            self.notes.setMarkdown(bundled)
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
