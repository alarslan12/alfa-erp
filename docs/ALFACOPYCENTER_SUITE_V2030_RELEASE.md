# ALFACOPYCENTER Suite v2.0.30 — Stabilite ve optimizasyon

- Doğrudan v2.0.28 çalışan kaynak ağacı esas alınmıştır. İptal edilen v2.0.29 kargo fişi özelliği dahil değildir.
- Güncelleme indirmeleri 512 KiB bloklarla yapılır; arayüz ilerleme bildirimleri saniyede yaklaşık 10 ile sınırlandırılır, son ilerleme her zaman bildirilir. SHA-256 ve kurulum öncesi eşitleme kontrolleri korunur.
- İptal edilen v2.0.29 yeni güncelleme merkezinde aday olarak değerlendirilmez.
- Sipariş bildirimi servisinde durum değişmediyse gereksiz yerel JSON yazımı yapılmaz; yeni sipariş tespiti ve ses davranışı korunur.
- Personel, Yönetici, Banner Studio ve Print Center aynı Suite paketindedir.
- Firebase güvenlik kuralları, veri modeli, kullanıcı yetkileri, Katalog ve Siparişler kodu v2.0.28 ile aynıdır. Yeni kural yayımlamak gerekmez.
- Daha önce canlı kargo fişi kuralları yayımlandıysa, aktif siparişleri tamamlamadan önce durum ayrıca doğrulanmalıdır.
