# ALFA ERP V6.1.6 — Temiz Kurulum ve Kesintisiz Eşitleme

## Kritik düzeltme: geçici hatalarda işlem kaybolmaz
- Bulut ağ geçidinde `upstream request timeout` daha önce hatalı biçimde 409 (kalıcı çakışma) döndürüyordu. Artık 503 (geçici sorun) döndürür; işlem `op_id` korunarak yeniden denenebilir.
- Masaüstünde 401/403 (ör. oturum/cihaz erişimi) veya 503/504 hataları, sipariş hareketini otomatik olarak kalıcı ret arşivine taşımaz. Operasyon kuyruğunda korunur.
- Durum/hazırlama güncellemesi başarılı olunca ilgili sipariş buluttan tekrar okunur.
- Her 45 saniyede bir siparişlerin gerçek durumu zorunlu doğrulanır. Bu süreç her seferinde kitap kataloğunu ve envanteri tekrar indirmez.
- Bu doğrulama, önceki yerel işlem kuyruğunun engellediği silme ve değişikliklerin daha sonra yeniden görülmesini sağlar.
- Eşitleme başarısız olursa kısa bir beklemeden sonra tekrar dener; arka arkaya başarısızlıkta Supabase'e gereksiz sık istek yollamaz.

## Sıfırdan temiz yerel kurulum
- Windows için `ALFA_TEMIZ_KURULUM.bat` ve `ALFA_TEMIZ_KURULUM.ps1` sunuluyor.
- Araç, kullanıcı `SIFIRLA` yazarak onaylarsa eski `%LOCALAPPDATA%\AlfaERP` klasörünün tamamını tarihli yedek klasörüne **taşır**, ardından temiz bir yerel veri klasörü oluşturur.
- Varsayılan olarak aynı Windows kullanıcısındaki DPAPI korumalı cihaz eşleştirmesini yeni klasöre geri koyar. Tekrar eşleştirme gerekirse `-NoPairing` seçeneği kullanılabilir.
- Eski reddedilmiş olaylar, kuyruk, önbellek ve ayarlar silinmek yerine **yedeklenir**; temiz kurulumda otomatik yeniden gönderilmez.
- **Supabase siparişleri, geçmiş kayıtları, ürünler, muhasebe veya cihaz yetkileri silinmez.**
- Yönetici ve personel Setup.exe dosyaları normal biçimde sıfırdan yüklenebilir.

## Kontroller
- Windows birim ve ekransız Qt GUI testleri, periyodik senkronizasyon doğrulaması, ağ geçidi zaman aşımı testleri.
- Windows CI sandbox'ında yerel sıfırlama aracının eski kuyruğu yedekleyip yeni klasörü boşaltması, eşleştirmeyi koruması ve isteğe bağlı olarak eşleştirmeyi sıfırlaması.
- Yönetici ve personel paketlenmiş EXE açılış testleri.
- Sunucudaki düzeltme `alfa-erp-device` Edge Function sürüm 16 olarak yayımlanmış, kaynak kodu ayrıca `supabase/functions/alfa-erp-device/index.ts` dosyasına eklenmiştir.

## Gelecekte tamamlanan sipariş sayısı artarsa
- Eski siparişleri silmek yerine tarih bazlı arşiv sayfalaması ve yalnızca değişen siparişlerin indirilmesi gerekir.
- Mevcut indeksler `workspace_id/status/created_at`, `workspace_id/completed_on` ve `workspace_id/updated_at/id` sorgularını destekler.
- Şu anki birkaç sipariş üzerinde geçmiş verileri silmek performans kazancı sağlamaz.
- Bu sürümde kurumsal arşiv/sonsuz geçmiş sayfalama sistemi henüz eklenmemiştir.

## Kurulum adımları
1. İki bilgisayarda ERP'yi ve bildirim ajanını kapat.
2. Eski sürümleri Windows uygulamalarından kaldırabilirsin.
3. İndirilen `ALFA_TEMIZ_KURULUM.ps1` ve `ALFA_TEMIZ_KURULUM.bat` aynı klasördeyken BAT dosyasına çift tıkla, onay istenince `SIFIRLA` yaz.
4. Yönetici PC'ye Yönetici Setup.exe, personel PC'ye Personel Setup.exe yükle.
5. Siparişler buluttan yeniden gelir. Eşleştirme korunmuşsa otomatik bağlanır. Eski başarısız hareketleri yeniden uygulamadan önce siparişin güncel durumunu kontrol et.

## Güvenlik
Yerel dosyaların yedeği kullanıcının bilgisayarında kalır; çevrimiçi veri yedeği veya bulut temizliği yapılmaz. Eski bulut hareketlerini otomatik tekrar göndermek duplicate hazırlama/kolileme riski yaratabileceğinden bilinçli olarak yapılmaz.
