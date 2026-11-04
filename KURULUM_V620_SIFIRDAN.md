# ALFA ERP V6.2.0 — Yeni Bilgisayara Temiz Kurulum

Bu sürüm Windows üzerinde Python kurulumu gerektirmeyen, birbirinden ayrı **Yönetici** ve **Personel** kurulum paketleri üretir.

## Sıfırdan kurulum
1. Mevcut uygulamaları ve varsa bildirim ajanını kapatın.
2. Eski yerel veriler varsa önce `%LOCALAPPDATA%\AlfaERP` klasörünü yedekleyin. Buluttaki siparişler ve katalog silinmez.
3. GitHub Releases sayfasından sürüm `v6.2.0` için iki ayrı kurulum dosyasını indirin.
4. `ALFA_ERP_Yonetici_Setup_V6_2_0.exe` ve `ALFA_ERP_Personel_Setup_V6_2_0.exe` dosyalarını ilgili Windows bilgisayarlarda çalıştırın.
5. Her iki uygulama da açılışta e-posta, yönetici parolası veya cihaz kodu sormadan ERP ekranını gösterir.
6. Bulut verilerinin kullanılabilmesi için bir kez **güvenli cihaz yetkilendirmesi** gerekir. Özel tek kullanımlık kurulum biletinin bulunduğu kuruluma ait pakette bu adım arka planda yapılır. Genel kurulum dosyasında **Buluta bağla** düğmesi kullanılabilir.
7. Üst bölümde **Bulut bağlı** görülmeden gerçekleşen yerel değişiklikleri buluta işlenmiş saymayın.
8. Yönetici Analitik bölümünde 6–12 rakamlı PIN belirler; personel aynı PIN ile yalnızca Analitik bölümüne erişir.

## Güvenlik ve veri bütünlüğü
- Yönetici kimlik bilgisi, gizli Supabase servis anahtarı veya tek kullanımlık cihaz bileti genel GitHub sürümüne eklenmez.
- Personel cihazına yönetici yetkisi verilmez; cloud rol kontrolü sunucu tarafındadır.
- Mevcut katalog ve sipariş tasarımları korunur; ayrı bir bulut siparişi sekmesi yoktur.
- `ALFA_TEMIZ_KURULUM.bat` yalnızca yerel verileri ayrı bir yedeğe taşır. Eski bekleyen işlemler gözden geçirilmeden silinmemelidir.
- Gerçek ortamda bağlantı hızı, kurum ağı ve Windows Defender engelleri ayrı etkiler yaratabilir.

## Windows derlemesi
Bu sürümün iki Setup.exe paketinin başarıyla oluşturulması için GitHub Actions Windows iş akışının tamamlanması ve paket başlangıç kontrolünün geçmesi gerekir.