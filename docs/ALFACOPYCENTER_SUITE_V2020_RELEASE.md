# ALFACOPYCENTER Suite v2.0.20 — PDF kapak kurtarma

## Düzeltilen sorunlar
- v2.0.19'da +90° yanlış dönen Meditus yatay PDF kapakları artık −90° döner.
- 402 kodlu TUSDATA PRETUS 3 kitabı, TUSDATA PRETUS 3.pdf adına göre bulunabilir.
- PDF başlığındaki 3 gibi cilt/seri numaraları başka kitap kodlarına atanmaz.
- Aynı kitap adına uyan birden fazla PDF varsa rastgele dosya seçilmez.
- Eski yanlış yönlü otomatik JPEG'ler saklanır ama aktif katalogda gösterilmez.
- Firebase Excel kitap kataloğu yenilenince yerel PDF kapakları arka planda taranır.
- Elle yüklenen kapaklara ve sipariş/Firebase verilerine dokunulmaz.

## Kurulum sonrası
1. Suite'i güncelle.
2. Personel veya Yönetici → Ayarlar → Kitap PDF klasörü.
3. PDF klasörünün erişilebilir olduğundan emin ol.
4. Tara ve kapakları güncelle düğmesine bas.
5. Ayarlar'daki eksik/hata sayılarını kontrol et.
6. Ayrıntılı yerel rapor: %LOCALAPPDATA%\AlfaERP\alfa_pdf_kapak_tarama_raporu.json.
7. Eksik kitap PDF dosya adlarını kitap kodu veya eksiksiz kitap adı olarak düzelt.

Not: Kullanıcının gerçek PDF dosyaları bu depoda bulunmadığından cihazında son görsel kontrol gereklidir.
