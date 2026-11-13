# ALFACOPYCENTER Suite v2.0.24 — GÜVENLİ GERİ DÖNÜŞ

Bu sürüm, 13 Kasım 2026 tarihinde yapılan v2.0.20–v2.0.23 değişikliklerinden kaynaklanan gerilemeler için **v2.0.19'un önceden çalışan uygulama kaynaklarını** yeniden kurar. v2.0.24 yalnızca Windows Suite sürümünü ve yayın/not bilgilerini yükseltir; kapak, Excel, PDF ve Firebase kodu v2.0.19 davranışına geri alınmıştır.

## Geri alınan kod davranışları
- PDF kod eşleştirme, JPEG oluşturma ve otomatik kapak taraması v2.0.19'a döner.
- Kapaklar görünürlük için PDF önbellek manifesti sürümüne bağlı değildir. Diskteki kodla adlandırılmış JPEG kapaklar yeniden gösterilebilir.
- Katalog Excel okuyucu, bulut katalog yükleyicisi, Personel/Yönetici ayar sayfaları ve diğer ERP işleyişi v2.0.19'a döner.
- Yeni sürüm otomatik güncelleyici üzerinden daha büyük sürüm olarak bulunur.
- Katalog ve Siparişler ekranları v2.0.19 görünüm ve işlevleriyle korunur.

## ÖNEMLİ: Sayfa sayıları, veri yedeği
Bu sürüm **Firebase kayıtlarını veya mevcut yerel kullanıcı verilerini değiştirmez**. Eğer Firebase kitabının `page_count` alanı daha önce 0 yapıldıysa, yalnızca kodu geri almak bulut sayfa sayılarını geri getirmez.

1. Kurulumdan önce `%LOCALAPPDATA%\AlfaERP` klasörünün tamamını ve orijinal Excel/PDF klasörlerini kopyalayarak yedekle.
2. Kişisel Firebase hesabını, cihaz eşleştirmesini veya sipariş dosyalarını silme.
3. En son sağlam Excel'deki sayfa değerleriyle yöneticide yükleme önizlemesi yap; yüklemeyi ancak verilerin doğruluğundan ve mevcut yedekten emin olduğunda onayla.
4. Daha önceki Excel aktarımında saklanan yerel `catalog_backups/before_excel_*.json` anlık görüntülerini de koru; kitapların eski sayfalarını barındırabilirler.

**Bu yayın bir kod geri dönüşüdür; mevcut Firebase verilerinin kendiliğinden geri yüklenmesi değildir.** Kaynak PDF klasörü cihaz dışında doğrulanamadığından tüm kapakların doğru eşleştiği garanti edilemez.
