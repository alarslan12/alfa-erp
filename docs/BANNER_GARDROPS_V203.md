# ALFACOPYCENTER Suite v2.0.3 — Banner Studio + Gardrops

Bu sürümde Kargonomi entegrasyonu tamamen kaldırılmıştır. Kargonomi API bağlantısı, menüsü, gönderi, alıcı/desi ve barkod akışları, gizli token depolama ve keyring bağımlılığı **yoktur**.

## Kalan özellikler
- **Gardrops:** Yeni siparişte 9 haneli kargo kodundan Gardrops otomatik tespit edilir; girilen satış tutarının %90'ı hesaplanır ve sonuç tam TL'ye **yukarı yuvarlanır**. Örneğin 555 TL -> 500 TL net ciro. Diğer platformlarda fiyat değiştirilmez.
- Sipariş ekranında net Gardrops tutarı canlı önizlemede gösterilir.
- **Banner Studio v3.4:** Tüm katalog gruplarından dinamik seçim, gösterilebilir bağımsız alt başlık, logo olmadan marka yazıları korunur.
- Mevcut sipariş açma, hazırlama, kolileme, tamamlama ve eski kargo fişi akışı değiştirilmemiştir.

## Kurulum
1. GitHub Actions'taki **ALFACOPYCENTER Suite v2.0.3 - Banner and Gardrops only** iş akışında başarılı çalışmanın Artifacts bölümünden aday ZIP'i indir.
2. Mevcut `%LOCALAPPDATA%\AlfaERP` verilerini yedekle.
3. ZIP'i çıkarıp `ALFACOPYCENTER_Suite_Setup_V2_0_3.exe` dosyasını çalıştır.
4. Kargo fişi ve sipariş işlemleri eski düzeninde devam eder, Kargonomi hesabı gerekmez.

Bu sürüm kaynak kodunda hazırlanmıştır; canlı Windows GUI testi yapılmamıştır. Paket yalnızca GitHub Actions iş akışı başarıyla bittiğinde kullanılabilir.
