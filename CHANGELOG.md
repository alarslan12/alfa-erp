# ALFA ERP · Sürüm Geçmişi

## [v2.0.28] — 2026-11-14

- Sipariş kapaklarında siyah toplam adet rozeti kaldırıldı; yalnızca SB/RNK etiketleri gösterilir.
- Personel ve Yönetici ortak kart bileşeni güncellendi.
- Katalog araması ve diğer işlevler korunur.


## [v2.0.27] — 2026-11-14

- Aktif sipariş ve havuz kapaklarında toplam adet ve SB/RNK etiketleri geri getirildi.
- Tek nüsha ve dar kapaklarda etiketler uyarlanır.
- Katalogda seri numarası ve kitap kodu ayrıştırılır; TUSDATA 24, 24 TUSDATA ve TUS 24 aramaları desteklenir.
- Personel ve Yönetici ortak kodu güncellendi.
- PDF, kapak önbelleği ve Firebase işleyişi korunur.


## [v2.0.26] — 2026-11-14

- TUSDATA Konu kitaplarının PDF adlarında kelime sırası ve Cilt 1/II farkları desteklendi.
- Seri, ders ve cilt numarası korunarak yanlış kapak eşleşmesi önlenir.
- Gerçekte eşleşmeyen PDF adları ayrıca raporlanır; katalogda PDF'si olmayan kitaplar işleme hatası sayılmaz.
- Sayfa sayısı olmayan kitaplar Katalog'da varsayılan gizlidir. İlk açılış ve Personel/Yönetici tercihleri düzeltilmiştir.
- Firebase kitap/siparişleri, çalışan kapak önbelleği ve manuel kapaklar korunur.


## [v2.0.25] — 2026-11-13

- DUSDATA 33 (katalog 117–130) ve DENTTEST (131–136) için benzersiz tam PDF adı eşleştirmesi.
- Kitap kodu yerine seri/cilt numarası yanlışlıkla eşleşmez; manuel ve mevcut kodlu kapaklar korunur.
- Sayfa bilgisi olmayan kitapları göster/gizle tercihi eklendi; varsayılan açık, sadece katalog görüntüsünü etkiler.
- Personel/Yönetici ortak kodu güncellendi; Firebase ve Excel verisi değişmez.


## [v2.0.24] — 2026-11-13

- v2.0.20–v2.0.23 kapak/Excel/PDF gerilemelerini geri alır; v2.0.19 çalışan koduna döner.
- Kapak JPEG'leri tekrar görünür (eski manifest filtrelemesi kaldırılmıştır).
- Firebase/Excel sayfa sayılarının daha önce değiştirilmesi otomatik geri alınmaz; veriler korunur.
- Kullanıcı verileri, siparişler, envanter ve cihaz yetkileri silinmez.
- Windows Suite sürüm numarası v2.0.24 olarak artırılır.


## [v2.0.24] — 2026-11-13

- Analitik'te en önemli dört rakam (Toplam Ciro, Kargo Sonrası
  Ciro, Ödenen Ciro, Ödenmeyen Ciro) belirgin ve açıklamalı tek finans
  panelinde toplandı; küçük ortalama/verimlilik KPI'ları ayrı gruba geçti.
- Ödenen/ödenmeyen tutarların müşteri bazlı banka tahsilatı değil,
  **Ödendi** işaretlenmiş tamamlanma günleriyle ilişkili olduğu açıklanıyor.
- Telafi siparişlerinde yeni kayıt ve düzenleme sırasında ciro zorunlu
  olarak sıfır; fiyat alanı gösterilmiyor. Eski yanlış telafi tutarları
  muhasebe raporu ve analitikte satış cirosu olarak sayılmıyor.
- Telafi ve açık adres kargoları tamamlanırken ayrı sorulmaya devam
  ediyor, genel kargo giderine bir kez eklenip cirodan düşülüyor.
- Kargo sonrası ciro **net kâr değildir**; formül ekranda açıklandı.
- Yatay PDF kapaklar artık +90° döndürülür; yeni otomatik kapak
  önbelleği mevcut manuel kapakları korur.
- Kitaplara Genel Bakış seçimlerinde yeni temalı açılır menü kullanılır;
  alttaki beyaz Qt listesi/şerit sorunu giderildi.
- Firebase, sipariş ve kullanıcı dosyaları, dört bileşenli Suite,
  Windows bildirim ajanı ve ortak Güncelleme Merkezi korunur.


## [v2.0.18] — 2026-11-13

- Sipariş grupları sayısal kitap koduna göre, veriyi değiştirmeden sıralanır.
- Sipariş takibi hazırlanmayanlar/kolilenmeyenler tek pillbox içinde ayrı filtrelenir.
- Sipariş sekme çubuğu yatay taşmayı kaydırır; sekmeler ayrı pencereye
  sürüklenebilir, geri sürüklenebilir veya 'Sekmeye geri al' ile kenetlenir.
