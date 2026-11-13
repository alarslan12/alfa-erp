# ALFACOPYCENTER Suite v2.0.22 — PDF Kod Eşleştirme ve Gerçek Hata Raporu

## Düzeltilenler
- 31.pdf, kitap_31.pdf, 31-endodonti.pdf, kod-31-kapak.pdf gibi dosyalardaki açık kitap kodları doğrudan eşleştirilir.
- Seri/cilt sayıları başka kitap kodlarına atanmaz; aynı kodlu birden fazla PDF bulunduğunda rastgele kapak seçilmez.
- PDF ve katalog kitabı adları arasında yüksek güvenilirlikli küçük yazım farkları tolere edilir.
- 31 PDF içeren klasörde 478 katalog kitabının bulunmaması, 478 bozuk PDF olarak yorumlanmaz.
- Gerçek eşleşmeyen PDF dosyaları ve katalogda PDF'si bulunmayan kitaplar ayrı sayılır.
- PDF kapak önbelleği v6'ya çıkarıldı, yatay ilk sayfa −90° dönmeye devam eder.

## Nasıl uygulanır?
Ayarlar → Kitap PDF klasörü → Tara ve kapakları güncelle.

İşlem raporu: `%LOCALAPPDATA%\AlfaERP\alfa_pdf_kapak_tarama_raporu.json`.
PDF'lerin gerçek adları, kodları ve kitap listesi cihazda olduğundan nihai eşleşme burada kontrol edilmelidir.

## Korunanlar
Manuel kapaklar, Firebase sipariş ve katalog verileri, sipariş ekranları, Banner Studio ve Print Center arşivleri korunur.
