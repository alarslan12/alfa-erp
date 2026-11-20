## [v2.0.50] — 2026-11-21

- ERP Personel/Yönetici Sipariş detaylarına **Siparişi Derle** eklendi. Tam sipariş, tek kitap veya seçili kitaplar bir ZIP olarak Windows Masaüstüne kaydedilir.
- Yerel PDF kaynakları yeniden rasterize edilerek 300 DPI yeni PDF'lere dönüştürülür; kaynak metadata, gizli metin, ekler ve PDF nesneleri aktarılmaz. SB gri tonlama, RNK renkli olarak ayrı klasörlerde hazırlanır.
- PDF'ler rastgele adlarla kaydedilir; birden fazla baskı adedi dosya adında ve `BASKI_TALIMATI.txt` içinde belirtilir. Eksik/bozuk PDF için tamamlanmamış ZIP yayınlanmaz; orijinal belgeler korunur.
- Normal Analitik HTML raporu Masaüstüne otomatik kaydedilir ve tarayıcı yazdırma penceresi tetiklenir.
- Belgedeki görsel filigranlar/anlatımsal kişisel bilgiler görüntüde kalabilir. PDF dönüştürme çevrimdışı yapılır; Firebase, yerel geçmiş, cihazlar ve diğer Suite uygulamaları değiştirilmez.
- Kaynak PR'lar: #22 ve #23. Tek ortak Windows Suite Setup ve sürüm kanalı korunur.

## [v2.0.49] — 2026-11-20

- Banner Studio: Excel/kapak dosyaları ve JSON yedeği Ayarlar → Uygulama Yönetimi'ne taşındı.
- Tek Dışa Aktar penceresinde PNG, JPG ve A4 PDF; Standart/HD/Ultra HD; Masaüstüne doğrudan kayıt veya dosya konumu seçimi sunuldu.
- Afiş dosyaları bütün arşivin doğal A–Z sırası ve kayıt adıyla, ör. `0001_TasarimAdi.png`, numaralandırılır; toplu PNG indirmeleri de aynı sırayı korur.
- Swap iptal, kare kırpma, proje aç ve ayrı JPG/PNG butonları kaldırıldı.
- Tasarım dilleri Vintage Koleksiyon / Minimal Premium; kapak dizilimleri Akıllı / Dengeli Sıralar seçeneklerine indirildi. Kapak ölçeği en çok %100.
- Varsayılan fiyat farkı rozeti ve kapak üstü katalog kodları kaldırıldı; kitaba özel etiketler sağ tıkla düzenlenir, fiyat etiketi tek satırda kalır.
- Uygulamanın sol üstüne ALFACOPYCENTER logosu yerleştirildi.
- Yerel tasarım/kapak arşivi, Firebase, ERP ve Print Surveillance veri ve işlevleri korunur.

## [v2.0.48] — 2026-11-20

- FlexFlow'da gerçek tamamlanma sayıları değiştirilmeden ayrıca iki vardiya arasında dağıtılan tahmini standart üretim yükü grafiği eklendi.
- SB/RNK baskı, delme, manuel spiral ve kolileme kapasitesinden teorik dakika yükü oluşturulur. Tamamlanmış siparişlerin medyan iş yükü referans alınarak standart sipariş eşdeğeri hesaplanır.
- Kaydedilmiş hazırlandı/kolilendi olayları gerçek gününe bağlanır. Kaydı olmayan hazırlama aşaması, yalnız bir önceki gün aktivasyonu kayıtlıysa iki vardiyanın mesai süreleri ve ideal paralel kapasite varsayımıyla tahmini bölünür.
- Ertesi gün toplu tamamlanma zirvelerinde kapasite uyumsuzluğu ve olası devreden iş günlük değerlendirmede işaretlenir; gerçek çalışma saati veya geçmiş işlem iddiasında bulunulmaz.
- Günlük tablolar, CSV ve HTML raporları üretim eşdeğerini, veri eksiğini ve dünden devreden model dakikalarını açıkça ayırır.
- Katalog/Siparişler, Firebase kuralları, muhasebe, Banner Studio, mobil katalog ve Print Surveillance verileri korunur.

