# ALFACOPYCENTER Suite v2.0.50 — Fason Sipariş Derleme ve Analitik Yazdırma

## ERP Personel / Yönetici — Siparişi Derle
- Sipariş detayında tam sipariş; kitap kartında tek kitap; aktif takipte birden çok seçili kitap için tek ZIP hazırlar.
- Windows Masaüstüne `Sipariş 76.zip` gibi otomatik kaydeder. Var olan ZIP'in üzerine yazılmaz.
- ZIP'de `Siyah/` ve `Renkli/` klasörleri, rastgele isimli PDF'ler ve sipariş numarası/kodu ile baskı adetlerini içeren `BASKI_TALIMATI.txt` vardır.
- Tekrar kitap baskıları dosya adı ve talimat dosyasında kaç adet basılacağıyla belirtilir.
- Yerel PDF kütüphanesi kullanılır; Firebase'e belge yüklenmez. Eksik/bozuk PDF varsa eksik ZIP yayımlanmaz.
- Kaynak PDF'ler değişmeden bırakılır. Kaynak PDF nesneleri yerine sayfaların 300 DPI görüntülerinden yeni PDF hazırlanır; kaynak belge bilgisi/XMP, gömülü ek, gizli metin, anotasyon ve form gibi yapılar korunmaz.
- Siyah baskı gri tonlama, renkli baskı renkli hazırlanır. Uzun işlemler için arka plan iş parçacığı, ilerleme ve iptal desteği vardır.

## Normal Analitik — HTML Raporu / Yazdır
- HTML muhasebe raporu artık farklı kaydet penceresi açmaz; otomatik Windows Masaüstüne kaydedilir.
- Varsayılan tarayıcıda açılır ve `window.print()` üzerinden yazdırma penceresi tetiklenir. Kullanıcı onayı olmadan yazıcıya çıktı gönderilmez.

## Güvenlik ve kullanım notları
- Raster dönüştürme, görünür sayfa içeriğine yerleştirilmiş filigran, ad, QR kod, ekran görüntüsü veya piksellerdeki gizli veriyi silemez. Fason firmaya göndermeden önce sayfaları gözden geçirin; tam anonimlik garanti değildir.
- PDF metni aranabilir/vektörel olmaz ve 300 DPI çıktılar daha büyük olabilir.
- Kullanıcı arşivleri, yerel PDF kitaplıkları, canlı siparişler, Firebase Authentication/RTDB, cihaz yetkilendirmeleri ve çevrimdışı kuyruk korunur. Firebase Rules ve Hosting değiştirilmez.
- Banner Studio, Mobil Katalog ve Print Surveillance kaynak işlevleri değiştirilmedi; dört bileşen tek Suite Setup ile kurulur.
- Windows CI ve EXE smoke testleri yayın sırasında kontrol edilir; gerçek yazıcı/fason ortamında fiziksel baskı test edilmemiştir.

## Kaynak
- ERP Analitik PR: https://github.com/alarslan12/alfa-erp/pull/22
- ERP Sipariş ZIP PR: https://github.com/alarslan12/alfa-erp/pull/23

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_50.exe`.
