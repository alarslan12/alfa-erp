# ALFACOPYCENTER Suite v2.0.48 — FlexFlow gerçek tamamlanma / tahmini üretim yükü

## Sorun ve yeni analiz
Önceki gün basılan/hazırlanan kitaplar ertesi gün kolilenip sipariş tamamlanınca mevcut 'Tamamlanan siparişler' grafiğinde toplu kapanma zirveleri oluşabiliyor. **Gerçek tamamlanan sipariş adedi ve resmi tamamlanma tarihleri korunur.** İkinci grafik, üretimin olası tarihsel dağılımını modelleyen alternatif bir istatistik sunar.

- 'Gerçek tamamlanma / vardiyalara dağıtılan iş yükü' çizgi grafiği eklenmiştir.
- Model, tamamlanmış siparişlerdeki SB/RNK sayfa sayıları, 3 siyah-beyaz/3 renkli baskı kapasitesi, tek delme makinesi, iki çalışan, manuel spiral ve kolileme alt sınırlarını kullanır.
- Standart sipariş eşdeğeri, sayfa bilgisi tam olan tamamlanmış siparişlerin son 365 günlük **medyan tahmini minimum iş yükü** ile normalize edilir. Bu bir sipariş adedi değildir.
- Kullanılabilir kaydedilmiş hazırlandı/kolilendi hareketleri öncelikle **gerçekte kaydedildiği güne** atanır. Bilinmeyen hazırlama yükü yalnızca bir önceki güne ait geçerli aktife alma zamanı varsa iki vardiyanın kullanılabilir süresine göre tahmini paylaştırılır. İdeal kapasitenin gün içi alt sınırı aşılması bu tahmini dağılımda ayrıca dikkate alınır.
- Dünün tamamlanan sayısı sıfır, bugünün tamamlanan sayısı 16 olsa bile dünkü hazırlama kayıtları veya önceki gün aktivasyonu varsa yeni tahmini grafik dünkü üretim yükünü gösterebilir; gerçek tamamlanmalar değişmez.
- Kolileme işlemi gerçek tarihi biliniyorsa o güne, bilinmiyorsa tamamlanma gününe atfedilir. Eksik sayfa bilgisi bulunan siparişler üretim eşdeğeri hesabına dahil edilmez ve 'Eksik veri' olarak belirtilir.
- Günlük yorumda kayıtlı vs. tahmini katkı, teorik kapasite uyumsuzluğu ve dünden devreden iş bilgisi ayrılır. CSV/HTML raporlarında aynı ayrım bulunur.

## Bilimsel ve operasyonel sınırlamalar
- **Model dakika** gerçek çalışan dakika, fiziksel cihaz telemetrisi, satış veya ücret değildir.
- Süre alt sınırları teorik varsayımdır; çalışan molaları, iş değiştirme, yazıcı arızası, yeniden baskı ve kayıtsız işlemler bilinmemektedir.
- Geçmiş olay veya aktivasyon verisi bulunmayan tarihlere üretim otomatik olarak taşınmaz. Günlük üretim yükü grafiği kesin tarihsel hakikat olarak yorumlanmamalıdır.
- Geçmiş tek gün filtresi, ertesi gün tamamlanan siparişin kayıtlı/tahmini önceki gün emek payını gösterebilir; ilgili siparişi geçmiş günün **tamamlanan sayısına** eklemez.

## Korunanlar
Canlı Firebase RTDB/Auth/Rules, çalışan yetkileri, yerel JSON/SQLite arşivleri, güncelleme, Siparişler ve Katalog düzeni, finansal hesaplar, mobil web, Banner Studio ve Print Surveillance değişmedi. Suite v2.0.47 üzerine aynı AppId ile yükseltilebilir.

Windows Setup: `ALFACOPYCENTER_Suite_Setup_V2_0_48.exe`.
