"""Offline embedded ALFACOPYCENTER Suite release history.

This is shipped inside every ERP EXE so notes are available without GitHub
or Firebase connectivity. Exact historical release pages remain accessible at
https://github.com/alarslan12/alfa-erp/releases.
"""

_RELEASES = [
    ("2.1.2", "Üst çubuk sadeleştirme ve sekme etiketi düzeltmesi", [
        "Tek Duyurular ve Güncelleme Merkezi; mükerrer düğme kaldırıldı.",
        "Üst kontroller genişletildi, bulut göstergesi daraltıldı ve kapsül düzenlendi.",
        "Bildirimler & Cihazlar sekmesindeki ampersand gösterimi düzeltildi.",
    ]),
    ("2.1.1", "Ayar kartları, cihaz paneli ve bildirim iyileştirmeleri", [
        "PDF, Excel ve görünüm kartları hizalandı; ayar sekmeleri pillbox görünümünde.",
        "Bildirimler & Cihazlar ortak ekranı: Yönetici cihaz listesi, Personel kendi cihazı.",
        "Otomatik bildirimde yalnız dört özgün Ozan anonsu rastgele; ayrı ve rastgele dinleme düğmeleri.",
        "Güncelleme denetimi üst çubuğa taşındı; eş boyutlu ikonlar ve kompakt bulut durumu.",
        "Yönetici cihaz panelinin Windows yerleşimi düzeltildi; mevcut kullanıcı verileri korunur.",
    ]),
    ("2.1.0", "Yönetici ve Personel çalışma alanı yenilemesi", [
        "Hata Merkezi toplu inceleme ve silme, arama, hata kodu ve ayrıntı görünümü.",
        "Bağlı Bilgisayarlar UID, özel ad ve güvenli pasif cihaz temizliği.",
        "İşlem günlüğü tarih ve 120 saniyelik aktivite grupları; filtre ve zaman damgaları.",
        "PDF, Excel ve görünüm tek Uygulama Ayarları sayfasında; sistem sağlığı kaldırıldı.",
        "Derleme yalnız Yönetici; geçmiş not kurtarma kaldırıldı, yeni mobil notlar korunuyor.",
        "Bulut çakışma uyarısı 14 saniye; ElevenLabs kaldırıldı, dört özgün Canva Ozan M4A anonsu eklendi.",
    ]),
    ("2.0.53", "Mobil not havuz aktarımı ve güvenli eski checkout onarımı", [
        "Mobil checkout sipariş notları masaüstü havuz siparişine ve ilk not uyarısına aktarılır.",
        "Eski sürümden notsuz kalan siparişler, kaynak checkout notu mevcutsa güvenli koşullu yazmayla kurtarılır.",
        "Mevcut sipariş notları, okunmuş veya bekleyen uyarılar ve diğer sipariş verileri değiştirilmez.",
        "Fason ZIP baskı talimatına kayıtlı sipariş notu varsa eklenir.",
        "Firebase canlı Rules/Hosting yayını yapılmaz; tüm Suite uygulamaları tek Setup içinde güncellenir.",
    ]),
    ("2.0.52", "Fason ZIP adet etiketi ve sade baskı talimatı", [
        "Siparişi Derle PDF dosyalarının başına 1 ADET, 2 ADET gibi baskı miktarı ekler.",
        "Baskı talimatı yalnız sipariş kodu, toplam sayfa sayısı ve toplam kitap sayısını içerir.",
        "Sayfa toplamında tarihsel sipariş sayfa kaydı, yoksa katalog sayfa sayısı esas alınır.",
        "Tekli veya seçili kitap ZIP'lerinde toplamlar yalnız paketteki kitaplara aittir.",
        "PDF içerikleri aynen korunur; Firebase, yerel kullanıcı kayıtları ve diğer Suite uygulamaları değişmez.",
    ]),
    ("2.0.51", "Fason sipariş ZIP'inde hızlı orijinal PDF aktarımı", [
        "Siparişi Derle PDF'leri yeniden görüntüleyip oluşturmadan ZIP'e doğrudan ekler.",
        "PDF yeniden sıkıştırması kaldırıldı; kaynak dosyalar, baskı çözünürlüğü ve görünüm birebir korunur.",
        "Rastgele PDF adı, Siyah/Renkli klasörleri, tekrar adedi ve baskı talimatı korunur.",
        "PDF içindeki orijinal metaveri ve filigranlar artık temizlenmez; yalnız dosya adı değiştirilir.",
        "Eksik belgede ZIP oluşturulmaz; Firebase, diğer Suite bileşenleri ve kullanıcı verileri değişmez.",
    ]),
    ("2.0.50", "Yerel fason sipariş derlemesi ve Analitik yazdırma", [
        "Personel/Yönetici Sipariş detayından tüm siparişi, tek kitabı veya seçili kitapları anonim ZIP'e derler.",
        "PDF sayfaları 300 DPI görüntü olarak yeniden oluşturulur; kaynak PDF metadata, gizli nesneler ve ek dosyalar taşınmaz.",
        "Siyah/Renkli klasörleri, rastgele PDF adları, tekrar adedi uyarıları ve BASKI_TALIMATI.txt içerir.",
        "Sipariş numarasıyla ZIP Windows Masaüstüne otomatik kaydedilir; önceki arşivler ezilmez.",
        "Analitik HTML raporu Masaüstüne kaydedilir ve tarayıcı yazdırma penceresi açılır.",
        "Yalnız yerel dosyalar kullanılır; Firebase ve önceki siparişler değişmez. Görsel filigranlar PDF sayfalarında kalabilir.",
    ]),
    ("2.0.49", "Banner Studio tek dışa aktarma ve arayüz sadeleştirme", [
        "Veri kaynakları ve JSON yedeği Ayarlar > Uygulama Yönetimi alanına taşındı.",
        "Tek PNG/JPG/A4 PDF dışa aktarma, kalite seçimi ve doğrudan Masaüstüne kaydetme eklendi.",
        "Dosyalar Tasarım Arşivi A-Z sırası ve arşiv adıyla numaralandırılır.",
        "Vintage Koleksiyon/Minimal Premium ve Akıllı/Dengeli Sıralar seçimleri sadeleştirildi.",
        "Kapak zoom üst sınırı %100; kitap özel etiketler sağ tıkla ve tek satır korunur.",
        "ALFACOPYCENTER logosu uygulama üstünde; kapak arşivi ve diğer uygulama verileri korunur.",
    ]),


    ("2.0.48", "FlexFlow iki vardiyaya dağıtılan tahmini üretim yükü", [
        "Gerçek tamamlanan siparişler korunurken FlexFlow'a ayrı iki çizgili 'Gerçek tamamlanma / Üretim eşdeğeri' grafiği eklendi.",
        "Kayıtlı hazırlandı/kolilendi hareketleri kendi günlerine bağlanır. Eksik hazırlama zamanı, önceki gün aktivasyon kaydı varsa mesai/kaynak kapasitesine göre iki güne tahmini paylaştırılır.",
        "Makine+işçilik referansları SB/RNK sayfa, delme, spiral ve kolileme alt sınırlarıdır; gerçek çalışan saat ölçümü değildir.",
        "Günlük yorum ve CSV/HTML raporlarında kaydedilmiş ve modellenmiş iş yükleri, dünden devreden katkı, eksik sayfalar ve kapasite uyumsuzluğu açıkça gösterilir.",
        "Sipariş durumları, Firebase/yerel veri, muhasebe, Banner Studio, mobil katalog ve Print Surveillance değiştirilmez.",
    ]),


    ("2.0.47", "Banner Studio arşiv kaydı ve Türkiye saat dilimi düzeltmesi", [
        "Tasarım Arşivi > Düzenle akışı mevcut arşiv kimliğini korur; Değişiklikleri Kaydet kopya oluşturmaz.",
        "Farklı Kaydet yeni kayıt oluşturur; aynı isimli tasarım için üzerine yazma onayı gerekir.",
        "Düzenlenmekte olan bannerın PNG/JPG indirmeleri arşiv kaydını günceller.",
        "Arşiv oluşturulma/güncellenme tarihleri Europe/Istanbul saatinde gösterilir; UTC kaynak verisi değiştirilmez.",
        "Banner Studio dışındaki Suite uygulamalarının işlevleri ve yerel veri klasörleri korunur.",
    ]),


    ("2.0.46", "FlexFlow hareketli gün filtreleri ve günlük operasyon yorumu", [
        "Son 7/14/30 gün seçimleri kaldırıldı; yalnızca kayıtlı üretim hareketi olan günler modern tarih listesinden seçilebilir.",
        "Siparişler ekranında kullanılan takvim FlexFlow'a eklendi; tek gün ve Shift+tık tarih aralığı aynı veri raporunu filtreler.",
        "En üstte seçilen günün/dönemin iş hacmi, hareket kaydı güvenilirliği, üretim ortalaması ve açık iş önceliklerini açıklayan günlük değerlendirme yer alır.",
        "Günlük/saatlik grafik ve tablolar ile CSV/HTML raporları da seçilen gün veya dönemle uyumlu çalışır.",
        "Geçmiş tarihteki açık sipariş durumu uydurulmaz; güncel kuyruk ayrıca belirtilir. Kayıt bulunmayan hareketler sıfır olarak gösterilmez.",
        "Mevcut muhasebe, Firebase, personel katalog ve sipariş akışları korunur.",
    ]),


    ("2.0.45", "FlexFlow günlük/saatlik operasyon analitiği", [
        "FlexFlow teknik dakika katsayıları yerine anlaşılır, gerçek işlem sayılarını ve üretim temposunu gösterir.",
        "Bugünkü tamamlanan sipariş, hazırlanma/kolileme nüshaları, açık sipariş ve vardiya saati başına tamamlama hızı.",
        "7/14/30 günlük üretim eğilimleri, önceki üretim günleriyle karşılaştırma ve mesaiye yetişme değerlendirmesi.",
        "Seçilen günün saatlik aktife alma/tamamlama grafiği ve kayıtlı hazırlanma/kolileme hareketleri tablosu.",
        "Olayların sunucu zaman damgaları mevcut Firebase eşitlemesinden alınır, ek ağ isteği yapılmaz; kayıt eksikleri açıkça belirtilir.",
        "CSV ve HTML günlük/saatlik üretim raporları eklendi; teknik makine varsayımları ekranda gizlidir.",
        "Normal Analitik, mevcut sipariş ekranları, iade/kargo muhasebesi ve Firebase kuralları korunur.",
    ]),


    ("2.0.44", "Onaylı Analitik tasarımı ve grafik doğrulaması", [
        "Çizgi grafikleri: QPainter yolu dolgusuz çizilir, önceki renkli üçgen/dolu alan sorunu giderildi.",
        "Sol dikey eksende ölçülü sayısal değerler geri getirildi; hover'da her veri noktasının gerçek değeri görünür.",
        "Uygulamanın genelinde çıkan Bulut bağlı tooltip'i ana pencereden kaldırılıp sadece bağlantı göstergesine bırakıldı.",
        "Platform satış gelir grafiği bir grafik kartı genişliğine sığacak şekilde küçültüldü.",
        "Grafiğin yanında seçili dönemin iade/kargo sonrası cirosu, sayfası, kitap adedi ve SB/RNK sayılarından oluşan özet kartlar eklendi.",
        "Yeni özet değerleri gerçek muhasebe verilerindendir; uydurma büyüme oranı kullanılmaz.",
        "Normal Analitik / FlexFlow, Katalog, Siparişler ve Firebase güvenlik kuralları korunur.",
    ]),


    ("2.0.43", "İnteraktif platform pasta grafiği ve sade çizgi grafikler", [
        "Normal Analitik'e satış platformlarının iade sonrası ciro payını gösteren interaktif halka grafik eklendi.",
        "Gardrops, Dolap ve diğer platformlarda yüzde/gelir tutarı hover'da; renkli açıklamalar yanda gösterilir.",
        "Çizgi grafikler dolgusuz ve yalın tutuldu; dikey eksende sabit sayılar ve tepe üstünde kalıcı değerler kaldırıldı.",
        "Her veri noktasının kendi sayısal değeri yalnızca fareyle üzerine gelindiğinde gösterilir.",
        "İade/kargo sonrası finans kartları, FlexFlow ve mevcut sipariş ekranları korunur.",
    ]),


    ("2.0.42", "Analitik hızlandırma ve görsel FlexFlow", [
        "Analitik ekranı Normal Analitik ve FlexFlow olarak iki ana sekmeye ayrıldı; popup kaldırıldı.",
        "FlexFlow tek ekranda dinamik kapasite grafikleri, kişi-saat kartları ve sipariş iş yükü tablosu gösterir.",
        "Analitik raporu yüklemesi gecikmeli/birleştirilmiş; pencere boyutu her değiştiğinde bütün grafikler yeniden oluşturulmaz.",
        "Çizgi grafiklerinde tam sol eksen, hover sayısal değerleri ve vurgulanan tepe noktaları eklendi.",
        "İade ve kayıtlı kargo giderleri sonrası nihai ciro; ödenmeyen tutar da aynı net bazdan hesaplanır.",
        "İade sebebi girişindeki beyaz zemin-beyaz yazı sorunu giderildi.",
        "Kitap başına ciro eklendi, kitap/sayfa ve SB/RNK istatistikleri birleştirildi; gereksiz alt metrikler kaldırıldı.",
    ]),

    ("2.0.41", "FlexFlow sayısal üretim kapasitesi", [
        "Yönetici Analitik ekranına FlexFlow Verimlilik görünümü eklendi.",
        "3 siyah-beyaz ve 3 renkli yazıcının gerçek hızları, tek delme cihazı ve iki çalışan hesaba katılır.",
        "Standart işçilik kişi-saatleri, baskı yükü, darboğaz ve mesai riski dakika cinsinden gösterilir.",
        "Aktif işler, havuz ve seçili dönemin tamamlanan siparişleri ayrıdır; bilinmeyen sayfa sayıları uyarılır.",
        "Personel ekranı, mevcut katalog/sipariş işlemleri, Firebase kuralları ve kullanıcı verileri değişmedi.",
    ]),

    ("2.0.40", "Banner Studio arka plan süreçleri düzeltmesi", [
        "Tarayıcıdaki son Banner Studio sekmesi kapatılınca yerel sunucu otomatik kapanır.",
        "Aynı bilgisayarda tekrar açma mevcut sunucuyu kullanır; mükerrer EXE oluşmaz.",
        "Beklenmedik tarayıcı kapanışında sahipsiz süreçler zaman aşımıyla temizlenir.",
        "Tasarım arşivi, ERP siparişleri ve Firebase verileri korunur.",
    ]),

    ("2.0.39", "Banner arşivi, iade sebebi ve performans", [
        "Tasarım Arşivi'nde Türkçe karakter uyumlu arama ve sonuç sayacı.",
        "Arşivde silme, yeniden adlandırma ve seçme işlemlerinde kaydırma konumu korunur.",
        "Yönetici iade sebebini girer, düzenler; iade kartlarının altında görünür.",
        "Firebase iade sebebi senkronizasyonu yönetici yetkisi ve sürüm çakışma kontrolüyle yapılır.",
        "Gereksiz arka plan arayüz yenilemeleri birleştirilerek uzun kullanımda takılma riski azaltıldı.",
    ]),

    ("2.0.38", "Kargo takibi ve iade yönetimi", [
        "Yönetici tamamlanan siparişlerden iade işaretler veya geri alır.",
        "İade sekmesi, iade sonrası ciro ve oranlar; kargo gideri korunur.",
        "Açık Adres ve Telafi kargo takibi; 0 TL/boş ücret bekler.",
    ]),
    ("2.0.37", "Telafi sipariş etiketi", [
        "Telafi siparişlerinin ciro alanında 0 TL yerine TELAFİ SİPARİŞ etiketi gösterilir.",
        "Personel ve Yönetici ortak sipariş kartları; muhasebe ve kargo giderleri değişmez.",
    ]),
    ("2.0.36", "Sipariş arşivi ve arayüz düzeltmeleri", [
        "Tamamlanan siparişler 20'şerli sayfalara ve son üç takvim günü / arşiv ayrımına kavuştu.",
        "Tamamlanan siparişlerde statik kart ve kapak rengi; tikler korunur.",
        "Yöneticiye açık adres kargo ücreti düzenleme; analitikte aktif ve tamamlanan giderler.",
        "Renk körlüğü paleti genişletildi; adet düğmeleri ve kitap değişikliği ipucu düzeltildi.",
    ]),
    ("2.0.35", "Renk körlüğü modu", [
        "Personel ve Yönetici ayarlarına kalıcı ve temadan bağımsız renk körlüğü modu.",
        "Kolilenen kitap ve tamamlanan siparişlerde yoğun elektrik mavisi, güçlü kenar ve hover.",
        "Okunmamış not ve güncelleme uyarılarında parlak sarı; durumlar metinle de ayrılır.",
        "Üretim özeti, sipariş işlevleri ve Firebase kuralları korunur.",
    ]),
    ("2.0.34", "Aktif sipariş üretim özeti", [
        "Aktif siparişler üstünde altı kompakt gösterge: sipariş, kitap, kalan, basılacak, kolilemeye hazır ve ciro.",
        "SB/RNK adetleri, basılacak sayfa ve kolileme ilerlemesi gösterilir.",
        "Filtrelerden bağımsız tüm aktif siparişler hesaplanır; dar ekranda iki satıra uyarlanır.",
        "Mevcut sipariş işlemleri, not sistemi ve Firebase kuralları korunur.",
    ]),
    ("2.0.33", "Not alanı ve yerel okundu onayı", [
        "Not alanının tema renkleri, yeni sipariş notu başlığı ve sade popup düzeltildi.",
        "Okundu onayı kalıcı yerel kuyruğa yazılır; bulut yanıtı beklenmez.",
        "Uyarıya basınca popup kapanır; detaya basınca onaydan sonra detay açılır.",
        "Yeşil kolileme kartları ve Firebase kuralları korunur.",
    ]),
    ("2.0.32", "Kolilenen kitapların yeşil görünümü", [
        "Tamamen kolilenen kitap kartlarına hafif şeffaf yeşil zemin, yeşil kenar ve hover eklendi.",
        "Sipariş detayları, genel bakış ve sipariş kapaklarında aynı koli durumu kullanılır.",
        "Koli geri alındığında renk normale döner; SB/RNK adet etiketleri korunur.",
        "v2.0.31 not sistemi korunur; Firebase kuralları değişmedi.",
    ]),
    ("2.0.31", "Sipariş notu ve revizyon onayı (ön izleme)", [
        "Yeni siparişlerde opsiyonel not; Yönetici için mevcut not düzenleme.",
        "Kargo, kitap/adet, sipariş türü, platform, ciro ve not değişikliklerinin karşılaştırması.",
        "Kartta ışıklı güncelleme uyarısı; Okudum, anladım onayı ve kapak hover önizlemesi.",
        "Revizyon başına bulut onayı; eski kuyruk işlemleri kontrollü.",
        "Firebase güvenlik kuralları değişmedi; v2.0.30 kararlı sürüm olarak kalır.",
    ]),
    ("2.0.30", "Stabilite ve performans optimizasyonu", [
        "v2.0.28 çalışan sürümü esas alındı; iptal edilen v2.0.29 kargo fişi dahil değildir.",
        "Güncelleme indirme blokları büyütüldü, arayüz ilerleme olayları sınırlandırıldı.",
        "Sipariş bildirim servisinde gereksiz yerel durum yazımları azaltıldı.",
        "Firebase kuralları, siparişler ve katalog değiştirilmedi.",
    ]),
    ("2.0.29", "İptal edilen kargo fişi güncellemesi", [
        "Bu sürüm üretimden çıkarıldı ve v2.0.30'a taşınmadı.",
    ]),
    ("2.0.28", "Sipariş kapaklarında sade SB/RNK etiketleri", [
        "Siyah toplam adet rozeti kaldırıldı; yalnızca SB ve RNK adetleri kapak üzerinde gösterilir.",
        "Etiketler sağ üstte yer alır; tek nüsha etiketleri korunur.",
        "Personel ve Yönetici ortak kart düzeltmesini içerir.",
        "Katalog araması, PDF eşleştirme ve Firebase verileri korunur.",
    ]),
    ("2.0.27", "Sipariş kapak etiketleri ve hassas katalog araması", [
        "Aktif sipariş ve sipariş havuzu kapaklarında toplam adet, SB ve RNK miktarları gösterilir.",
        "Tek nüsha ve küçük kapaklarda etiketler gizlenmez; dar alanda alt alta yerleşir.",
        "TUSDATA 24, 24 TUSDATA, TUS 24 gibi seri aramaları gerçek sayı ve kelimelerle eşleşir; 424 kodlu ilgisiz kitaplar çıkmaz.",
        "Personel ve Yönetici ortak düzeltmeleri içerir.",
        "PDF eşleştirme, kapak önbelleği ve Firebase verileri değiştirilmedi.",
    ]),
    ("2.0.26", "TUSDATA Konu kapakları ve boş sayfalı kitap görünürlüğü", [
        "TUSDATA Konu derslerinin PDF adındaki kelime sırası, Cilt 1/II yazımı ve işaret farklılıkları tanınır.",
        "Kitap serisi, dersi ve cilt numarası birebir doğrulanır; başka serinin kapağı atanmaz.",
        "Gerçek eşleşmeyen PDF dosyaları ayrı JSON raporunda listelenir; mevcut manuel/otomatik kapaklar korunur.",
        "Sayfa sayısı olmayan kitaplar katalogda varsayılan olarak gizlenir; Firebase'den silinmez.",
        "Personel ve Yönetici ayarları ilk açılıştan itibaren uygulanır.",
    ]),
    ("2.0.25", "DUSDATA 33 ve DENTTEST kitap kapak eşleştirmesi", [
        "DUSDATA 33 ve DENTTEST PDF adları kitap kodundan bağımsız tam adlarıyla eşleştirilir.",
        "Seri/cilt numaraları yanlış kitap kodu sayılmaz.",
        "Eski kodlu ve elle eklenen kapaklar, JPEG önbelleği ve Firebase verileri korunur.",
        "Sayfa sayısı boş kitapları katalogda gösterme ayarı eklendi; varsayılan açık.",
        "Personel ile Yönetici ortak PDF kütüphanesi ve ayarlar kodunu kullanır.",
    ]),
    ("2.0.24", "Çalışan v2.0.19 koduna güvenli geri dönüş", [
        "PDF kod eşleme, kapak görselleri ve katalog yükleme kodu v2.0.19'a geri alındı.",
        "Önceki kapak JPEG'leri manifest doğrulaması yüzünden gizlenmez.",
        "İşletim sistemindeki Excel/PDF dosyaları ve Firebase verileri silinmez.",
        "Firebase'de daha önce sıfırlanmış sayfa değerleri ayrı yedekten kurtarılmalıdır.",
        "Kurulumdan önce %LOCALAPPDATA%\\AlfaERP klasörünü yedekleyin.",
    ]),
    ("2.0.23", "Kapak görünürlüğü ve sayfa verisi kurtarma", [
        "Başarısız PDF taraması önceki kodlu JPEG kapakları gizlemez.",
        "Boş tarama eski kapak manifestini silmez.",
        "Excel/Firebase boş sayfaları, aynı kod ve ad için önceden bilinen sayfaları yerelde sıfırlamaz.",
        "Yerel sayfa kurtarma kayıtları korunur; bulut verisi kendiliğinden değiştirilmez.",
        "Excel önizlemesinde dolu ve boş sayfa sayıları gösterilir.",
    ]),
    ("2.0.22", "PDF kodları ve eşleşme raporu düzeltmesi", [
        "31-endodonti.pdf ve kitap_31.pdf gibi açık kod içeren PDF'ler tanınır.",
        "Tam kitap adları arasında yalnız güvenli yazım benzerlikleri eşleştirilir.",
        "Klasörde PDF'si olmayan katalog kitapları ile eşleşmeyen PDF dosyaları ayrı gösterilir.",
        "Aynı kodlu iki PDF varsa rastgele dosya seçilmez.",
        "Önbellek v6 ile yenilenir; yatay kapaklar -90 derece kalır.",
    ]),
    ("2.0.22", "PDF kapak görünürlüğü ve eşleşme güncellemesi", [
        "Küçük ama geçerli JPEG kapaklar katalogdan gizlenmez.",
        "Tam PDF dosya adı eşleştirmesi güvenli kapak/baskı eklerini destekler.",
        "Otomatik PDF kapak önbelleği v5'e yükseltildi; yeniden tarama gerekir.",
        "Yatay PDF kapakları -90 derece döner; manuel kapaklar korunur.",
        "Önceki Excel, Analitik PIN, hata ve cihaz temizliği revizyonları korunur.",
    ]),
    ("2.0.22", "PDF kapak taraması ve kitap eşleşmesi onarımı", [
        "Yatay ilk PDF sayfaları -90 derece döndürülür ve ters yönlü önbellek yenilenir.",
        "PRETUS 3 kitabının 402 kodu ile PDF'nin tam adı eşleşebilir.",
        "PDF adındaki seri sayıları yanlış kitap kodu olarak kullanılmaz.",
        "Belirsiz veya yinelenen PDF kaynakları raporlanır, yanlış görsel atanmaz.",
        "Eski otomatik kapaklar diskte korunur; doğrulanmamışsa katalogda kullanılmaz.",
        "Firebase Excel kitap katalog revizyonunda yerel PDF kapakları yeniden taranır.",
        "Ayarlar ekranında eksik kapak örnekleri ve yerel JSON tanı raporu bulunur.",
    ]),

    ("2.0.19", "Analitik ciro odağı ve telafi muhasebesi", [
        "Toplam, kargo sonrası, ödenen ve ödenmeyen ciro dört belirgin açıklamalı kartta toplandı.",
        "Ortalama sipariş, sayfa başı ciro ve kitap başı ortalamalar ayrı verimlilik grubuna taşındı.",
        "Telafi siparişi oluşturma ve düzenlemede ciro otomatik 0 TL; kargo gideri tamamlanırken sorulur.",
        "Eski telafi siparişindeki hatalı ciro Analitik ve HTML muhasebe toplamlarına dahil edilmez.",
        "Telafi/açık adres kargo giderleri ayrı gösterilip kargo sonrası tutardan tek kez düşülür.",
        "Yatay ilk PDF kapaklar ters yön yerine +90° döndürülür; eski otomatik kapak önbelleği yenilenir.",
        "Genel Bakış filtreleri beyaz boşluksuz kurumsal açılır liste stilini kullanır.",
    ]),
    ("2.0.18", "Sipariş görünümü, bildirim ajanı ve yatay kapaklar", [
        "Sipariş detayları ve genel bakış kitapları sayısal kitap koduna göre sıralar.",
        "Hazırlanmayanlar ve kolilenmeyenler aynı pillbox'ta ayrı filtrelenebilir.",
        "Sipariş sekmeleri kaydırılabilir, dışarı sürüklenerek ayrı pencereye alınabilir ve geri eklenebilir.",
        "Katalog başlık bandı iki satırı koruyarak kısaldı; SB/RNK sayaçları büyüdü ve aradaki çizgi kaldırıldı.",
        "Dolap uzun kodunun son dört hanesi ayrı gruba dönüştürüldü.",
        "Windows Zamanlanmış Görev ile ERP'den bağımsız Firebase sipariş bildirimi ve doğal ses seçenekleri.",
        "Yatay PDF ilk sayfası 270 derece döndürülerek kapaklara oturtulur.",
    ]),
    ("2.0.17", "Firebase kitap kodları, 0 sayfa ve Excel kurtarma", [
        "Buluttaki eski kod kaymaları Excel'deki kodlara göre, sunucu doğrulamalı olarak düzeltilir.",
        "Katalogun eski kopyası otomatik saklanır ve tam yazma doğrulanmadan revizyon artışı yapılmaz.",
        "Yeni siparişlerde kitap adı ve sayfa anlık görüntüsü Firebase'e doğru gönderilir.",
        "Eski 0 sayfa kaydı katalogda doğru sayfa biliniyorsa ekranda düzeltilir.",
        "Mobil katalog önbelleği ve sipariş sayfa toplamları katalog değişiminde güncellenir.",
        "Cloud Shell üzerinden salt-okunur fark kontrolü ve kontrollü kurtarma eklendi.",
    ]),
    ("2.0.16", "Analitik PIN açılış güvenliği", [
        "Personel ve Yönetici PIN kontrolü artık GUI iş parçacığına yönlendirilen Qt slotları ile sonuçlanır.",
        "İş parçacığı bitişinde pencereyi doğrudan sonlandırma/iş parçacığı bekleme yarışı giderildi.",
        "Analitik raporun yeniden çizimi ve boyut değişimi sırasında iç içe render korunur.",
        "Personel PIN sonrası Analitik ekranı için Windows regresyon testi eklendi.",
    ]),
    ("2.0.15", "Geçmiş notlar, Personel Excel ve temizlik araçları", [
        "Personel ve Yönetici güncelleme ekranları önceki Suite revizyonlarını çevrimdışı gösterir.",
        "Personel, yetkilendirilmiş Firebase cihazından Excel kitap kataloğu aktarabilir.",
        "Yönetici, eski pasif cihazları ve hata raporlarını onayla temizleyebilir.",
        "Mevcut siparişler, katalog kartlarının düzeni ve Suite bileşenleri korunur.",
    ]),
    ("2.0.14", "Yönetici kurulum koruması ve Cloud Shell", [
        "Yönetici bileşeni için yerel kurulum şifresi; Personel, Banner ve Print şifresiz.",
        "Firebase owner yetkisi yerel şifreden bağımsızdır ve Cloud Shell'de onaylanır.",
        "Tek Suite kurulumu, önceden seçilen bileşenler ve kullanıcı verileri korunur.",
    ]),
    ("2.0.13", "Firebase ile dört bileşenli Suite bütünleşmesi", [
        "Personel ve Yönetici Firebase RTDB, canlı SSE ve çevrimdışı kuyruk kullanır.",
        "Banner Studio ve Print Center aynı Suite Setup'a geri eklendi.",
        "Ortak Güncelleme Merkezi, SHA-256 kontrolü ve v2 Suite yayın kanalı.",
        "Gardrops satışına girilen ciroyu %100 koruyan düzeltme.",
        "Eski bulut bağımlılıkları, yinelenen kurulumlar ve geçiş araçları temizlendi.",
    ]),
    ("2.0.12", "Banner Studio özel fiyat etiketi", [
        "Kitap kapağındaki fiyat farkı yazısının punto ayarı düzeltildi.",
        "Gerektiğinde iki satırlı etiket ve taşma önleyici yerleşim kullanılır.",
    ]),
    ("2.0.11", "Banner Studio kapak eşleştirme", [
        "Kapak dosyasının kitap kodu eşleşiyorsa farklı başlık nedeniyle reddedilmesi düzeltildi.",
        "Cerrahi/Radyoloji gibi kısaltılmış isimler ve kapak arşivi korunur.",
    ]),
    ("2.0.10", "Banner Studio döndürme, alt grup ve setler", [
        "Yatay kapaklar 270° çevrilerek orantısı korunur.",
        "YDUS, DUSDATA 1+2, ÇTS/TTS gruplarında doğru Excel etiketlerine göre arama.",
        "Arşivdeki tasarım açıldığında kodlar güncel katalogla eşleştirilir.",
    ]),
    ("2.0.9", "Banner Studio Excel veri yenileme", [
        "Kitap adı ve kodu varsa sayfa sayısı boş olan satırlar da kabul edilir.",
        "Yeni Excel eskisinin yerine geçer; tasarım ve kapak arşivi silinmez.",
    ]),
    ("2.0.8", "Banner Studio Excel şablonu doğrulama", [
        "Boş yer tutucular ve mükerrer kitap kodları için veri kontrolleri.",
        "Hatalı içe aktarma mevcut afiş arşivini değiştirmez.",
    ]),
    ("1.1.2", "Firebase ilk iyileştirmeler", [
        "Çevrimdışı yeniden açılış için doğrulanmış çalışma alanı işareti.",
        "Başlangıç kontrolleri, hızlı bağlantı kurtarma ve korunan işlem kuyruğu.",
    ]),
    ("1.1.1", "Güncelleme Merkezi güvenilirliği", [
        "Güncelleme sırasında gerçek ERP penceresinin güvenli kapanışı.",
        "Bekleyen işlemlerle güncellemeyi durdurma ve yeniden başlatma düzeltmeleri.",
    ]),
    ("1.1.0", "Envanter, eşitleme ve duyurular", [
        "Yönetici satış iptali: stok partilerine güvenli geri alma ve satış arşivi.",
        "Siparişlerde çakışma kurtarma, Hata Bildir, Duyurular ve günlük sürüm kontrolü.",
    ]),
    ("1.0.0", "Firebase ERP ilk birleşik Windows sürümü", [
        "Personel/Yönetici seçimi, Firebase RTDB ortak sipariş havuzu, hata merkezi.",
        "SHA-256 doğrulamalı GitHub güncellemesi ve owner cihaz yetkisi.",
    ]),
]


def release_history_markdown(installed=None):
    """Full offline version log; retains previous v1/v2 releases."""
    lines=["# ALFACOPYCENTER Suite · Sürüm geçmişi",
           "Kurulu sürüm: **v"+str(installed or "bilinmiyor")+"**",
           ""]
    for number,title,items in _RELEASES:
        lines.extend(("## v"+number+" — "+title,""))
        lines.extend("- "+item for item in items)
        lines.append("")
    lines.append("Daha eski ve ayrıntılı sürüm kayıtları: "
                 "https://github.com/alarslan12/alfa-erp/releases")
    return "\n".join(lines)
