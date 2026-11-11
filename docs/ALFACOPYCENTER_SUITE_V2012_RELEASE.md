# ALFACOPYCENTER Suite v2.0.12 · Banner Studio v3.13

## Kapak üstündeki özel fiyat etiketinin punto düzeltmesi
- Kapak üzerindeki özel fiyat farkı etiketi artık punto kaydırıcısını gerçek yazı büyüklüğüne uygular.
- Önceki çizim kodu arka planı büyütse de tek satırlı dar kutuya sığdırmak için yazıyı yeniden küçültüyordu. Yeni çizim yazı boyutuna öncelik verir, gerektiğinde miktar ile para birimini iki satırda yerleştirir.
- Etiketin arka planı metne göre büyür; çok küçük kitap kapaklarında taşma ve yan kapaklarla çakışma önlenir.
- Tasarımların kaydı, mevcut kapak arşivi, Excel kataloğu ve ERP Katalog/Siparişler bölümleri değiştirilmemiştir.
- Testler kullanıcı tercihi uyarınca çalıştırılmadı. Windows derleme durumu GitHub Actions üzerinden takip edilmelidir.
