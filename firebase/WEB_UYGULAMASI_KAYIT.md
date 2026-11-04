# ALFA ERP / Web Firebase yapılandırması alındı

**Project ID:** `alfa-erp-8700c`  
**Web App ID:** `1:992806140382:web:0cab0fed51b72fba91054f`  
**Auth Domain:** `alfa-erp-8700c.firebaseapp.com`  
**Messaging Sender ID:** `992806140382`

Firebase Web SDK yapılandırması kullanıcı tarafından sağlandı ve
`firebase/web/config.js` içinde geçiş dalına kaydedildi.

Bu `apiKey` Firebase'in herkese açık istemci proje tanımlayıcısıdır,
Admin SDK özel anahtarı değildir. Uygun API kısıtlamaları, Firebase Auth,
Firestore Security Rules ve gerektiğinde App Check şarttır.

`databaseURL` Realtime Database'e aittir; ALFA ERP için **Firestore**
hedefleniyor. İkisini aynı anda canlı sipariş deposu olarak kullanmayacağız.

`firebase/web/catalog_pilot.html` sayfası Firestore'un **yalnızca okuma**
bağlantısını sınamak içindir. Mobil kataloğun mevcut Supabase sipariş
gönderimini değiştirmez. Veri aktarımı, güvenli checkout ve Windows
bağlantısı tamamlanmadan üretim sürümüne geçilmez.

Gerçek Firebase projesine erişen yönetim bağlantısı bu sohbet ortamında
henüz mevcut olmadığı için kuralların yayımlandığı veya kaynak verilerin
aktarıldığı iddia edilmez.
