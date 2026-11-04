# ALFA ERP V5.1 Mobil Panel (Alpha)

- `index.html` mobil ön yüzdür; Supabase Auth, RLS ve atomik `alfa_create_order` sunucu fonksiyonunu kullanır.
- Geliştirme için `python -m http.server 8080 --directory mobil_panel` komutuyla localhost'ta görüntülenebilir.
- İnternet erişimi ve yönetici/operatör üyeliği gerekir. Yönetici olmadan katalog boş kalır.
- **Henüz herkese açık bir adrese yayımlanmadı.** Telefonlardan farklı ağlarla erişim için ilerleyen aşamada HTTPS statik hosting gereklidir.
- `sb_publishable_...` anahtarı halka açık istemci anahtarıdır; şifre / secret / service_role kullanılmaz.
- Oturum JWT'si yalnızca bellek içinde tutulur, sayfa yenilenince tekrar giriş gerekir.
- Oturum açma, sepet ve mobil sipariş gönderimi hazır; masaüstüne çift yönlü yazma senkronizasyonu henüz açık değildir.
