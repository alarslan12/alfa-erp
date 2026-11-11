# ALFACOPYCENTER Suite v2.0.9 · Banner Studio v3.10

- Excel içe aktarma artık **sayfa sayısı boş olan fakat kitap kodu ve kitap adı bulunan** kitapları da kabul eder.
- Sayfa sayısı boş, sıfır veya geçersiz ise kitabın `pages` değeri `null` olur. Kitap katalogda kalır ve grup/set seçiminde gösterilir.
- Kitap adı ya da kodu olmayan yer tutucu satırlar ürün olarak alınmaz.
- Yeni Excel başarılı biçimde yüklendiğinde eski Excel kataloğu ve aktif kitap seçimleri sıfırlanır.
- Kapak arşivi, kayıtlı tasarımlar, marka ayarları ve fiyat alanlarına dokunulmaz.
- Excel'de gerçek ürünler için tekrar eden kitap kodu varsa karışıklığı önlemek üzere içe aktarım reddedilir.
- ERP Katalog / Siparişler bölümleri değiştirilmedi. İstek üzerine otomatik testler çalıştırılmadı.
