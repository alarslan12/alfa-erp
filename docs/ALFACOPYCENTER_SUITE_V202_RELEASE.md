# ALFACOPYCENTER Suite v2.0.2 — Banner Studio & Gardrops

Bu sürüm birleşik Windows kurulumunun önceki v2.0.1 sürümünden uygulama içinden yükseltilmesini sağlar.

## Yenilikler
- **Gardrops fiyatı:** Yeni siparişe yazdığın tutarın %90'ı hesaplanır, kuruşlu sonuç bir üst tam TL'ye yuvarlanır. 555 TL → 500 TL. Dolap ve diğer platformlar değişmez. Brüt tutar ayrıca korunur.
- **ALFA Banner Studio v3.4:** TTS'ye sabit seçimler yerine bütün katalog gruplarını içeren kaydırılabilir seçici, isteğe bağlı serbest alt başlık, logosuz marka alanı ve nötr marka mesajı.
- **Güncelleme Merkezi:** GitHub'daki yayımlanmış kararlı sürümün notları gösterilir. Tek **Güncellemeyi yükle** onayıyla Setup uygulama içine indirilir, SHA-256 kontrolü yapılır, uygulama kapanıp kurulum sihirbazı açılır ve yeniden başlatılır.
- **Kargonomi entegrasyonu kaldırıldı:** API, depo ayarları, alıcı iletişim formu, desi ve Yeni Barkod akışı uygulamaya dahil değildir. Önceki normal sipariş tamamlama mantığı korunur.

## Veri ve kurulum
- Katalog, Siparişler, Firebase eşitleme, analitik ve yazdırma işlevlerinin mevcut çalışma mantığı korunur.
- Eski yerel veriler, siparişler ve kuyruklar kurulum tarafından temizlenmez.
- Güncelleme yalnızca uygulama içinden onay verildiğinde yüklenir. Yönetici kurulum parolası kuralı değişmez.
- Yeni sürümün otomatik bulunması için GitHub'da kararlı v2.0.2 Release ve SHA256SUMS.txt yayımlanmış olmalıdır.

**Doğrulama sınırı:** Derleme iş akışında otomatik testler kullanıcı tercihi nedeniyle çalıştırılmaz. Windows ve gerçek kurulum davranışı ayrıca doğrulanmalıdır.