## [v2.0.47] — 2026-11-20

- Banner Studio Tasarım Arşivi'nde “Düzenle” ile açılan tasarımın kimliği korunur; “Değişiklikleri Kaydet” mevcut kaydın üzerine yazar, kopya üretmez.
- Ayrı tasarım oluşturmak için “Farklı Kaydet” seçeneği eklendi. Yeni kayıtta isim çakışırsa eski tasarımın üzerine yazma onayı istenir.
- PNG/JPG indirmeleri düzenlenen tasarımın kaydını günceller; kare önizleme orijinal arşiv görselini değiştirmez.
- Arşiv tarihleri kayıtlı UTC verisi değiştirilmeden Europe/Istanbul saat diliminde, Türkçe gün/ay/yıl ve saat olarak gösterilir.
- Yerel arşiv, kapaklar, Excel katalogu, diğer Suite bileşenlerinin iş akışları ve Firebase verileri korunur.

## [v2.0.46] — 2026-11-19

- FlexFlow'un Son 7/14/30 gün QComboBox'ı kaldırıldı. Yerine Siparişler'deki `AlfaTemaliCombo` ile gerçek üretim hareketi (aktife alınma, tamamlanma, kayıtlı hazırlama/kolileme) bulunan gün listesi geldi.
- Aynı `TarihPopup` bileşeni üzerinden tek gün veya Shift+tık tarih aralığı seçilebiliyor. Gün seçimi saatlik/günlük metrikleri, grafik ve tabloları, CSV/HTML dışa aktarımı etkiliyor.
- FlexFlow en üstünde seçili tarihin gerçek tamamlanan sipariş/kitap/sayfa rakamları, kayıtlı ilerlemeler, geçmiş üretim günü ortalaması, güncel açık işler ve operasyon önceliği/riskinin yer aldığı değerlendirme paneli eklendi.
- Geçmiş tarih verileri ile **şu anki** aktif/havuz kuyruğu ayrı tanımlanır; eksik hareket ve sayfa kayıtları asla ölçülmüş sıfırmış gibi gösterilmez.
- Küresel görünümde grafikler yalnız hareketli günleri, günlük tablolar yalnız hareket kaydı bulunan günleri listeler. Veri okuma Firebase'de ek sorgu oluşturmaz.
- Katalog/Siparişler, Firebase güvenlik kuralları ve mevcut ödeme/iade/kargo hesaplamaları değiştirilmedi.

## [v2.0.45] — 2026-11-18

- FlexFlow baştan operasyonel yönetim paneline dönüştürüldü; makine hızı/delme/spiral katsayıları yalnız hesaplama çekirdeğinde kaldı.
- Bugün tamamlanan sipariş, gerçek zaman damgalı hazırlama/kolileme hareketleri (nüsha/sipariş), açık iş sayısı ve vardiya saatine göre tamamlanma temposu kartları.
- Son 7/14/30 gün çizgi grafikleri, seçilen günün saatlik aktife alınan/tamamlanan sayıları, hazırlanma/kolileme hareketleri ve günlük rapor tablosu.
- Önceki üretim günlerinin saatlik ortalamasına göre tempo değişimi; keyfî 0-1 verimlilik skoru yok.
- Buluttaki mevcut işlem günlüklerinden yalnız anonimleştirilmiş işlem/adet/tarih özetleri aynı senkronizasyonda alınır; ek Firebase okuma yok. Yerel, küçük bir 90 günlük olay özeti çevrimdışı kullanım için saklanır.
- Saatlik olay geçmişi olmayan günler 'Kayıt yok' olarak gösterilir, geçmişe dönük uydurma çalışma saatleri üretilmez.
- CSV ve HTML rapor dışa aktarımı eklendi; Katalog/Siparişler, Normal Analitik, iade/kargo muhasebesi ve Firebase Rules değişmedi.

