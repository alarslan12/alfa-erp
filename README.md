# ALFA ERP V4.32 — Desktop / PySide6

Kitap kataloğu, sipariş havuzu, aktif kitap baskı/kolileme, tamamlanan sipariş arşivi, yerel muhasebe takvimi ve işlem günlüğü.

**Windows:** İlk kurulum `KUR_WINDOWS.bat`; programı başlatma `BASLAT_WINDOWS.bat`. Önce mevcut proje klasörünü ve `%LOCALAPPDATA%\AlfaERP` verilerini yedekleyin.

**Katalog ve aktif siparişler:** V4.25 görünümü ve baskı işlevleri korunur. **Havuz:** büyük Sipariş Detayı / Aktife Al / Sil tuşları; detayda yalnızca kitap grupları ve miktarlar.

**Analitik:** Yerleşik takvimle tek gün veya tarih aralığı seçilir. Sadece **tamamlanan siparişler**, **tamamlandıkları gün** esas alınarak muhasebeleştirilir. Ciro, kargo sonrası ciro, Telafi/Açık Adres gideri, kitap/sayfa ve günlük sipariş eğilimi gösterilir. Seçili dönem **HTML raporu** olarak dışa aktarılır.

**Ödeme günleri:** Sarı tamamlandı, parlak mavi ödendi, soluk mavi sadece aktif sipariş günü. ÖDENDİ/ÖDENMEDİ işaretleri yerel `%LOCALAPPDATA%\AlfaERP\alfa_muhasebe_gunleri.json` dosyasında kalıcı saklanır ve Ayarlar > Yedek kapsamında dışa aktarılır. Ödenmiş günün tamamlanan kayıtları değişirse gün yeniden muhasebe kontrolü gerektirir.

**Ayarlar ⚙:** işlem günlüğü, koyu/açık/kontrast tema, Excel katalog, PDF klasörü ve veri yedeği.

**Sınırlar:** Farklı internet bağlantıları üzerinden çoklu bilgisayar senkronizasyonu henüz yoktur. Bu sürüm yerel veri tutar; Windows için PySide6 gerekir. Tamamlanma tarihi olmayan eski siparişlere sahte tarih atılmaz.

Ayrıntı: `SURUM_NOTLARI_V4_27.md`.

**V4.27 — Analitik görünüm:** İnce çizgiye daralan KPI kutuları sabit, okunabilir 70px yüksekliğe alındı. Seçilen tamamlanma gününe göre 20 sayısal metrik, 4 grafik, en çok tamamlanan kitaplar, platform kırılımı ve HTML raporu sağlanır. 7 gün / 30 gün / Bu ay hızlı takvim seçenekleri. Katalog, Siparişler, ayarlar ve veritabanının kayıt akışı korunur.


### V4.29: Analitik ve tamamlanan sipariş arşivi
Analitik değerler Finans/Ciro, Kargo, Sipariş/İş Günü, Kitap/Sayfa ve SB/RNK başlıklarında sınıflandırılır. 7/30 gün düğmeleri kaldırıldı. Tamamlanan siparişlerde son 5 takvim günü otomatik gösterilir; eski siparişler "Arşivi aç" ile 25’erli yüklenir. Analitik hesapları tüm tamamlanan siparişleri kullanır.


### V4.30 — UI polish
Üst Siparişler işlem düğmeleri ortak şekil, filtre kontrol hizası, kart hover/seçim vurguları ve tema tutarlılığı iyileştirildi. Ayrıntılar `SURUM_NOTLARI_V4_30.md`.


### V4.31 — Sipariş detay ve aksiyon alanları
Sipariş detayı popup'ında sekme alanı başlığı ve açık sekme sayacı, toplu işlem araçlarında ayırt edilebilir panel, kitap baskı kontrollerinde bölüm başlıkları; aktif sipariş kartlarında progress bar ve aksiyonlar için ortak hizalanmış sağ panel. Mevcut işlevler ve veri kaydı korunur.


### V4.32 — Aktif kitap havuzu, temalı tarih listesi ve daha net toplu işlemler
Siparişlere Genel Bakış penceresi artık yalnızca aktif siparişlerin kitaplarını ve baskı adetlerini toplar; havuz ve tamamlanan kayıtlar burada görünmez. Hazırla/Kolile/Geri al toplu işlem düğmeleri daha belirgin, aynı ölçülerde ve hizalıdır. Tarih seç ve sıralama kontrolleri beyaz boş şerit oluşturmayan temalı açılır menü kullanır. Koyu/kremsi açık tema hover ve konturları iyileştirilmiştir.


## V4.34
Açık tema renk paleti katalog ve sipariş ekranlarında kremsi tonlarla yeniden dengelendi.


## V4.35
Açık temada kalan koyu hover, sekme, kargo kodu ve katalog başlıkları düzeltildi. Toplu işlem toolbar'ı eş ölçülere alındı.
