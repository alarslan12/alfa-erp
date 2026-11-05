# ALFA ERP v1.1.0 — Personel ve Yönetici için tek Windows kurulumu

Windows 11 · PySide6 · Firebase Realtime Database · ortak çoklu cihaz sipariş havuzu.

**Sürüm notları:** [CHANGELOG.md](CHANGELOG.md). Eski v1.0.0
kararlı yayın [GitHub Releases](https://github.com/alarslan12/alfa-erp/releases/tag/v1.0.0)
üzerinde korunur.

## Kurulum ve erişim

`ALFA_ERP_Setup_V1_1_0.exe` tek dosya olarak **Personel / Yönetici**
seçtirir; her bilgisayara seçilen uygulama kurulur.

- **Personel:** katalog, siparişler, envanter, açık/koyu tema anahtarı,
  kategorili Hata Bildir, Duyurular ve Windows sipariş ses/bildirim ajanı.
- **Yönetici:** yönetim, cihaz yetkisi, Hata Merkezi, envanter satış iptali,
  ürün arşivleme/geri alma, Duyurular ve Güncelleme Merkezi.
- Yönetici kurulumu sabit kurulum parolası ister.
  **Bu parola bulutta yönetici rolü oluşturmaz.** Firebase
  `members/{uid}.role=owner` ve `active=true` kontrolünü ayrıca uygular.
- Yerel `%LOCALAPPDATA%\AlfaERP` veri ve cihaz dosyaları silinmez.

## v1.1 yenilikleri

- Satış iptalinde tek ETag kontrollü Firebase ürün güncellemesiyle
  orijinal alım partisine stok iadesi, iptal kaydını geçmişte tutma.
- Katalog ürünlerinde hard-delete yerine arşiv ve geri yükleme.
- Pillbox biçiminde okunur envanter satış formu, iptali muhasebeden
  düşen analiz ve işlem geçmişi.
- ETag yarışları için korunmuş retry; sipariş havuzu silme sonrası
  eski sunucu görüntüsünün geri eklenmesini engelleme.
- Başlıkta uygulama adı/sürümü, personel tema anahtarı ve Hata Bildir.
- Açık tema kontrastı: Siparişlere Genel Bakış, Cihaz Yetkisi,
  Sipariş Geldi popup pencereleri.
- Uygulama içinde Duyuru Merkezi ve otomatik kararlı güncelleme popup'ı.
  Sürüm kontrolü en fazla 24 saatte bir GitHub API isteği yapar; Firebase
  verisine fazladan sorgu eklemez. Kullanıcı onayı olmadan yeni sürüm kurulmaz.

## Güvenilirlik

- Siparişler, stok partileri, satış geçmişi ve kullanıcı kimlikleri
  sırf sürüm yükseltmesi için silinmez.
- Firebase Security Rules mevcut v1.0 sürümüyle uyumlu kalır;
  yeni kurallar veya ücretli Cloud Functions **gerekmez**.
- Firebase silme koruması, cihaz rolü, hata raporları ve bulut
  bağlantısı [Firebase kuralları](firebase/database.rules.json) üzerinden.
- Eşzamanlı iş kuralı çakışması oluşursa başarısız işlem arşive alınır,
  başka cihazın verisinin üzerine körlemesine yazılmaz.
- Yeni sürümün ilk yüklenmesinde duyurular otomatik görünür.
- Güncelleme Merkezi SHA-256 kontrolü yapar ve buluta henüz
  gönderilmemiş işler varsa yükseltmeye izin vermez.

## Derleme ve kararlı yayın

`.github/workflows/firebase-rtdb-preview.yml` Windows paketini,
`SHA256SUMS.txt` ve `RTDB_KURULUM.md` dosyasını Actions artifact olarak üretir.
Resmî sürüm yalnız başarılı kaynak derlemesinin tek EXE + SHA-256
dosyalarını GitHub Release'e ekler.

Kullanıcının hız tercihi doğrultusunda otomatik fonksiyonel testler
koşulmaz; sözdizimi, PyInstaller, Qt PDF modülü, Inno Setup paketleme
ve kurulum checksum kontrolleri yapılır. Gerçek Windows davranışının
ayrıca kabul edilmesi gerekir.

**Mimari uyarı:** Supabase tabanlı eski `main` dalıyla Firebase tabanlı
`firebase-rtdb-final` dalını körlemesine birleştirmeyin.
