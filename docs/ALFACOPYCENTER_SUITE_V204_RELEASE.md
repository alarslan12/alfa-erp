# ALFACOPYCENTER Suite v2.0.4 · Banner Studio v3.5

## Banner Studio düzeltmeleri
- Tasarım Arşivi grid alanı bağımsız kaydırılır; çok sayıda kayıt olduğunda Düzenle, Görseli indir, Ad ve Sil düğmeleri kart altında erişilebilir kalır.
- Tekli PNG/JPG dışa aktarmada destekleyen Chrome/Edge tarayıcılarında **Farklı Kaydet** penceresi açılır. Dosya adı: **Seri başlığı - Set/ilan adı - Alt başlık**. Özel alt başlık kapalıysa otomatik **N Kitap** kullanılır.
- Arşivden **Görseli indir** işlemi her zaman PNG üretir; eski JPG kayıtlar da yalnız PNG olarak dışa aktarılır.
- Seçilen tasarımları toplu dışa aktarma, destekleyen tarayıcılarda **klasör seçimi** açar ve seçilen klasöre sadece **PNG** dosyalarını koyar. JSON içermez. Klasör seçimi desteklenmiyorsa yalnızca PNG içeren ZIP sunulur.
- Arşivdeki düzenlenebilir proje JSON'ları ve yerel tasarım arşivi **silinmez**; yalnızca dışa aktarma paketinden çıkarılır. Ayrı **JSON yedeği** düğmesi korunur.
- Hızlı alt grup ekleme, önceden girilmiş seri/set/ilan başlığını, alt başlığı ve fiyat ayarlarını artık değiştirmez.

## Kullanım
Chrome veya Edge üzerinde localhost Banner Studio'yu aç; klasör kaydetme izni sorulduğunda seçim yap. İndirme menüsü tarayıcıda desteklenmiyorsa normal indirme klasörü davranışı veya PNG ZIP alternatifi kullanılır.

Mevcut ERP sipariş ve katalog işleyişi değiştirilmedi. Otomatik testler kullanıcı tercihiyle çalıştırılmadı; gerçek Windows kurulumunun sonucu GitHub Actions'ta doğrulanmalıdır.
