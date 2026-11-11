# ALFACOPYCENTER Suite v2.0.7 · Banner Studio v3.8

- Excel içe aktarma sırasında Windows WinError 32 dosya kilidi düzeltildi: openpyxl artık taşınacak geçici dosyayı değil Excel bellekteki kopyasını okuyor.
- Yeni katalog yalnızca tüm kod/isim kontrolleri başarılıysa kaydedilir; başarısızlıkta eski Kitaplar.xlsx korunur.
- Windows geçici indeksleme/dosya kilitleri için sınırlı yeniden deneme ve açıklayıcı hata mesajı eklendi.
- Başlangıçta kayıtlı Excel okunamıyorsa kitap listesinin neden boş olduğunu gösteren mesaj gösterilir; sessizce boş liste bırakılmaz.
- Önceki v3.7 kitap kodu ve kapak eşleştirme düzenlemeleri korunmuştur.
- ALFA ERP Katalog/Siparişler ve veritabanı değiştirilmedi; tasarım arşivi temizlenmedi.
- Otomatik testler kullanıcı isteği gereği çalıştırılmadı. Windows paketleme sonucu GitHub Actions'ta izlenir.
