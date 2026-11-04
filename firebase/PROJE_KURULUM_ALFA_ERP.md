# ALFA ERP — Firebase proje kurulumu

**Firebase Project ID:** `alfa-erp-8700c`

Bu dosya yalnızca proje kimliğini kaydeder. Firebase projesine bağlantı, veritabanı kurulumu veya veri aktarımı yaptığı anlamına gelmez. Firestore bölgesi, kimlik doğrulama sağlayıcıları ve kurallar henüz doğrulanmadı.

## Firebase Console'da gerekli adımlar

1. [Firebase Console](https://console.firebase.google.com/project/alfa-erp-8700c/overview) sayfasını aç.
2. **Build → Firestore Database → Create database**: Standard edition; database ID `(default)`. Bölge henüz seçilmediyse `europe-west3` (Frankfurt) uygundur; oluşturulduktan sonra bölge taşınamaz. **Production mode** seç: test mode tüm kayıtlara istemci erişimi açabilir.
3. **Build → Authentication → Get started**. Sonra uygulama cihazlarını giriş ekranı olmadan oturumda tutmak için bir kerelik kimlik bağlama yöntemi tasarlanacak. Personelin rastgele anonim kullanıcı olarak iş yetkisi kazanmasına izin verme.
4. Firebase projesine bir **Web app** kaydet; SDK yapılandırmasındaki `apiKey`, `authDomain`, `appId` gibi istemci tanımlayıcıları daha sonra mobil katalog için kullanılabilir. **Servis hesabı JSON / özel anahtarları** GitHub'a veya sohbet mesajına yapıştırma.
5. Firestore veritabanının oluşturulduğunu ve bölgesini doğrula. Firebase hesabını bu sohbette yetkilendirebilirsen gerçek proje durumunu doğrudan kontrol etmek mümkün olabilir.

## Kod ve veri aktarımı durumu

- Firebase proje kimliği `firebase/.firebaserc` içinde kaydedildi.
- Hazırlanmış güvenlik kuralları `firebase/firestore.rules` içindedir; henüz yayımlanmadı.
- Özel veri dışa aktarım aracı `tools/firebase_export_supabase.py`; kontrollü içe aktarma `tools/firebase_stage_import.py`.
- **Canlı Supabase uygulamalarının bağlantısı değiştirilmedi.** Siparişler, katalog ve yerel bekleyen işlemler korunuyor.
- Gerçek aktarım için Firebase üzerinde yetkili erişim, kaynağın güvenli yedeği, sayım doğrulaması ve sonradan rol/işlem kuralları gereklidir.

## Önemli güvenlik notları

- Yeni bir Firestore projesinde `Production mode` başlangıçta istemci okuma/yazmalarını kapatır.
- Personel uygulamasının giriş ekranı göstermemesi = veritabanının anonim ve korumasız olması değildir.
- Gerçek zamanlı emir dinleyicileri ve mobil sipariş yazma işlemleri ancak rol doğrulaması, idempotency ve yarış koşulları çözüldükten sonra etkinleştirilecek.
- Free Spark planında Cloud Functions ve diğer ürünlerin kullanılabilirliği için güncel Firebase konsolunda plan koşullarını kontrol etmek gerekir; *tam backend hizmetlerinin ücretsiz olacağını varsayma.*
