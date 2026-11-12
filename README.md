# ALFACOPYCENTER Suite v2.0.13

**Tek Windows kurulumu**, dört seçilebilir bileşen:

| Bileşen | Kaynak/çalıştırılabilir | Kurulum |
|---|---|---|
| ALFA ERP Personel | Staff/AlfaERP.exe | Seçilebilir, varsayılan |
| ALFA ERP Yönetici | Owner/AlfaERPYonetici.exe | Seçilebilir; Firebase'de yetkili owner rolü zorunlu |
| ALFA Banner Studio Pro | BannerStudio/AlfaBannerStudio.exe | Seçilebilir, varsayılan |
| ALFA Print Center | PrintSurveillance/AlfaPrintSurveillance.exe | Seçilebilir, varsayılan |
| Arka plan yardımcıları | Bildirim, PrintAgent, PrintSupervisor | Seçilen bileşene bağlı |

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_13.exe`. Aynı Inno Setup AppId
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
