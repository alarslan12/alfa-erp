# ALFA ERP v1.0 — Tek Windows Kurulumu

**Üretim altyapısı:** Firebase Realtime Database + Firebase Authentication,
Windows 11 / PySide6. Kaynak geliştirme dalı: `firebase-rtdb-final`.
Önceki Supabase tabanlı `main` dalını **birleştirmeyin**.

## Kurulum

GitHub Actions `.github/workflows/firebase-rtdb-preview.yml` iki uygulamayı
paketler; Inno Setup ise **bir** `ALFA_ERP_Setup_V1_0_0.exe` üretir.

Kurulum sihirbazında:
- **Personel:** katalog, sipariş havuzu, aktif sipariş, sesli/Windows bildirimi.
- **Yönetici:** aynı ERP işlemleri ve yönetim, cihazlar, Hata Merkezi.
  Bu seçenekte **sabit Yönetici kurulum parolası** gereklidir.

Parolanın yalnızca SHA-256 doğrulama değeri `alfa_tek_kurulum.iss`
içinde bulunur. Parola **Firebase owner yetkisinin yerine geçmez**:
bulut verilerine/cihaz yönetimine erişim için cihazın Firebase'de
`members/{uid}.role=owner` ve `active=true` olması zorunludur.
Parolayı EXE'den tamamen gizlemek mümkün olmadığından bunu sistemin tek
güvenlik sınırı olarak değerlendirmeyin.

Kurulum mevcut sürümlerin **AppId'lerini ve yükleme dizinlerini** kullanır;
`%LOCALAPPDATA%\AlfaERP` içindeki uygulama verileri ve cihaz kimliği
silinmez. Bu sürüm 6.6.0'dan **1.0.0** olarak yeniden numaralandırıldığı
için ilk yükseltmede birleşik Setup.exe'yi **elle** yükleyin. Sonraki
v1.x güncellemeleri Güncelleme Merkezi'nde aynı birleşik EXE'yi arar.
Yönetici güncellemelerinde kurulum sihirbazı yeniden parola ister.

## Modüller ve maliyet kontrolü

- Katalog: Excel / Firebase; PDF/JPEG kapaklar, mobil katalog.
- Siparişler: havuz/aktif/tamamlanan, aynı kargo kodu uyarısı,
  Firebase ETag ile çakışmaya dayanıklı güncellemeler.
- Analitik PIN, envanter, muhasebe, işlem günlüğü.
- Personel bildiricisi ve Yönetici cihaz yetkilendirmesi.
- Hata Merkezi: yalnız hata gerçekleştiğinde anonimleştirilmiş teknik
  rapor gönderimi; offline dosya kuyruğu; Yönetici SSE akışı.
- Güncelleme Merkezi: günlük en fazla bir sürüm sorgusu, SHA-256 kontrolü,
  bekleyen sipariş varsa güncellemenin engellenmesi.
- Eski mobil checkout geçmişinde tekil sorguları azaltma;
  veri silmeden RTDB trafiğini düşürme.
- Firebase Rules, siparişin doğrudan hard-delete edilmesini engeller;
  uygulamadaki `deleted_at` soft-delete davranışı korunur.

## Firebase güvenliği

Güvenlik kuralları `firebase/database.rules.json` içinde saklanır.
Canlı kurallar, `tools/firebase_error_rules_cutover.py` ile ayrı
yedek/ön kontrol/terminal onayından sonra güncellenmelidir.
Kuralların GitHub'da bulunması **canlı Firebase'e otomatik dağıtım
yapıldığı anlamına gelmez**. Veritabanı reseti yapılmaz.

## Derleme ve yayın

Windows Actions:
- `ALFA_ERP_Setup_V1_0_0.exe`
- `SHA256SUMS.txt`
- `RTDB_KURULUM.md` (dağıtım rehberi)

Kararlı yayın `.github/workflows/alfa-stable-release.yml`
üzerinden **manuel** ve başarılı Actions `source_run_id` ile yapılır;
`v1.0.0` etiketi GitHub Releases'te tek kurulum EXE'sini içerir.
İlgili workflow varsayılan dalda mevcut olmalı ve yetkili
`ALFA_RELEASE_TOKEN` tanımlanmalıdır. Token veya şifre
**GitHub depoya, hata raporlarına veya servis koduna kaydedilmez**.

Otomatik işlev testleri hız tercihi nedeniyle koşulmaz. Derleme sözdizimi,
PyInstaller paketleme, Qt PDF bağımlılığı ve kurulum SHA-256'sını kontrol
eder; gerçek Windows Yönetici/Personel kurulumu, parola sayfası ve
Firebase yetkisi ayrıca kabul edilmelidir.

Uygulama/katalog/sipariş geçmişi temizlik bahanesiyle silinmez.
Firebase Usage: https://console.firebase.google.com/project/alfa-erp-8700c/database
