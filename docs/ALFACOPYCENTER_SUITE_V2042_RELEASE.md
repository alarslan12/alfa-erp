# ALFACOPYCENTER Suite v2.0.42 — Analitik hız ve FlexFlow görünüm düzeltmesi

- Yönetici Analitik ekranı, **Normal Analitik** ve **FlexFlow** olmak üzere iki ana sekme içerir. FlexFlow artık açılır pencere değildir; kendi içinde aktif/havuz/tamamlananlar alt sekmeleri yoktur.
- FlexFlow tek bir ekranda **tüm açık üretim işleri** (aktif + havuz), sayfa sayısı, kişi-saat aralığı, ideal en erken bitiş, mesai marjı, kapasite yük çubukları, süreç süre çizelgeleri ve sipariş iş yükü tablosu gösterir.
- 3 × 45 = 135 sayfa/dk siyah-beyaz; 2 × 15 + 1 × 7,5 = 37,5 sayfa/dk renkli. 1 delme makinesi (300 sayfa için 1–2 dk), elle spiral (5–45 sn/nüsha), kolileme (1–5 dk/sipariş), 2 çalışan ve 07:00–17:00 mesai temel alınır.
- Hazırlandı ve kolilendi işaretleri sadece işin kalan miktarını belirler; geçmişte ölçülmemiş süreler uydurulmaz. Sayfa sayısı bilinmeyen kitaplar görünür biçimde bildirilir. Teorik alt sınır bir teslim garantisi değildir.
- Normal Analitik ilk açılışta gereken veriyi gecikmeli işler. Bulut olaylarından gelen yenilemeler birleştirilir, pencere yeniden boyutlanırken tüm grafik ve tablolar tekrar oluşturulmaz.
- Çizgi grafiklerinde tam sayısal sol eksen, hover halinde parlayan veri noktası/sayısal değer ve tepe noktası işareti bulunur; sol-alt etiketler grafik ekseninden ayrılmıştır.
- **Ödenmeyen ciro**, iadeler ve siparişlerde kayıtlı kargo giderleri düşüldükten sonraki nihai tutardır. Ödenen ve ödenmeyen toplamı aynı net esasla hesaplanır. HTML muhasebe raporu da bu hesabı kullanır.
- İade edilmiş siparişlerin satış cirosu sıfırlanır (iade öncesi tutar istatistiklerde korunur); kargo gideri iade sonrasında da kalır. Önceden kaydedilmiş Türkçe virgüllü tutarlar doğru okunur.
- İade sebebi giriş penceresi ayrı ve açık/koyu temada okunabilir hâle getirildi; beyaz arka plan/beyaz yazı uyumsuzluğu giderildi.
- Kitap başına ciro eklendi; **KİTAP · SAYFA** ile **BASKI TÜRLERİ · SB/RNK** tek gruba alındı. Ödeme kapsama, aktif açık adres kargo istatistiği ve alttaki sipariş tablosu kaldırıldı.
- Personel, Katalog ve Siparişler ekranlarının normal iş akışları, Firebase güvenlik kuralları ve canlı veriler değiştirilmedi. Suite aynı AppId ile yükseltilir; kullanıcı verileri ve Banner Studio arşivi silinmez.

Kurulum adı: ALFACOPYCENTER_Suite_Setup_V2_0_42.exe.

**Ölçüm sınırı:** FlexFlow, manuel hazır/kolilendi işaretlerini ve teorik cihaz hızlarını kullanır. Personel veya cihazların gerçek süre kayıtlarını, mola/arıza/kalite tekrarlarını ölçmez; gösterilen tahmin ve çizelgeler sözleşmesel bitiş saati değildir.
