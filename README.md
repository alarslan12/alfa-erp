# ALFACOPYCENTER Suite v2.0.27

**Tek Windows kurulumu**, dört seçilebilir bileşen:

| Bileşen | Kaynak/çalıştırılabilir | Kurulum |
|---|---|---|
| ALFA ERP Personel | Staff/AlfaERP.exe | Seçilebilir, varsayılan |
| ALFA ERP Yönetici | Owner/AlfaERPYonetici.exe | Seçilebilir; Firebase'de yetkili owner rolü zorunlu |
| ALFA Banner Studio Pro | BannerStudio/AlfaBannerStudio.exe | Seçilebilir, varsayılan |
| ALFA Print Center | PrintSurveillance/AlfaPrintSurveillance.exe | Seçilebilir, varsayılan |
| Arka plan yardımcıları | Bildirim, PrintAgent, PrintSupervisor | Seçilen bileşene bağlı |

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_27.exe`. Aynı Inno Setup AppId
(`ALFACOPYCENTER.Suite`) ve kurulum yolu korundu:
`%LOCALAPPDATA%\Programs\ALFACOPYCENTER`.

## Güncelleme Merkezi

Personel, Yönetici, Banner Studio ve Print Center **aynı kararlı Suite
sürümünü** kontrol eder. Yalnız `v2.x` Suite GitHub Releases ve gerçek
`ALFACOPYCENTER_Suite_Setup_Vx_y_z.exe` + `SHA256SUMS.txt` birlikte
yayımlandıysa güncelleme sunulur. Diğer geçmiş ERP v1/v6 yayınları Suite
güncellemesi sayılmaz.

Paket indirildikten sonra SHA-256 doğrulanır. Onaylanan güncelleme sırasında
uygulama kapanır, mevcut Suite'in seçili bileşenleri korunur ve aynı
uygulama yeniden başlatılır. ERP işlem kuyruğu doluysa ERP güncellemesi
engellenir. Print Center, yerel ERP kuyruğunu ayrıca kontrol eder.
Banner Studio kendi yerel web Güncelleme Merkezi'ne sahiptir.

Güncelleme **otomatik kontrol** ve **kullanıcı onaylı kurulum** yapar;
kullanıcı izni olmadan uygulama değiştirilmez.

## Firebase ve çevrimdışı mod

Personel ve Yönetici bulutta Firebase Authentication + Realtime Database
kullanır. Firebase cihaz kimlikleri Windows DPAPI ile korunur.
Başarılı ilk eşitlemeden sonra internet kesintisinde sipariş kuyruğu yerelde
kalır; doğru çalışma alanı yeniden doğrulanmadan buluta gönderilmez.
Firebase SSE etkin bildirim kullanır, kaçırılan olaylar periyodik denetlenir.
Gardrops satışında girilen tutarın **%100'ü** saklanır.

Açılış splash ekranında yerel dosyalar, kuyruk, katalog, cihaz kimliği ve
Firebase durumu ayrı gösterilir. İnternet olmaması uygulamayı süresiz
bekletmez. Mevcut Katalog ve Siparişler ekran tasarımı korunur.

## Veriler korunur

**Aşağıdaki kullanıcı klasörlerini silmeyin:**

- `%LOCALAPPDATA%\AlfaERP`: siparişler, kuyruk, Firebase kimlikleri,
  bildirimler ve Print Center geçmişi.
- `%LOCALAPPDATA%\ALFA_Banner_Studio_Pro`: afiş tasarımları, kapaklar,
  fiyatlar ve çalışma arşivi.

Yeni sürüm önceki Suite v2.x kurulumuna yükseltme olarak uygulanır.
İlk geçişte eski v1 ERP kurulumuyla yan yana bulunabilir; eski kısayolu
yeniden kullanmayın.

## Derleme ve doğrulama

Tek dağıtım komutu: `ALFA_BUILD_SUITE_WINDOWS.ps1`.
Tek dağıtım manifesti: `ALFACOPYCENTER_Suite.iss`.
Tek Windows kalite kapısı: `.github/workflows/alfacopycenter-suite.yml`.
Eski tekil ERP Setup betikleri yeni derlemeden çıkarılmıştır.

Yerel/CI testleri, gerçek Firebase hesap onayı ve fiziksel yazıcı
hatalarını tek başına doğrulamaz. Uçtan uca iki-PC senkronizasyon ve
fiziksel çıktı güvenilirliği ayrı operatör doğrulaması gerektirir.

[Suite yayınları](https://github.com/alarslan12/alfa-erp/releases) ·
[Firebase kurulum rehberi](firebase/RTDB_KURULUM.md)

## Yönetici kurulumu ve Cloud Shell

Suite kurulumunda **Yönetici** bileşeni seçildiğinde güçlü bir yerel kurulum
şifresi sorulur. Uygulama kaynak kodunda veya kuruluma eklenen dosyalarda
şifrenin kendisi bulunmaz; yalnız rastgele tuzla oluşturulmuş doğrulama
özeti vardır. Parola yalnız kurulum engelidir; Firebase owner yetkisini
**asla** kendi başına vermez.

Owner Firebase UID yetkisi, yetkili proje operatörü tarafından Google Cloud
Shell'de `tools/rtdb_authorize.py` ile onaylanır. Kurulum ve onaylama adımları
`firebase/RTDB_KURULUM.md` dosyasındadır.

## v2.0.24: Excel / Firebase katalog eşleştirme onarımı

Katalogda kitap kodları veya sayfa bilgileri yanlışsa doğru Excel'i
Yönetici uygulamasındaki Excel kataloğu bölümünden buluta yeniden yükleyin.
Kaynak kodu kitapları satır sırasına göre numaralandırmaz: Excel'deki kod
esas alınır. Firebase'deki eski kitap verileri yükleme öncesi otomatik
yedeklenir; yazılan kitaplar ve mobil katalog sunucudan doğrulanır.
Personel uygulamasında onaylı cihazlara Excel Katalog seçeneği de vardır.

Yetki reddi yaşanırsa Cloud Shell araçları ile salt-okunur karşılaştırma
ve kontrollü düzeltme yapılabilir (firebase/RTDB_KURULUM.md).
Yeni Suite kurulumu canlı Firebase katalogunu tek başına değiştirmez.

## v2.0.24: Sipariş sekmeleri ve bildirim ajanı

Sipariş detayları sayısal kitap koduyla sıralanır. 'Hazırlanmayanlar'
ve 'Kolilenmeyenler' filtreleri tek buton alanını paylaşır. Sekme çubuğunda
sekme dışarı sürüklenerek ayrı pencere yapılır; pencerenin üstünden
sekme çubuğuna geri sürüklenebilir ya da 'Sekmeye geri al' kullanılır.

Ayarlar → Bildirim sesi içinde ücretsiz Windows konuşma sesleri ve
isteğe bağlı ElevenLabs sesleri bulunur. Personel kurulunca zamanlanmış
görev `ALFA_ERP_OrderNotifications` kullanıcının oturumu açıldığında
bildirim ajanını başlatır. ERP kapatılsa da ajan sistem tepsisinde kalır.
Windows kullanıcı oturumu açık ve Firebase cihazı onaylı olmalıdır.

Yatay ilk PDF sayfaları 270° döndürülür. Kapaklar için Ayarlar →
Tara ve kapakları güncelle kullanılabilir. Manuel kapaklara dokunulmaz.

## Suite v2.0.24 — finans paneli ve telafi muhasebesi

Analitik sayfasında en önemli dört ciro göstergesi kendi panelinde
birbirine yakın ve açıklamalı görünür. Ödeme değerleri tamamlanma günü
bazlı 'Ödendi' işaretinden hesaplanır; doğrudan banka tahsilatı değildir.

Telafi siparişinde fiyat girilmez ve tüm yerel yeni/düzenle işlemleri
0 TL ciro kaydeder. Kargo bedeli yalnız tamamlanırken sorulup
Analitik'te Telafi/Açık Adres olarak ayrı gösterilir. Kargo sonrası
cirodan baskı, işçilik veya diğer giderler düşülmediği için net kâr
değildir. Önceden yanlış ciro yazılmış telafi kayıtları raporda satış
görülmez; geçmiş sipariş verileri otomatik olarak değiştirilmez.

Yatay ilk PDF kapaklar artık ters yöne değil +90° döndürülür; kapakları
yenilemek için Ayarlar → Kapakları tara / güncelle kullanılabilir.


## v2.0.24: Önceki çalışan sürüm kaynaklarına dönüş

PDF/kapak/Excel/katalog kodları v2.0.19 sürümüne geri alındı. Yerel otomatik JPEG kapaklar manifest yüzünden gizlenmeyecek. Firebase verileri otomatik değiştirilmez. Kurulumdan önce `%LOCALAPPDATA%\AlfaERP` klasörünü ve Excel/PDF arşivini yedekleyin. Sayfa sayıları Firebase'de zaten sıfırlanmışsa eski Excel veya `catalog_backups` dosyalarıyla ayrıca geri yüklenmelidir.

## v2.0.25: DUSDATA 33 ve DENTTEST PDF kapakları

Çalışan v2.0.24 sistemi korunur. Tam ve benzersiz kitap adından PDF eşleştirilir; DUSDATA 33 / DENTTEST seri sayıları kitap koduyla karışmaz. Var olan kapaklar ve Firebase verileri değişmez. Ayarlar → Görünüm'de sayfa bilgisi boş kitapların gösterimi isteğe bağlıdır (varsayılan açık). Personel ve Yönetici aynı ortak PDF ve ayar kodunu kullanır.

## v2.0.26 — TUSDATA Konu kapakları ve sayfasız kitaplar

TUSDATA Konu kapakları sırası değişmiş veya `Cilt 1` eklenmiş PDF dosya adlarıyla benzersiz eşleştirilir; diğer serilere veya cilt numaralarına ait PDF seçilmez. Eşleşmeyen gerçek dosya adları `alfa_pdf_eslestirme_raporu.json` dosyasına kaydedilir. Katalog kartlarında sayfa sayısı boş/0 kitaplar varsayılan gizli; Personel/Yönetici aynı ayarı kullanır. Firebase verileri ve eski kapaklar korunur.

## v2.0.27 — Sipariş etiketi ve seri araması

Aktif sipariş ve havuz kapaklarında toplam nüsha, SB/RNK adetleri görünür. Katalogda TUSDATA 24, 24 TUSDATA, TUS 24 gibi aramalar tam sayı eşleşmesi ve seri adını kullanır. Personel ve Yönetici ortak kodu güncellenmiştir. Firebase ve PDF eşleştirme korunur.
