# ALFACOPYCENTER Suite v2.0.36 — Sipariş arşivi ve arayüz düzeltmeleri (ön izleme)

- Tamamlanan sipariş kartları ve kapaklarda hareketli hover rengi kaldırıldı; tamamlanma tiki ve sabit koli rengi korundu.
- Tamamlananlar ve Arşiv ekranı 20'şer kayıtlık önceki/sonraki sayfalara ayrıldı. Son üç takvim günü (bugün ve önceki iki gün) güncel sekmede; eski kayıtlar arşiv görünümünde. Siparişler silinmez ve veritabanında taşınmaz.
- Yönetici, aktif veya tamamlanmış açık adres siparişinin kart menüsünden kargo ücretini ekleyebilir/düzenleyebilir; mevcut yerel kuyruk ve koşullu bulut yazımı kullanılır. Siparişin ilk eşitlemesi tamamlanmış olmalı.
- Analitik'te tüm aktif açık adres kargoları ayrı gösterilir; tamamlananlar tamamlanma tarihine göre mevcut kargo ve kargo sonrası ciro hesaplarına dahil edilir. Böylece çift sayım yapılmaz.
- Renk körlüğü modu ortak tema paletindeki kırmızı/yeşil tonlarını sarı/maviye dönüştürür; özel sipariş/kitap durumları ve analitik çizimleri de uyarlanır. Kitap kapağı görselleri değiştirilmez.
- Sipariş düzenlemede daha görünür ayrı eksi/artı adet düğmeleri. Kitap eklendi/çıkarıldı bildirimlerinde başlığın altında özel kapak önizleme ipucu; diğer bildirimlerde ipucu yok.
- Firebase kuralları ve canlı veriler değiştirilmedi. Yöneticiye özgü yeni işlem istemci ve rol doğrulamasıyla sınırlıdır; doğrudan Firebase istekleri için yeni sunucu kuralı uygulanmadı.
- v2.0.35 kararlı kanalda kalır; v2.0.36 Windows kalite kapısından sonra ön sürüm olarak yayımlanır.
