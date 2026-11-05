# ALFA ERP 6.6.0 — Windows Yönetici ve Personel

**Üretim kodu:** Firebase Realtime Database üzerinde çoklu cihazlı,
Windows 11 / PySide6 masaüstü uygulaması. Bu dal: `firebase-rtdb-final`.

Bu depo 2026-11-05 itibarıyla tek etkin Firebase Windows paketleme iş akışı
ve ayrı, manuel kararlı yayın iş akışı içerir. Önceki Supabase uygulaması
`main` dalında korunmuştur. **Geliştirme dalını ana dal ile körlemesine
birleştirmeyin; Firebase kuralları ve release yetkilerini önce doğrulayın.**

## Çalışan modüller

- Kitap kataloğu (Excel / Firebase), sayısal kod sıralaması, PDF ilk sayfadan
  yerel JPEG kapak önbelleği, manüel kapak önceliği.
- Katalogdan sipariş: aynı kargo kodu uyarısı (önceki siparişin tarih ve durumu),
  işlemden sonra Katalog'da kalma, kısa başarı bildirimi.
- Sipariş havuzu / aktif / tamamlanan, hazırlama-kolileme için aynı siparişte
  gruplanmış Firebase ETag koşullu yazma.
- Analitik PIN'i, muhasebe, ayrıntılı işlem günlüğü.
- Envanter: tarih ve maliyete göre alım partileri, satarken parti + fiyat
  seçimi, işlem geçmişi, ciro / maliyet / brüt fark.
- Personel arka plan bildiricisi: özel sesler ve Windows toast.
- Güncelleme Merkezi: en fazla 24 saatte bir GitHub kararlı sürüm kontrolü
  (tek GET), kullanıcı onaylı SHA-256 doğrulanmış Windows kurulumu.
- Hata Merkezi: Personel/Yönetici beklenmedik hata ve kalıcı bulut redlerinde
  tek olay raporu, yerel kalıcı kuyruk, Yönetici'de Firebase SSE ile canlı
  ve incelenebilir günlük. Müşteri verisi ve token gönderilmez.

## Kritik: Hata Merkezi için Firebase Rules geçişi

Yeni `error_reports` / `error_acks` alanlarının owner-only read,
authenticated-device create ve owner-only acknowledgement kuralları
`firebase/database.rules.json` dosyasında hazırlanmıştır.

**Canlı veritabanındaki kurallar otomatik değiştirilmedi.** Cloud Shell'de:

```bash
cd ~/alfa-erp
git checkout firebase-rtdb-final
git pull --ff-only
python3 tools/firebase_error_rules_cutover.py
```

Bu komut yalnız mevcut Rules'u kontrol edip yedekler. Kaynak kurallar ile
mevcut kurallar (iki yeni alan hariç) farklıysa durur. Yedek ayrı güvenli yere
alındıktan sonra, iki uygulamanın yeni sürümü kullanılmadan önce:

```bash
python3 tools/firebase_error_rules_cutover.py --apply
```

Terminal yalnız `ALFA-HATA-KURALLARINI-AC` onayıyla dağıtır.
İşlem **sipariş, katalog, cihaz ve stok verilerini silmez**. Kuralların
dağıtılmadığı bilgisayarlarda raporlar yerel kuyrukta saklanır ve
Yönetici'de bulut hata ekranı erişim uyarısı gösterir.

## Windows kurulum ve kararlı güncelleme

GitHub Actions: `.github/workflows/firebase-rtdb-preview.yml` çalıştığında
iki ayrı Inno Setup EXE ve `SHA256SUMS.txt` üretir.
Büyük uygulama testleri koşulmaz; derlemede Python sözdizimi ve
PDF modülü bulunabilirliği kontrol edilir.

Güncelleme Merkezi **yalnızca GitHub Releases/latest** üzerinden kalıcı,
`draft=false`, `prerelease=false` sürümleri kabul eder. Her sürüm
yüklemesinde aynı isimli Windows Setup.exe'ler ve SHA256SUMS.txt bulunmalıdır.
Yeni release eski çalışan EXE'yi zorla değiştirmez: indirme,
SHA doğrulaması, eşitlenecek iş yokluğu ve kullanıcı onayı gereklidir.

**GitHub Release yayını otomatik değildir.** Eski GitHub 403 workflow yetki
sorununu önlemek için `.github/workflows/alfa-stable-release.yml`
yalnızca açık yetkilendirmeyle manuel çalıştırılır. GitHub UI'da
`ALFA_RELEASE_TOKEN` (yalnız bu depo, Contents write, Workflows write)
tanımlanmalı; ilgili workflow GitHub'ın varsayılan dalında da mevcut
olmalıdır. Alternatif olarak yetkili repo sahibi GitHub Releases
web arayüzünden manuel tag/asset yayımlayabilir. **Token'ı koda koyma.**

Güncelleme başarısız olursa uygulama verileri, cihaz kimliği ve indirilen
kurulum korunur; `%LOCALAPPDATA%\AlfaERP\updates\last_update_error.txt`
yerel tanılama bilgisi saklar.

## Kota ve temizlik

- Hata gönderimi **olay başına**, tekrarlar 5 dakika sınırlı; ayrı poll yok.
- Yönetici SSE akışını dinler (tek açık Firebase bağlantısı); yalnız
  değişiklikte en son 70 rapor ve en son 150 incelenme kaydı çekilir.
- Python traceback/mesaj, müşteri adresleri, PDF'ler ve token buluta yüklenmez.
- Güncelleme denetimi günde en fazla bir kez; indirmeler manuel onaylıdır.
- Eski Windows build/release workflow dosyaları yalnız Firebase dalından
  kaldırıldı; `main` sürümü ve Git geçmişi yerinde.
- Canlı veritabanının `orders`, `inventory`, `audit` alanları
  **performans için silinmedi veya sıfırlanmadı**. İleri tarihli
  arşiv/retention ancak yedek ve ayrı denetimden sonra yapılabilir.

Güncel Firebase kota takibi: <https://console.firebase.google.com/project/alfa-erp-8700c/database>

İlgili rehberler:
- `docs/URETIM_OPERASYON_REHBERI.md`
- `docs/ALFA_ERP_V650_STABLE.md`
- `docs/ENVANTER_PARTI_SATIS_V642.md`
- `docs/GITHUB_YAYIN_KONTROLU.md`
