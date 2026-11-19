# ALFACOPYCENTER Suite v2.0.46 — FlexFlow hareketli tarihler ve günlük değerlendirme

## Modern tarih filtresi
- FlexFlow'daki “Son 7 gün”, “Son 14 gün”, “Son 30 gün” açılır menüsü kaldırıldı.
- Yerine Siparişler'de zaten kullanılan **AlfaTemaliCombo** tasarımında “Tüm hareketli günler” ve yalnızca gerçek üretim hareketi bulunan tarihlerin listesi eklendi.
- “▦ Takvim” düğmesi aynı Siparişler takvimini açar. Tarihlerde kaydedilmiş üretim hareketi vurgulanır. Tek gün seçimi ve **Shift + tık** ile başlangıç/bitiş aralığı desteklenir; “Temizle” filtresiz görünüme döner.
- Dropdown'daki günler kaydedilmiş aktife alma, tamamlanma ve Firebase üzerinden zaten alınmış olay günlüğündeki hazırlama/kolileme hareketlerinden çıkarılır. Kayıtsız geçmiş işlemler uydurulmaz. Yeni Firebase sorgusu veya yazması eklenmez.
- Filtrelenmiş gün veya dönem; günlük istatistikler, saatlik görünüm, çizgi grafikler, günlük/saatlik tablolar, CSV ve HTML raporu için aynı kaynak olur. Tarih aralığının son günü saatlik grafikte gösterilir.
- Filtresiz görünümde son 90 günlük gerçek üretim hareketleri grafiklerde yer alır. Tarih açılır menüsü gerçek kayıtlı günleri listelediği için boş günlerle dolmaz. Tam tarih filtresi 366 güne kadar kullanılabilir.

## En üstte veriye dayalı yorum
- **GÜNLÜK OPERASYON DEĞERLENDİRMESİ** paneli, filtresiz görünümde her zaman bugünün kaydedilmiş verisini özetler. Geçmiş tek bir gün seçilirse o günü, tarih aralığı seçilirse toplam dönemi yorumlar.
- Tamamlanan sipariş, kitap ve sayfa sayıları; kayıtlı hazırlandı/kolilendi hareketleri; önceki üretim günleri ortalaması ve seçilen günün karşılaştırması.
- Şu anki **aktif/havuz siparişler**, baskı bekleyen ve kolilemeye hazır nüshalar, operasyonun öncelikli işi ve mesaiye yetişme riski insanın anlayacağı kısa ifadelerle yazılır.
- Eksik sayfa sayısı varsa tahminin belirsiz olduğu belirtilir. Kayıtlı hazırlandı/kolilendi zaman bilgisi yoksa “0 üretim” denmez, kayıt eksikliği açıklanır.
- Geçmiş tarihin sipariş kuyruğu/mesai durumu geriye dönük uydurulmaz. “Şu an” açık işler güncel kuyruk görüntüsüdür. Mesai 07:00–17:00 ve 2 çalışan varsayımı korunur; tahminler gerçek cihaz/işçilik telemetrisi değildir.
- Aynı yorum CSV/HTML raporlarında bulunur.

## Güvenli yükseltme
Önceki Katalog/Siparişler düzenleri, Firebase kuralları, canlı sipariş kayıtları, ödeme/iade/kargo hesaplamaları ve diğer Suite bileşenleri korunmuştur. Aynı Inno Setup AppId ile mevcut kurulumun üstüne yükseltilir; Firebase veya yerel veriler sıfırlanmaz.

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_46.exe`.
