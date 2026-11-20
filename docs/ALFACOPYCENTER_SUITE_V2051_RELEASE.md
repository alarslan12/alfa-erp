# ALFACOPYCENTER Suite v2.0.51 — Fason ZIP derleme hızlandırma

## ERP Personel / Yönetici — Siparişi Derle
- 300 DPI raster dönüştürme, metadata silme, PDF yeniden oluşturma ve tekrar ZIP sıkıştırma kaldırıldı.
- Kaynak PDF dosyalarının **orijinal baytları** hiç değiştirilmeden ZIP'e eklenir; PDF'nin görsel kalitesi, gömülü metni ve renk içeriği aynı kalır.
- Sadece ZIP içindeki PDF dosya adları rastgeleleştirilir; baskı türüne göre `Siyah/` ve `Renkli/` klasörlerine ayrılır.
- `BASKI_TALIMATI.txt`, sipariş kodu, baskı adetleri, tekli/seçili/tüm sipariş derleme ve Masaüstüne `Sipariş N.zip` adı korunur.
- Hatalı/boş veya eksik kaynak dosyası varsa tamamlanmamış ZIP Masaüstüne kaydedilmez.
- İndirme veya Firebase'e dosya yükleme yapılmaz; kaynaklar yalnızca yerel diskte okunur.

## Gizlilik sınırı
- Dosya adı maskelemesi **PDF içindeki kaynak metadata, yaratıcı adı, notlar, gizli nesneler, sayfa içeriği veya filigranları silmez**. Başka kırtasiyeye göndermeden önce PDF içeriğini kontrol edin.
- Siyah/Renkli klasörü baskı türünü belirtir; kaynak PDF'nin renkleri dönüştürülmez.

## Mevcut Suite
- ERP Analitik HTML raporunun Masaüstüne kaydedilmesi ve yazdırma diyaloğu korunur.
- Firebase Authentication/Realtime Database, siparişler, çevrimdışı kuyruk, cihaz yetkileri ve yerel arşivler değiştirilmez.
- Banner Studio, Mobil Katalog ve Print Surveillance işlevlerinde değişiklik yapılmadı.
- Tek ALFACOPYCENTER Suite Setup ve mevcut uygulama AppId korunur.

## Kaynak
- ERP hızlandırma PR: https://github.com/alarslan12/alfa-erp/pull/25

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_51.exe`.
