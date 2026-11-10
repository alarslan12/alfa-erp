# ALFACOPYCENTER Suite v2.0.6 · Banner Studio v3.7

## Excel/kod/kapak eşleştirme düzeltmeleri
- Excel'de başlık satırı ilk 40 satır içinde aranır; giriş açıklamaları nedeniyle kitaplar artık gözden kaçmaz.
- Başlıklar Türkçe karakterlere duyarlı biçimde tanınır (Kitap Kodu, Kitap Adı, Kitap Grubu, vb.).
- Sayısal kitap kodları tek biçime alınır: 071, 71.0, 71 -> 71. Aynı kodun farklı satırlarda kullanılması içe aktarma sırasında açık hatadır.
- Eksik kod/ad içeren geçersiz kayıtlar sessizce atlanmaz. Yeni Excel tamamen doğrulanmadan eski Kitaplar.xlsx değiştirilmez.
- Yeni Excel başarıyla yüklendikten sonra seçili afiş kitapları yeni kod/başlıklarla yeniden eşleştirilir; artık bulunmayan eski katalog kayıtları aktif afiş seçiminden çıkarılır. Diğer tasarım ayarları korunur.
- Eski başlangıç/demo kapağı yeni Excel'in kodlarına otomatik bağlanmaz.
- Kapağın dosya adındaki kodu esas alınır; farklı kodlu kapak benzer kitap adına dayanarak yeniden bağlanmaz. Eski yanlış eşleşmeler engellenir.
- Sol katalogda yalnızca ilk 160 satırı gösterme sınırlaması kaldırıldı; tüm kitaplar arama ve grup filtreleriyle erişilebilir.
- Alt grup sırası Excel dosyasındaki ilk görüldüğü sıraya göre korunur.

## Korunanlar
- ALFA ERP Katalog, Siparişler ve mevcut Firebase senkronizasyonu değişmez.
- Yerel tasarım arşivi, kapak dosyaları ve geçmişe ait kaydedilmiş afişler silinmez.
- Banner Studio Ayarlar / Güncelleme Merkezi sürümü artık 3.7, Suite sürümü 2.0.6 görüntüler.
- Testler kullanıcı tercihi doğrultusunda çalıştırılmadı. Windows kurulum ve indirme durumu GitHub Actions sonuçlarına bağlıdır.

## Önemli
Kapakların doğru eşleşmesi için en güvenilir dosya adı `71 - DUSAK Konu ADÇ Cerrahi.png` veya `71.png` biçimindedir. Excel içindeki kod tekrarlı veya eksikse önce Excel düzeltilmelidir; program yanlış katalogla devam etmez.
