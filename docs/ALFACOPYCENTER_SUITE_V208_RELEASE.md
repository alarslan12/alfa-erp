# ALFACOPYCENTER Suite v2.0.8 · Banner Studio v3.9

## Excel içe aktarma
- Excel şablonundaki boş kitap yer tutucuları hata değildir. Yalnızca kitap kodu, kitap adı ve pozitif tam sayı sayfa sayısı bulunan ürün satırları kataloğa aktarılır.
- Boş sayfa sayısı, sıfır, geçersiz sayfa sayısı veya eksik kitap adı içeren satırlar kataloğa ve setlere girmez.
- Gerçek kitap kodlarının yinelenmesi yine engellenir; yanlış ürünün başka bir ürünle karışması önlenir.
- Yeni Excel başarıyla doğrulanıp kaydedildiğinde, **önceki Excel kataloğu tamamen değiştirilir** ve mevcut afişteki eski kitap seçimi temizlenir. Yeni katalogdan set veya kitaplar yeniden seçilir.
- Başlık, fiyat, stil ve marka ayarları korunur; kapak arşivindeki yüklenmiş görseller ve geçmişte kaydedilen afişler silinmez.
- Excel hatalıysa mevcut katalog ve seçimler değişmez.
- Önceki Windows dosya kilidi düzeltmesi korunur.

## Diğer
ERP Katalog/Siparişler, Firebase ve diğer uygulama modülleri değiştirilmedi. Kullanıcı tercihi doğrultusunda testler koşulmadı; Windows paketlemesi Actions üzerinden izlenecektir.