## [v2.0.44] — 2026-11-18

- Kullanıcı tarafından onaylanan Analitik tasarımına göre grafikler ve kart yerleşimi düzenlendi.
- Grafikte QPainter'ın aktif dolgu fırçası nedeniyle oluşan üçgen alanlar giderildi: çizgiler yalnızca kontur ve hafif nokta işaretleriyle çizilir.
- Sol Y ekseni sayısal etiketleri geri getirildi; veri noktasının gerçek tarihi ve değeri sadece hover'da gösterilir.
- Bulut durumu araç ipucunun ana pencereye verilmesi kaldırıldı; artık yalnız bağlantı göstergesinde, grafiklerin hover ipucunu örtmez.
- Platforma göre gelir donut grafiği bir grafik kartı genişliğinde; yanında gerçek verilerle Net Ciro, Basılan Sayfa, Kitap Adedi, SB/RNK özet göstergeleri düzenlendi.
- Hayali büyüme yüzdesi eklenmedi. Katalog, Siparişler, FlexFlow ve Firebase/finans modeli değiştirilmedi.

## [v2.0.43] — 2026-11-18

- Normal Analitik'e satış platformlarının iade sonrası ciro yüzdesini gösteren interaktif halka (pasta) grafiği eklendi. Hover'da platform adı, tutar ve yüzde; yanında renkli açıklama listesi.
- Gelir payı hesabı sipariş adedini değil gerçek satış cirosunu kullanır; iade edilen satışları ve sıfır cirolu telafi siparişlerini dilimlere katmaz. Kargo, ayrı finans kartlarında düşülmeye devam eder.
- Çizgi grafiklerinin altı doldurulmaz; sol dikey eksendeki sabit sayısal etiketler ve tepeye yapıştırılmış sürekli değerler kaldırıldı.
- Grafikteki veri noktalarının sayısal değerleri sadece fareyle üzerine gelince gösterilir.
- Normal Analitik/FlexFlow yerleşimi, siparişler, kargo ve iade muhasebesi korunur.

## [v2.0.42] — 2026-11-18

- Analitik artık **Normal Analitik** ve tek, popup olmayan **FlexFlow** sayfası olarak iki sekme içerir. Kapasite grafikleri, zaman aşamaları, sayısal kartlar ve iş yükü tablosu eklenmiştir.
- Sayfa açılışı/yenilemeleri gecikmeli birleştirilir; grafikler her boyut değişiminde tekrar kurulmaz.
- Çizgi grafiklerinin sayısal sol ekseni, hover noktaları ve tepe işaretleri iyileştirildi.
- Ödenmeyen ciro, iade ve kaydedilmiş kargo giderleri düşüldükten sonraki tutarı gösterir; HTML raporu aynı yöntemi kullanır.
- İade sebebi dialogu açık/koyu temalarda okunabilir; kitap başına ciro eklenmiş, kitap/sayfa/SB/RNK istatistikleri birleştirilmiştir.
- İstenmeyen ödeme kapsama, aktif açık adres kargo göstergesi ve alt sipariş tablosu kaldırılmıştır.
- Katalog, Siparişler ve Firebase güvenlik kuralları korunmuştur.

## [v2.0.41] — 2026-11-18

- Yönetici → Analitik → Verimlilik (FlexFlow): gerçek cihaz hızları, delme, elle spiralleme ve kolileme süreleriyle sayısal üretim kapasitesi.
- Aktif üretim, havuz ve tamamlanan dönem için baskı sayfaları, standart manuel kişi-saatleri, darboğaz ve vardiya risk değerlendirmesi.
- Sayfa sayısı bilinmeyen kitaplarda eksik tahmin açıkça gösterilir. Bu rakamlar yazıcı telemetrisi veya ölçülmüş personel verimliliği değildir.
- Personel, Katalog, Siparişler, Firebase veri modeli ve güvenlik kuralları değiştirilmedi; Suite yükseltme yoluyla kurulur.

