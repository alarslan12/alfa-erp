# ALFA ERP · Sürüm Geçmişi

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