- Katalog kartı başlık yüksekliği kısaldı, iki satırlı ad korundu;
  SB ve RNK sayaçları 27 piksele büyütüldü, ortadaki çizgi kaldırıldı.
- Dolap kodlarında son dört rakam ayrı blokta gösterilir.
- Sipariş bildirici Windows oturum açılışında zamanlanmış görev olarak
  başlar; Personel penceresi kapalıyken de görev çalışmaya devam eder.
- Doğal Windows sesleri ve isteğe bağlı şifreli ElevenLabs A/B uyarıları.
- Yatay PDF ilk sayfası 270 derece döndürülerek kapak olarak kaydedilir.
- Firebase, mevcut siparişler, ayrı yönetici yetkileri ve Suite bileşenleri korunur.


## [v2.0.17] — 2026-11-13

- Firebase kitap kodları Excel'deki benzersiz kodla eşleşir;
  eski 508/509/510 TIPDEMY kaymaları giderilebilecek şekilde düzeltildi.
- Buluta katalog yazmadan önce yedek, yazdıktan sonra aktif kitap
  ve mobil katalog readback doğrulaması yapılıyor.
- Sayfa sayıları yeni Personel/Yönetici siparişlerinde Firebase anlık
  görüntülerine ekleniyor. Eski 0 sayfalı görüntüler doğru katalog
  üzerinden toparlanıyor.
- Firebase katalog revizyonu sonrası mobil sipariş kataloğu önbelleği
  ve sipariş sayfa toplamları tazeleniyor.
- Cloud Shell kuru çalışma/fark kontrolü, operatör onaylı veri onarma.
- v2.0.16 Analitik PIN NativeCrash riskine karşı Qt iş parçacığı
  düzeltmesi ve dört bileşenli Suite korunuyor.
- Sipariş, cihaz yetkisi ve arşivler silinmiyor.


## [v2.0.16] — 2026-11-13

- Personel PIN doğrulama iş parçacığı tamamlandığında arayüze
  Qt GUI-thread slotları üzerinden dönülüyor; pencere ve thread kapanış
  sırasındaki yarış durumu önleniyor.
- Analitik ekranında yeniden boyutlandırma sırasında reentrant rapor
  inşasına karşı koruma eklendi.
- PIN doğrulaması başarılı Personel/Analitik açılışı ve grafik
  yeniden boyutlandırma Windows kalite kontrolüne dahil edildi.
- Firebase oturumları, siparişler, Suite kurulum şifresi ve diğer dört
  bileşenin dağıtım düzeni değişmedi.


## [v2.0.15] — 2026-11-13

- **Duyurular / Güncelleme Merkezi:** Personel ve Yönetici sürümlerinin
  önceki v1.x ve v2.x revizyon notları internet olmadan da okunabiliyor.
- **Personel Excel:** Ayarlar → Excel Katalog; onaylı Firebase staff/owner
  cihazından ortak kitap kataloğuna kullanıcı onaylı Excel güncellemesi.
- **Yönetici cihazları:** Aktif cihazlar önde, pasifler gizli; iptal edilen
  cihazların eski üyeliklerini kalıcı temizleme (owner onayı gerekir).
- **Yönetici Hata Merkezi:** Seçili hata raporunu silme ve yalnız incelenmiş
  raporları toplu temizleme; her iki işlem onaylıdır.
- **Firebase Security Rules:** Onaylı staff için kitap katalog güncellemesi,
  owner için iptal edilen cihaz ve hata onay kayıtlarını silme izni.
  GitHub değişikliği tek başına canlı Rules deploy etmez.
- Mevcut Suite Setup, owner kurulum parolası, sipariş kuyruğu,
  sipariş/katalog ekran görünümü, Banner/Print arşivleri korunur.


## [v1.1.1] — 2026-11-06

Güncelleme Merkezi güvenilirlik düzeltmesi · Tek Windows kurulum paketi.

- **Ana pencere kapanışı:** Güncelleme komutu modal pencerenin içinden
  çağrılsa da gerçek Yönetici/Personel ana penceresini bulur ve
  güncellemeden önce kapatır. Windows kurulum yardımcısı eski EXE açıkken
  üzerine yazmaya çalışmaz.
- **Bekleyen sipariş güvenliği:** Güncelleme Duyurular popup'ı içinden
  açıldığında bile ana uygulamanın gerçek bekleyen bulut işlemleri
  denetlenir; eşitleme sürüyorsa güncelleme engellenir.
- **Yeniden başlatma:** Kurulum başarıyla bitince doğru Personel/Yönetici
  EXE'si yalnızca bir kez açılır. Yönetici kurulum parolası geçerlidir.
- **Sorun raporu:** Kurulum yardımcısının bekleme, SHA-256, Windows
  yükleme ve yeniden başlatma aşamaları yerel durum dosyasına yazılır.
  Hata oluşursa sebep Güncelleme Merkezi'nin sonraki açılışında gösterilir.
  Tanı kayıtları Firebase'e yüklenmez.
