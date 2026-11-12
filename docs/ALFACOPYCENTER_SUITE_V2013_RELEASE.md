# ALFACOPYCENTER Suite v2.0.13 — Firebase ve Suite bütünleşmesi

## Bileşenler

- Personel ERP: Firebase Realtime Database, canlı SSE bildirimleri,
  çevrimdışı işlem kuyruğu, uygulama açılış kontrolleri ve Gardrops fiyat
  kuralı düzeltmesi.
- Yönetici ERP: aynı Firebase veri alanı, owner cihaz yetkileri ve
  arka plan eşitlemesi; ek yönetici kurulum parolası gömülmez.
- Banner Studio Pro 3.13: v2.0.12'deki son kapak ve afiş tasarım
  düzeltmeleri, kalıcı yerel tasarım arşivi ve Suite Güncelleme Merkezi.
- Print Center 2.0: yazdırma planı, kullanıcı oturumu izleme ajanı,
  Print Supervisor ve merkezi Suite Güncelleme Merkezi.

## Güncelleme / güvenlik

- Tek Suite Setup; kurulumda seçilen modüller yükseltmede korunur.
- GitHub v1/v6 sürüm karmaşasını önlemek için yalnız yayınlanmış,
  SHA-256 dosyalı ve gerçek Suite Setup varlığı olan v2.x yayınlar
  güncelleme kaynağıdır.
- Bütün bileşenlerin güncelleme kanalı aynıdır. Güncelleme kullanıcının
  açık onayını ve Windows kurulum sihirbazını gerektirir.
- Firebase owner yetkilendirmesi istemciye gömülü şifreyle değil,
  Firebase Rules ile uygulanır.
- Birikmiş sipariş işlemleri silinmez veya yanlış çalışma alanına
  yeniden gönderilmez.

## Veri güvenliği

`%LOCALAPPDATA%\AlfaERP` ve
`%LOCALAPPDATA%\ALFA_Banner_Studio_Pro` korunur.
Windows Spooler sürücülerine, aktif baskı işlerine, Firebase canlı
siparişlerine veya cihaz rollerine otomatik silme/yenileme uygulanmaz.

## Test sınırları

Windows CI: Python ve PySide6 çevrimdışı sözleşmeleri, Suite sürüm
seçimi, ERP Personel/Yönetici paketli EXE açılışı, Banner Studio ve
Print Center paketli self-check, Inno Setup derleme ve SHA-256.

İki gerçek bilgisayarda Firebase Auth/Rules yetki ve çevrimdışı
senkronizasyon testi ile gerçek yazıcılarda fiziksel sayfa/kağıt
kesilmesi senaryoları hâlâ saha testi gerektirir.