## [v2.0.40] — 2026-11-17

- Banner Studio: son tarayıcı sekmesi kapatıldığında güvenli server shutdown; yeniden yükleme ve birden fazla sekme destekli oturum sayacı.
- Windows tek-örnek mutex; ikinci çalıştırma mevcut stüdyoyu açar, yeni arka plan EXE'si bırakmaz.
- Çökmüş tarayıcı ve hiç açılamamış pencere için zaman aşımıyla kendini kapatma; localhost origin/host kontrolleri.
- Tasarım arşivi, siparişler, Firebase ve diğer Suite bileşenleri değişmedi.

## [v2.0.39] — 2026-11-17

- Banner Studio Tasarım Arşivi: anlık Türkçe uyumlu arama, filtreli seçim, sonuç sayacı, silme/yeniden adlandırmada konum koruma.
- Yönetici Tamamlananlar > İade Edildi: zorunlu iade sebebi, düzenleme, sipariş kartı altında açıklama; Firebase owner-only senkronizasyon.
- Personel/Yönetici: bulut yenileme sinyalleri birleştirildi, gizli sekmelerin sipariş kartları gereksiz yenilenmiyor.
- Yerel kayıt ve Firebase güvenlik kuralları, dört uygulamalı tek Setup, kargo/analitik ve önceki sürüm özellikleri korunur.

# ALFA ERP · Sürüm Geçmişi

## [v2.0.38] — Kargo takibi ve iade yönetimi

- Tamamlanan siparişlerde Yönetici iade işareti, ayrı iade listesi, kargo takibi ve iade sonrası muhasebe.

## [v2.0.37] — 2026-11-15

- Telafi siparişleri kartında 0 TL yerine TELAFİ SİPARİŞ etiketi; satış cirosu 0 TL olarak korunur.
- Normal siparişlerin ciro etiketi, Firebase ve muhasebe işleyişi değişmez.

## [v2.0.36] — 2026-11-15 (ön izleme)

- Tamamlanan siparişlerde 20 kayıtlık sayfalar, üç takvim günü ve arşiv ayrımı.
- Statik tamamlanma görünümü ve kapak tikleri.
- Açık adres kargo gideri düzenleme, analitik yansıması.
- Renk körlüğü paleti, adet düğmeleri ve kitap değişikliği ipucu.

## [v2.0.35] — Renk körlüğü modu (ön izleme)

- Personel ve Yönetici için temadan bağımsız yüksek görünürlük ayarı.
- Kolileme/tamamlanma cyan, uyarılar ve hazırlama sarı; güçlü kenar ve hover.
- Önceki işlevler ve Firebase kuralları korunur.

## [v2.0.34] — 2026-11-14 (ön izleme)

- Aktif siparişlerde kalan kitap, basılacak kitap/sayfa ve kolilemeye hazır kitap göstergeleri.
- Toplam adet, SB/RNK, koli ilerlemesi, sayfa ve ciro düzenli, uyarlanabilir kartlarda.
- Üretim toplamları tüm aktif siparişleri kapsar; filtre sonucu ayrıca gösterilir.
- Önceki işlevler ve Firebase kuralları korunur.

## [v2.0.33] — 2026-11-14 (ön izleme)

- Not alanı tema uyumu; ilk not ile gerçek sipariş güncellemesi ayrımı.
- Kalıcı yerel okundu kuyruğu, revizyon doğrulaması ve ayrı tıklama akışları.
- Popup'a bağlı ağ işçisi kaldırıldı. Yeşil koli kartları ve Firebase kuralları korundu.

## [v2.0.32] — 2026-11-14 (ön izleme)

- Yalnız tüm kopyaları kolilenmiş kitaplara yarı şeffaf yeşil kart ve yeşil hover.
- Genel bakış ve açık detay kartları koli güncellemelerine göre yenilenir.
- v2.0.31 işlevleri ve Firebase kuralları korunur.

## [v2.0.31] — 2026-11-14 (ön izleme)

