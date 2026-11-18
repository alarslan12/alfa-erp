# ALFACOPYCENTER Suite v2.0.45 — FlexFlow üretim yönetim paneli

Bu sürüm FlexFlow'u teknik mühendislik ekranı olmaktan çıkarıp yönetici ve personelin kolayca anlayabileceği bir operasyon analitiğine dönüştürür. **Personel sürümüne yetkisiz analitik erişimi açılmaz**; Yönetici > Analitik > FlexFlow altında çalışır.

## Görünen göstergeler

- **Bugün tamamlanan:** Tamamlanma zaman damgası bulunan sipariş adedi.
- **Bugün hazırlanan / kolilenen:** Buluttaki işlem günlüğünde kayıtlı pozitif/negatif hareketlerin net kitap nüshası ve hareket görülen farklı sipariş adedi. Tarihsel olay kaydı yoksa *Kayıt yok*.
- **Açık sipariş:** Aktif + havuz ayrı belirtilir; açık işte baskı bekleyen, kolilemeye hazır ve kolilenmiş nüsha dağılımı.
- **Tamamlama temposu:** 07.00–17.00 planlı vardiyasının geçen saati başına o gün tamamlanan sipariş sayısı. Personelin fiilen çalıştığı saat iddiası değildir.
- **Ortalama karşılaştırma:** Seçili 7/14/30 günlük pencerenin bugünden önceki, sipariş tamamlanan günlerindeki ortalama saatlik tempo ile bugünkü kıyas. Tarihsel temel yoksa yüzdelik karşılaştırma uydurulmaz.
- **Mesaiye yetişme durumu:** Sabit işletme cihaz ve işçilik varsayımlarından üretilen, herkesin anlayacağı metinsel kapasite tahmini. Katsayılar ve ham tahmini dakika kartları gizlidir.

## Grafikler ve raporlar

- Günlük tamamlanan sipariş grafiği; günlere göre kaydedilmiş hazırlanma ve kolileme nüshası grafiği.
- Kullanıcının seçtiği gün için saat saat aktife alınan / tamamlanan sipariş grafiği ve hazırlanma / kolileme hareketleri tablosu.
- Günlük üretim çizelgesi: sipariş, kitap, sayfa ve gerçek olay günlüğü bulunduğunda hazırlanma/kolileme.
- Yönetici ekranından **CSV** ve yazdırılabilir **HTML** raporu indirme.

## Veri doğruluğu ve altyapı

- Firebase mevcut sipariş olaylarını `event_log` içinde saklıyor. Yeni bir ağ okuma isteği yapılmadan, zaten gelen sipariş anlık görüntüsünden son 90 günün yalnız tarih/işlem/adet özeti ayrıştırılır.
- Operasyon tarihçesi yerel kullanıcı veri klasöründe küçük bir `alfa_flexflow_olaylari.json` önbelleğinde saklanır, ayrı müşteri adı/adres/telefon verileri çoğaltılmaz.
- Eski olay günlüğü yoksa çalışanların o saatte ne yaptığı **tahmin edilerek doldurulmaz**. Geçmiş tamamlanma/aktife alınma sayıları yalnız kaydedilmiş zaman damgalarından gelir.
- İşlem geri almaları net hareketten düşülür. Kolilenen nüsha ile tamamen bitmiş sipariş birbirine karıştırılmaz.
- FlexFlow kullanıcı tarafından erişilen tek bütünleşik paneldir; ayrı aktif/havuz/tamamlananlar popup/alt sekmesi yaratılmaz.
- Sabit arka plan varsayımları: 3×45 SB, 2×15+1×7,5 RNK, tek delme, manuel spiral ve kolileme, iki çalışan, 07.00–17.00. **Bunlar ölçülmüş cihaz/verimlilik verisi değildir.**
- Katalog, Siparişler, Normal Analitik, iade/kargo muhasebesi, Firebase erişim kuralları ve sipariş kayıtları değiştirilmez.

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_45.exe`. Mevcut Suite yükseltmesiyle kurulur; veritabanı sıfırlanmaz.
