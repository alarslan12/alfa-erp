# ALFACOPYCENTER Suite v2.0.5 · Banner Studio v3.6

## Banner Studio arşiv ve indirme düzeltmeleri
- Arşiv kartlarının düzenle/indir/ad değiştir/sil düğmeleri çok sayıda tasarımda da görünür.
- Toplu dışa aktarmada seçilen klasöre yalnızca PNG görselleri kaydedilir. JSON arşivin içinde saklanmaya devam eder ancak dışa aktarılmaz.
- Tekli görsel indirirken destekleyen tarayıcılarda Farklı Kaydet penceresi açılır; dosya adı seri başlığı, ilan/set başlığı ve özel alt başlıktan (yoksa kitap sayısı) oluşur.
- Alt grup seçimi önceden ayarlanmış seri/ilan/alt başlık ve fiyatları değiştirmez.

## Banner Studio Ayarlar → Güncelleme Merkezi
- Banner Studio içinde yeni **Ayarlar** sekmesi, kurulu Suite sürümü, GitHub kararlı sürüm kontrolü, sürüm notları ve Güncellemeyi yükle seçenekleri vardır.
- Aynı ALFACOPYCENTER Suite kurulum dosyası indirilir; indirme ve SHA-256 doğrulaması mevcut ERP güncelleme modülüyle yapılır.
- Güncelleme yalnızca kullanıcı onayıyla başlar. Banner Studio kapanır; Windows kurulum sihirbazı açılır ve sadece Banner Studio bileşeni seçilir, sonra yeniden başlatılır.
- API yalnızca 127.0.0.1 üzerindeki stüdyo web arayüzüne açıktır; güncelleme başlatma rastgele web siteleri tarafından tetiklenemez.
- Bu özellik kurulu v2.0.3 uygulamasında henüz yoktur; v2.0.5 ilk kez yüklenirken ERP Güncelleme Merkezi kullanılabilir.

Arşiv verileri, siparişler ve kapaklar silinmez. Windows kurulumunun başarı sonucu GitHub Actions'ta doğrulanmalıdır. İstenilen şekilde otomatik testler koşulmamıştır.