- Opsiyonel sipariş notları, Yönetici düzenleme alanı ve revizyon bazlı okundu bildirimi.
- Kart uyarısı; kitap değişiklikleri eski/yeni adetleriyle, kapak hover önizlemesiyle sunulur.
- Hazırlama/kolileme ve onay işlemleri okunmamış revizyonlarda uygulama düzeyinde kilitlenir.
- Firebase güvenlik kuralları değiştirilmedi. v2.0.30 kararlı kullanımda kalır.

## [v2.0.30] — 2026-11-14

- v2.0.28 tabanına dönüş; v2.0.29 kargo fişi iptal.
- Güncelleme indirme ve ilerleme olayları optimize edildi.
- Değişmeyen bildirim durumunun gereksiz yerel yazımı kaldırıldı.
- Firebase, katalog ve sipariş işlevleri korunur.

## [v2.0.29] — İptal

- Kargo fişi güncellemesi üretimde kullanılmamalıdır.

## [v2.0.28] — 2026-11-14

- Sipariş kapaklarında siyah toplam adet rozeti kaldırıldı; yalnızca SB/RNK etiketleri gösterilir.
- Personel ve Yönetici ortak kart bileşeni güncellendi.
- Katalog araması ve diğer işlevler korunur.


## [v2.0.27] — 2026-11-14

- Aktif sipariş ve havuz kapaklarında toplam adet ve SB/RNK etiketleri geri getirildi.
- Tek nüsha ve dar kapaklarda etiketler uyarlanır.
- Katalogda seri numarası ve kitap kodu ayrıştırılır; TUSDATA 24, 24 TUSDATA ve TUS 24 aramaları desteklenir.
- Personel ve Yönetici ortak kodu güncellendi.
- PDF, kapak önbelleği ve Firebase işleyişi korunur.


## [v2.0.26] — 2026-11-14

- TUSDATA Konu kitaplarının PDF adlarında kelime sırası ve Cilt 1/II farkları desteklendi.
- Seri, ders ve cilt numarası korunarak yanlış kapak eşleşmesi önlenir.
- Gerçekte eşleşmeyen PDF adları ayrıca raporlanır; katalogda PDF'si olmayan kitaplar işleme hatası sayılmaz.
- Sayfa sayısı olmayan kitaplar Katalog'da varsayılan gizlidir. İlk açılış ve Personel/Yönetici tercihleri düzeltilmiştir.
- Firebase kitap/siparişleri, çalışan kapak önbelleği ve manuel kapaklar korunur.


## [v2.0.25] — 2026-11-13

- DUSDATA 33 (katalog 117–130) ve DENTTEST (131–136) için benzersiz tam PDF adı eşleştirmesi.
- Kitap kodu yerine seri/cilt numarası yanlışlıkla eşleşmez; manuel ve mevcut kodlu kapaklar korunur.
- Sayfa bilgisi olmayan kitapları göster/gizle tercihi eklendi; varsayılan açık, sadece katalog görüntüsünü etkiler.
- Personel/Yönetici ortak kodu güncellendi; Firebase ve Excel verisi değişmez.


## [v2.0.24] — 2026-11-13

- v2.0.20–v2.0.23 kapak/Excel/PDF gerilemelerini geri alır; v2.0.19 çalışan koduna döner.
- Kapak JPEG'leri tekrar görünür (eski manifest filtrelemesi kaldırılmıştır).
- Firebase/Excel sayfa sayılarının daha önce değiştirilmesi otomatik geri alınmaz; veriler korunur.
- Kullanıcı verileri, siparişler, envanter ve cihaz yetkileri silinmez.
- Windows Suite sürüm numarası v2.0.24 olarak artırılır.


## [v2.0.24] — 2026-11-13

- Analitik'te en önemli dört rakam (Toplam Ciro, Kargo Sonrası
  Ciro, Ödenen Ciro, Ödenmeyen Ciro) belirgin ve açıklamalı tek finans
  panelinde toplandı; küçük ortalama/verimlilik KPI'ları ayrı gruba geçti.
