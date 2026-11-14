# ALFACOPYCENTER Suite v2.0.31 — Sipariş notu ve değişiklik onayı (ön izleme)

- Sipariş oluştururken isteğe bağlı not alanı; boş not için soru veya popup yok.
- Yönetici, havuz/aktif siparişlerin notlarını ve mevcut düzenlenebilir bilgilerini güncelleyebilir.
- Yeni not veya iş alanı/kitap varyantı değiştiğinde sipariş kartı sarı/turuncu uyarı verir. Hazırlama/kolileme sayacı veya normal durum geçişi revizyon üretmez.
- Sipariş detayına veya karttaki uyarıya basınca detaylı eski/yeni değerler, eklenen/çıkarılan kitap kodları, SB/RNK ve miktarlar gösterilir. Kitap kodu hover'ında yerel kapak ve isim görünür.
- Okudum, anladım işaretinden sonra mevcut revizyon bulutta koşullu olarak onaylanır. Onay sipariş/revizyon başına ortaktır, onaylayan cihaz kayıtlıdır. Yeni revizyon yeni onay ister.
- Aktife alma, hazırlama/kolileme ve tamamlama mevcut revizyon okunana kadar yeni istemcide engellenir. Eski kuyruk revizyonu buluta yazılmadan reddedilir; çevrimdışı önbellek anlık olarak eski görünebilir.
- Firebase kuralları değiştirilmedi. Uygulama düzeyi kontroller, eski sürümler veya doğrudan yetkili Firebase istekleri için sunucu kuralı garantisi değildir. Üretimde her cihazda yeni istemci ve gerekiyorsa ayrıca güvenlik kuralı doğrulaması gereklidir.
- v2.0.30 kararlı kanalda kalır; bu paket ön sürümdür. Canlı veritabanı, cihaz kayıtları veya mevcut siparişler dağıtım sırasında değiştirilmez.
