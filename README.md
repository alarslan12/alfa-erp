# ALFA ERP v1.1.2 — Firebase masaüstü uygulaması

**Personel ve Yönetici**, tek Windows Setup.exe içerisinde ayrı kurulum
seçenekleridir. Masaüstü uygulaması PySide6, Firebase Authentication ve
Firebase Realtime Database kullanır.

## Bu sürümde

- Açılışta ALFA ERP splash screen: yerel dosyalar, sipariş kuyruğu, katalog,
  cihaz kimliği ve Firebase bağlantısı denetimi.
- İnternet yokken uygulama en fazla kısa bir bağlantı denetiminden sonra
  çevrimdışı açılır. Önceden doğrulanmış çalışma alanı işareti diskten alınır;
  gönderilmeyi bekleyen kuyruk korumalıdır.
- Firebase SSE ile değişiklik bildirimi ve kaçırılan olaylar için
  aktif kullanımda 10–13 saniye, boşta 45–52 saniye fallback senkronizasyon.
- Gardrops siparişine girilen tutarın **%100'ü** kaydedilir; %90 kesinti yoktur.
- Eski bulut istemcileri ve geçiş araçları aktif kaynak ağacından kaldırılmıştır.
- Firebase cihaz kimlikleri Windows DPAPI ile şifrelenir. Personel ve Yönetici
  cihaz oturumları birbirinden ayrıdır.
- Yönetici yetkisi yalnızca Firebase Security Rules ve onaylı owner UID ile
  belirlenir; kuruluma gömülü sabit bir yönetici şifresi bulunmaz.
- Yerel Katalog ve Siparişler ekranlarının mevcut tasarımı korunur.

## Kurulum

\`ALFA_ERP_Setup_V1_1_2.exe\` üzerinden Personel veya Yönetici seçin.
Eski sürümün üzerine kurarken **\`%LOCALAPPDATA%\AlfaERP\` klasörünü silmeyin**.
Burada cihaz kimliği, siparişler ve gönderilmeyi bekleyen işlemler bulunur.

Firebase rolü bilinmeyen bir bilgisayara yönetici sürümünü kurmak,
bulut üzerinde yönetici ayrıcalığı vermez. Cihaz onayı Firebase ile yapılır.

## Yayımlama ve test

Kaynak kodu: \`firebase-rtdb-final\` dalı.
GitHub Actions: \`.github/workflows/firebase-rtdb-preview.yml\`.
Güvenlik kuralları: \`firebase/database.rules.json\`.
Kuralların Firebase'e yayımlanması ayrıca yetkili bir proje hesabı gerektirir.

Önceki çevrimdışı veri ve kuyrukların korunması, bilgisayarların fiziksel
bağlantı kesintisiyle test edilmesi ve Firebase Rules yetkilerinin gerçek
bir test hesabıyla doğrulanması üretime alma önkoşuludur.

[Kurulum ve işletim rehberi](firebase/RTDB_KURULUM.md)