- Ödenen/ödenmeyen tutarların müşteri bazlı banka tahsilatı değil,
  **Ödendi** işaretlenmiş tamamlanma günleriyle ilişkili olduğu açıklanıyor.
- Telafi siparişlerinde yeni kayıt ve düzenleme sırasında ciro zorunlu
  olarak sıfır; fiyat alanı gösterilmiyor. Eski yanlış telafi tutarları
  muhasebe raporu ve analitikte satış cirosu olarak sayılmıyor.
- Telafi ve açık adres kargoları tamamlanırken ayrı sorulmaya devam
  ediyor, genel kargo giderine bir kez eklenip cirodan düşülüyor.
- Kargo sonrası ciro **net kâr değildir**; formül ekranda açıklandı.
- Yatay PDF kapaklar artık +90° döndürülür; yeni otomatik kapak
  önbelleği mevcut manuel kapakları korur.
- Kitaplara Genel Bakış seçimlerinde yeni temalı açılır menü kullanılır;
  alttaki beyaz Qt listesi/şerit sorunu giderildi.
- Firebase, sipariş ve kullanıcı dosyaları, dört bileşenli Suite,
  Windows bildirim ajanı ve ortak Güncelleme Merkezi korunur.


## [v2.0.18] — 2026-11-13

- Sipariş grupları sayısal kitap koduna göre, veriyi değiştirmeden sıralanır.
- Sipariş takibi hazırlanmayanlar/kolilenmeyenler tek pillbox içinde ayrı filtrelenir.
- Sipariş sekme çubuğu yatay taşmayı kaydırır; sekmeler ayrı pencereye
  sürüklenebilir, geri sürüklenebilir veya 'Sekmeye geri al' ile kenetlenir.
- Katalog kartı başlık yüksekliği kısaldı, iki satırlı ad korundu;
  SB ve RNK sayaçları 27 piksele büyütüldü, ortadaki çizgi kaldırıldı.
- Dolap kodlarında son dört rakam ayrı blokta gösterilir.
- Sipariş bildirici Windows oturum açılışında zamanlanmış görev olarak
  başlar; Personel penceresi kapalıyken de görev çalışmaya devam eder.
- Doğal Windows sesleri ve isteğe bağlı şifreli ElevenLabs A/B uyarıları.
- Yatay PDF ilk sayfası 270 derece döndürülerek kapak olarak kaydedilir.
- Firebase, mevcut siparişler, ayrı yönetici yetkileri ve Suite bileşenleri korunur.


## [v2.0.17] — 2026-11-13

- Firebase kitap kodları Excel'deki benzersiz kodla eşleşir;
  eski 508/509/510 TIPDEMY kaymaları giderilebilecek şekilde düzeltildi.
- Buluta katalog yazmadan önce yedek, yazdıktan sonra aktif kitap
  ve mobil katalog readback doğrulaması yapılıyor.
- Sayfa sayıları yeni Personel/Yönetici siparişlerinde Firebase anlık
  görüntülerine ekleniyor. Eski 0 sayfalı görüntüler doğru katalog
  üzerinden toparlanıyor.
- Firebase katalog revizyonu sonrası mobil sipariş kataloğu önbelleği
  ve sipariş sayfa toplamları tazeleniyor.
- Cloud Shell kuru çalışma/fark kontrolü, operatör onaylı veri onarma.
- v2.0.16 Analitik PIN NativeCrash riskine karşı Qt iş parçacığı
  düzeltmesi ve dört bileşenli Suite korunuyor.
- Sipariş, cihaz yetkisi ve arşivler silinmiyor.


## [v2.0.16] — 2026-11-13

- Personel PIN doğrulama iş parçacığı tamamlandığında arayüze
  Qt GUI-thread slotları üzerinden dönülüyor; pencere ve thread kapanış
  sırasındaki yarış durumu önleniyor.
