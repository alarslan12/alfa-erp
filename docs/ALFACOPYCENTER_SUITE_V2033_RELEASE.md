# ALFACOPYCENTER Suite v2.0.33 — Sipariş notu ve okundu akışı düzeltmesi (ön izleme)

- Katalog ve yönetici not alanları koyu/açık/kontrast temada okunabilir; isteğe bağlı not alanı açılıp kapanabilir.
- Yeni oluşturulan notlu siparişte "Siparişin notunu incele" uyarısı; popup yalnızca notu gösterir. Sonradan yapılan değişiklikler gerçek eski/yeni değerlerle gösterilir.
- Okuduğunu onaylamak ağ işlemini beklemez: önce mevcut kalıcı yerel kuyruğa yazılır, pencere kapanır. Mevcut Sync worker onayı daha sonra gönderir.
- Yeni sipariş veya bekleyen düzenleme önce buluta işlenir; sonra tam revizyonun onayı, ardından hazırlama/kolileme ve durum hareketleri sırayla gönderilir. Eski revizyon reddedilirse uyarı yeniden gösterilir.
- Uyarı düğmesinden açılırsa onay yalnız popup'ı kapatır; Sipariş detayı düğmesinden açılırsa onaydan sonra detay açılır.
- Popup'a ait QThread kaldırıldı ve takip ekranında eski widget referansları temizlendi. Bildirilen kapanma hatasının kesin kaynağına ait crash trace sağlanmamıştı.
- ÖNEMLİ: v2.0.32 yeşil kolileme görselleri ve not/yenileme sistemi korunur. Firebase kuralları değişmedi; yeni istemcilerde yerel okundu onayı optimistiktir. Çevrimdışı eski revizyonla yapılan işlemler sunucuda reddedilebilir. Tüm cihazlar aynı sürüme yükseltilmeden kilit garantisi yoktur.
- v2.0.30 kararlı kanalda kalır. Bu paket önce ön sürüm olarak yayımlanır.
