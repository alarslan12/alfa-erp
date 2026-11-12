# ALFA ERP Firebase üretim kontrol rehberi

## Mimarinin bileşenleri

- Windows Yönetici ve Personel sürümleri aynı yetkili Firebase Realtime
  Database çalışma alanına bağlanır.
- Mobil sipariş talepleri yalnızca yetkili cihaz tarafından aynı Sipariş
  Havuzu kayıtlarına dönüştürülür. Ayrı bulut siparişi sekmesi yoktur.
- Firebase Auth kimlikleri Windows DPAPI ile korunur. Yetki, Firebase Rules
  içinde owner/staff UID üyeliğine bağlıdır.
- Analitik PIN yalnızca yerel ekran kapısıdır, veritabanı güvenlik sınırı değildir.
- SSE bağlantısı olayları tetikler; yeniden bağlantı için revizyon kontrolleri
  yedek mekanizma olarak çalışır.

## Güvenli güncelleme kontrolü

1. Kurulu sürüm ve indirilen Setup.exe sürümü eşleşiyor mu?
2. \`%LOCALAPPDATA%\AlfaERP\` yedeklendi mi?
3. Her iki bilgisayarda bekleyen kuyruk sayısı **0** mı?
4. Cihazların Firebase owner/staff üyeliği doğru mu?
5. Firebase Rules test ortamında doğrulanıp yetkili operatörce yayımlandı mı?
6. İki PC aynı siparişte eşzamanlı değişiklik yapınca çakışma güvenle
   korunuyor mu? İnternet kesilince kuyruk sürüyor mu?
7. Uzun süre çevrimdışı kalan cihaz doğru Firebase çalışma alanına mı dönüyor?

**İşlem kuyruğunda bekleyen kayıt varken veri klasörünü sıfırlamayın.**
Bütün üretim kayıtlarının yedeklenmesi ve kurtarma yöntemi olmadan
veritabanını temizleme veya yeniden başlatma işlemi yapılmamalıdır.

## Firebase kullanım sınırları

Firebase Console'da Realtime Database → Usage ekranından depolama,
download ve concurrent connection sayılarını takip edin. SSE dinleyicileri
ve periyodik sorgular ücretsiz kullanım kotasını tüketebilir.

Resmî konsol: https://console.firebase.google.com/project/alfa-erp-8700c/database

Bu rehber kaynak kodunu düzenler; Firebase Console ayarlarını kendiliğinden
değiştirmez.