- Analitik ekranında yeniden boyutlandırma sırasında reentrant rapor
  inşasına karşı koruma eklendi.
- PIN doğrulaması başarılı Personel/Analitik açılışı ve grafik
  yeniden boyutlandırma Windows kalite kontrolüne dahil edildi.
- Firebase oturumları, siparişler, Suite kurulum şifresi ve diğer dört
  bileşenin dağıtım düzeni değişmedi.


## [v2.0.15] — 2026-11-13

- **Duyurular / Güncelleme Merkezi:** Personel ve Yönetici sürümlerinin
  önceki v1.x ve v2.x revizyon notları internet olmadan da okunabiliyor.
- **Personel Excel:** Ayarlar → Excel Katalog; onaylı Firebase staff/owner
  cihazından ortak kitap kataloğuna kullanıcı onaylı Excel güncellemesi.
- **Yönetici cihazları:** Aktif cihazlar önde, pasifler gizli; iptal edilen
  cihazların eski üyeliklerini kalıcı temizleme (owner onayı gerekir).
- **Yönetici Hata Merkezi:** Seçili hata raporunu silme ve yalnız incelenmiş
  raporları toplu temizleme; her iki işlem onaylıdır.
- **Firebase Security Rules:** Onaylı staff için kitap katalog güncellemesi,
  owner için iptal edilen cihaz ve hata onay kayıtlarını silme izni.
  GitHub değişikliği tek başına canlı Rules deploy etmez.
- Mevcut Suite Setup, owner kurulum parolası, sipariş kuyruğu,
  sipariş/katalog ekran görünümü, Banner/Print arşivleri korunur.


## [v1.1.1] — 2026-11-06

Güncelleme Merkezi güvenilirlik düzeltmesi · Tek Windows kurulum paketi.

- **Ana pencere kapanışı:** Güncelleme komutu modal pencerenin içinden
  çağrılsa da gerçek Yönetici/Personel ana penceresini bulur ve
  güncellemeden önce kapatır. Windows kurulum yardımcısı eski EXE açıkken
  üzerine yazmaya çalışmaz.
- **Bekleyen sipariş güvenliği:** Güncelleme Duyurular popup'ı içinden
  açıldığında bile ana uygulamanın gerçek bekleyen bulut işlemleri
  denetlenir; eşitleme sürüyorsa güncelleme engellenir.
- **Yeniden başlatma:** Kurulum başarıyla bitince doğru Personel/Yönetici
  EXE'si yalnızca bir kez açılır. Yönetici kurulum parolası geçerlidir.
- **Sorun raporu:** Kurulum yardımcısının bekleme, SHA-256, Windows
  yükleme ve yeniden başlatma aşamaları yerel durum dosyasına yazılır.
  Hata oluşursa sebep Güncelleme Merkezi'nin sonraki açılışında gösterilir.
  Tanı kayıtları Firebase'e yüklenmez.
- **Geçiş notu:** v1.0 ve v1.1'deki güncelleyici bu hatayı içerdiği
  için **v1.1.1 ilk kez GitHub'ın resmî Setup.exe dosyasından manuel
  kurulmalıdır**. Sonraki v1.x güncellemeleri uygulama içinden yapılabilir.
- Siparişler, envanter, maliyet geçmişi, Firebase Rules ve cihaz
  kimlikleri değiştirilmez. Otomatik işlev testleri çalıştırılmadı;
  Windows derleme, paketleme ve SHA-256 doğrulaması uygulanır.


## [v1.1.0] — 2026-11-05

İlk resmi güncelleme · Firebase Realtime Database · Windows 11 · tek Setup.exe.

### Envanter ve muhasebe
- **Yönetici satış iptali:** Satış analitiğinde ilgili satış seçilip gerekçe girilir.
  Firebase'de tek ETag kontrollü ürün güncellemesi orijinal satın alma
  partisinin stokunu geri yükler. Satış kaydı silinmez; `cancelled_at`,
  `cancelled_by` ve `cancel_reason` ile korunur. Tekrar iptal stokları
  iki defa artırmaz.