- **Geçiş notu:** v1.0 ve v1.1'deki güncelleyici bu hatayı içerdiği
  için **v1.1.1 ilk kez GitHub'ın resmî Setup.exe dosyasından manuel
  kurulmalıdır**. Sonraki v1.x güncellemeleri uygulama içinden yapılabilir.
- Siparişler, envanter, maliyet geçmişi, Firebase Rules ve cihaz
  kimlikleri değiştirilmez. Otomatik işlev testleri çalıştırılmadı;
  Windows derleme, paketleme ve SHA-256 doğrulaması uygulanır.


## [v1.1.0] — 2026-11-05

İlk resmi güncelleme · Firebase Realtime Database · Windows 11 · tek Setup.exe.

### Envanter ve muhasebe
- **Yönetici satış iptali:** Satış analitiğinde ilgili satış seçilip gerekçe girilir.
  Firebase'de tek ETag kontrollü ürün güncellemesi orijinal satın alma
  partisinin stokunu geri yükler. Satış kaydı silinmez; `cancelled_at`,
  `cancelled_by` ve `cancel_reason` ile korunur. Tekrar iptal stokları
  iki defa artırmaz.
- **Katalog arşivleme:** Ürünler etkin katalogdan kaldırılıp daha sonra
  geri getirilebilir. Satış geçmişi, stok ve alış partileri silinmez.
- Satış ekranı bölünmüş pillbox/özet formu; açık/koyu/kontrast renkleri.
- İptal edilen satışlar net satış adet, ciro, brüt kâr ve grafiklerden
  çıkarılır; geçmiş tablosunda iptal kaydı görünür.
- Eski bağımsız `inventory/sales` göç kayıtları, partiyle güvenli bağ
  doğrulanamadığı için otomatik iptale açılmaz; manuel inceleme gerekir.

### Sipariş ve eşitleme
- Sipariş silindikten sonra henüz ulaşmamış eski Firebase yanıtının
  siparişi havuza anlık geri eklemesini önleyen yerel tombstone koruması.
- ETag yarışında tüm denemelerin tükenmesi artık **geçici** sayılır:
  başarılı olmayan işlem kanıtı / durable outbox korunur, kalıcı
  karantinaya yanlışlıkla atılmaz.
- Başka cihaz tarafından zaten hedef duruma alınmış siparişler
  tekrar çakışma yaratmadan onaylanır.
- Gerçek iş kuralı çakışmalarında (örneğin yetersiz stok, uygunsuz
  durum geçişi) başarısız işlem otomatik uygulanmaz; kullanıcı incelemesi
  için geçmiş hata arşivinde tutulur. Kayıtlar silinmez.

### Arayüz ve duyurular
- Üst sol panelde **ALFA ERP Yönetici / Personel v1.1.0** ayrımı.
- Personel Ayarlar düğmesi kaldırıldı; üst panelde açık/koyu tema anahtarı.
- Personelde bulut bağlantısı yanında **Hata Bildir**: yalnız seçilen
  teknik kategoriyi gönderir. Serbest metin ve kişisel müşteri verisi
  toplanmaz; internet yoksa rapor yerel sırada saklanır.
- **Duyurular** paneli ve sürüm notları; ilk kurulumda tek seferlik
  neler değişti penceresi.
- En fazla 24 saatte bir GitHub kararlı sürüm sorgusu ve yeni sürüm
  bulunduğunda popup; indirme ve kurulum yine kullanıcının onayıyla.
- Siparişlere Genel Bakış, Firebase Cihaz Yetkisi ve Yeni Sipariş
  popuplarında tam açık tema / yüksek kontrast desteği.

### Dağıtım ve veri güvenliği
- Tek `ALFA_ERP_Setup_V1_1_0.exe`: kurulum sırasında yalnızca seçilen
  Personel ya da Yönetici sürümü kurulur. Yönetici kurulum parolası
  ve Firebase owner rol doğrulaması sürer.
- `SHA256SUMS.txt` ile kurulum paketi doğrulanır. Güncelleme Merkezi
  kurulumdan önce buluta gitmemiş sipariş varsa yükseltmeyi engeller.
- Firebase veri şeması veya kuralları değiştirilmedi; ek ücretli
  Google Cloud servisi gerekmiyor.
- Önceki v1.0.0 kararlı Release ve tüm sipariş/stok geçmişi korunur.
- Otomatik davranış testleri kullanıcının hız tercihi nedeniyle
  **çalıştırılmaz**; yayın iş akışında sözdizimi, bağımlılık, paketleme,
  EXE ve SHA-256 kontrolleri yapılır.

## [v1.0.0] — 2026-11-05

İlk birleşik Windows kurulum paketi. Personel/Yönetici seçim ekranı,
Yönetici kurulum parolası, Firebase RTDB ortak sipariş havuzu,
Hata Merkezi, güncelleme mekanizması ve SHA-256 doğrulanan GitHub
Release dağıtımı.

[Download/Release v1.0.0](https://github.com/alarslan12/alfa-erp/releases/tag/v1.0.0)
