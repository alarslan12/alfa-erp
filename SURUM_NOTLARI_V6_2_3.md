# ALFA ERP V6.2.3 — Açılış Tanılaması ve Senkronizasyon

## Bu sürümde
- Uygulama Windows'ta **ALFA ERP** markalı splash ekranıyla başlar. Açılışta yerel veri dizininin yazılabilir olması, sipariş JSON dosyaları ve dayanıklı bulut kuyruğu, katalog/yapısal bileşenler ve cihaz eşleştirmesi doğrulanır.
- Eşleştirilmiş cihazlar için ilk bulut eşitlemesi arka planda çalışır. Başarılı yanıt geldiğinde açılış ekranı kapanır. Bağlantı yanıtı 6 saniye içinde gelmezse **uyarı gösterilerek uygulama açılır**; eşitleme arka planda devam eder. Bulut çevrimdışı diye yerel veriler silinmez.
- Daha önce bulutla eşitlenmiş cihazın doğru çalışma alanı kimliği yerel dosyadan geri yüklenir; internet olmadan yeniden açıldığında yapılacak işlemler yerel kuyruğa alınır. İnternet geri dönünce sunucu çalışma alanı doğrulanmadan kuyruk gönderilmez.
- Sipariş sayfasında çalışma sırasında bulut kontrolü yaklaşık 10–13 sn, boşta 45–52 sn aralığındadır. **Bu periyodik eşitlemedir; henüz Supabase Realtime WebSocket değildir.** Aynı siparişin birden fazla cihazdan çakışan değişiklikleri hâlâ arşivlenerek incelemeye sunulur.
- Gardrops siparişlerinde girilen tutar aynen kaydedilir. %90 otomatik kesinti uygulanmaz; bu durum otomatik regresyon kontrolüyle korunur.
- Supabase üretim veritabanında salt eklemeli indeks migration'ı ile yabancı anahtar indeks eksiklikleri kapatıldı; sipariş satırları veya tabloların iş kuralları değiştirilmedi.
- Yerel katalog ve Siparişler ekranlarının mevcut görünümü değiştirilmedi.

## Açılış kontrolleri ve sınırlamalar
- Splash ekranındaki göstergeler sadece **gerçek başlatma koşullarını** doğrular; bütün işlevlerin uçtan uca test edildiği anlamına gelmez.
- İlk kurulumda hiç bulut eşitlemesi yapılmamış cihazlar, güvenlik gereği çevrimdışıyken buluta bağlı sipariş işlemleri başlatamaz. En az bir başarılı çevrimiçi yetkilendirme ve senkronizasyon gereklidir.
- %LOCALAPPDATA%\AlfaERP klasörü siparişler, kuyruk, yerel eşitleme işaretçileri ve eşleştirme anahtarını barındırır. Yeniden kurmadan önce yedekleyin. Temiz kurulum işlemini bekleyen işlemler varken çalıştırmayın.
- Gerçek internet kesintisi / iki PC eşzamanlı operasyonu / 7x24 testleri henüz fiziksel cihazlarda yapılmadı.
- Supabase Auth'taki sızdırılmış parola koruması sunucu panelinden etkinleştirilmelidir; bu masaüstü güncellemesi bu ayarı değiştirmez.

## Paketler
- Windows personel: ALFA_ERP_Personel_Setup_V6_2_3.exe
- Windows yönetici: ALFA_ERP_Yonetici_Setup_V6_2_3.exe
- Kurulumu yapan bilgisayarda Python gerekmez.