- **Katalog arşivleme:** Ürünler etkin katalogdan kaldırılıp daha sonra
  geri getirilebilir. Satış geçmişi, stok ve alış partileri silinmez.
- Satış ekranı bölünmüş pillbox/özet formu; açık/koyu/kontrast renkleri.
- İptal edilen satışlar net satış adet, ciro, brüt kâr ve grafiklerden
  çıkarılır; geçmiş tablosunda iptal kaydı görünür.
- Eski bağımsız `inventory/sales` göç kayıtları, partiyle güvenli bağ
  doğrulanamadığı için otomatik iptale açılmaz; manuel inceleme gerekir.

### Sipariş ve eşitleme
- Sipariş silindikten sonra henüz ulaşmamış eski Firebase yanıtının
  siparişi havuza anlık geri eklemesini önleyen yerel tombstone koruması.
- ETag yarışında tüm denemelerin tükenmesi artık **geçici** sayılır:
  başarılı olmayan işlem kanıtı / durable outbox korunur, kalıcı
  karantinaya yanlışlıkla atılmaz.
- Başka cihaz tarafından zaten hedef duruma alınmış siparişler
  tekrar çakışma yaratmadan onaylanır.
- Gerçek iş kuralı çakışmalarında (örneğin yetersiz stok, uygunsuz
  durum geçişi) başarısız işlem otomatik uygulanmaz; kullanıcı incelemesi
  için geçmiş hata arşivinde tutulur. Kayıtlar silinmez.

### Arayüz ve duyurular
- Üst sol panelde **ALFA ERP Yönetici / Personel v1.1.0** ayrımı.
- Personel Ayarlar düğmesi kaldırıldı; üst panelde açık/koyu tema anahtarı.
- Personelde bulut bağlantısı yanında **Hata Bildir**: yalnız seçilen
  teknik kategoriyi gönderir. Serbest metin ve kişisel müşteri verisi
  toplanmaz; internet yoksa rapor yerel sırada saklanır.
- **Duyurular** paneli ve sürüm notları; ilk kurulumda tek seferlik
  neler değişti penceresi.
- En fazla 24 saatte bir GitHub kararlı sürüm sorgusu ve yeni sürüm
  bulunduğunda popup; indirme ve kurulum yine kullanıcının onayıyla.
- Siparişlere Genel Bakış, Firebase Cihaz Yetkisi ve Yeni Sipariş
  popuplarında tam açık tema / yüksek kontrast desteği.

### Dağıtım ve veri güvenliği
- Tek `ALFA_ERP_Setup_V1_1_0.exe`: kurulum sırasında yalnızca seçilen
  Personel ya da Yönetici sürümü kurulur. Yönetici kurulum parolası
  ve Firebase owner rol doğrulaması sürer.
- `SHA256SUMS.txt` ile kurulum paketi doğrulanır. Güncelleme Merkezi
  kurulumdan önce buluta gitmemiş sipariş varsa yükseltmeyi engeller.
- Firebase veri şeması veya kuralları değiştirilmedi; ek ücretli
  Google Cloud servisi gerekmiyor.
- Önceki v1.0.0 kararlı Release ve tüm sipariş/stok geçmişi korunur.
- Otomatik davranış testleri kullanıcının hız tercihi nedeniyle
  **çalıştırılmaz**; yayın iş akışında sözdizimi, bağımlılık, paketleme,
  EXE ve SHA-256 kontrolleri yapılır.

## [v1.0.0] — 2026-11-05

İlk birleşik Windows kurulum paketi. Personel/Yönetici seçim ekranı,
Yönetici kurulum parolası, Firebase RTDB ortak sipariş havuzu,
Hata Merkezi, güncelleme mekanizması ve SHA-256 doğrulanan GitHub
Release dağıtımı.

[Download/Release v1.0.0](https://github.com/alarslan12/alfa-erp/releases/tag/v1.0.0)
