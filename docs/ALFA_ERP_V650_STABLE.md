# ALFA ERP 6.5.0 — İlk kararlı sürüm notları

Bu sürüm Firebase çoklu cihaz, kitap kataloğu, Sipariş Havuzu, Analitik,
Envanter ve bildirim sistemini tek masaüstü platformu olarak sürdürür.
V6.4.2'de kabul edilen işlevler korunur.

## Yeni sipariş bildirim sesleri

Ayarlar → Görünüm ve bildirimler → **Yeni sipariş bildirim sesi**.

- Windows varsayılan uyarı
- Yumuşak çift ton
- Belirgin üçlü ton
- Kısa çift uyarı
- Her siparişte farklı ton
- Sessiz (masaüstü/bildirim penceresi açık kalır)

**Sesi dinle** düğmesi seçilen tonu çalar. Seçim bilgisayarın
\`%LOCALAPPDATA%\AlfaERP\alfa_ayarlar.json\` dosyasına atomik
olarak kaydedilir. Bildirim servisi yeni siparişte bu dosyayı okur;
servisi yeniden başlatmaya gerek yoktur.

Arka plan Windows bildiricisi Personel kurulumunda yer alır ve
Windows oturumu açılışında başlar. Windows bildirim izinleri ve
hoparlör ayarları sistemden etkinleştirilmiş olmalıdır.
Bildirim servisinin kapalı uygulamayla gerçek cihazda çalışma testi
gereklidir.

## PDF'nin ilk sayfasından otomatik kapak

Ayarlar → Kitap PDF klasörü → **PDF klasörü seç**.

- \`31.pdf\`, \`031.pdf\`, \`kitap_31.pdf\`, \`31-endodonti.pdf\` eşleşir.
- \`31\` ile \`131\`, \`310\` karıştırılmaz. Birden fazla
  belirsiz sayıya sahip dosyalar otomatik seçilmez.
- Seçilen klasörün alt klasörleri de taranır.
- **Sadece PDF'nin ilk sayfası** 480×690 sınırında bir JPEG'e
  dönüştürülür. PDF'nin orijinali hiç değiştirilmez.
- Çıktı: \`%LOCALAPPDATA%\AlfaERP\kapaklar\pdf_otomatik\<kod>.jpg\`.
- Elle eklenen \`kapaklar\<kod>.jpg/png\` otomatik kapağın üzerindedir;
  hiçbir mevcut elle seçilmiş görselin üzerine yazılmaz.
- PDF dosya yolu, boyutu ve son değişiklik zamanı önbelleğe kaydedilir.
  İleride program açıldığında yalnız yeni/değişmiş dosyalar
  yeniden render edilir. **Tara ve kapakları güncelle** elle tarama yapar.
- PDF veya oluşturulan JPEG Firebase'e ya da mobil kataloğa
  otomatik yüklenmez. Her bilgisayar kendi PDF klasörünü seçebilir
  ya da aynı paylaşımlı Windows klasörünü gösterebilir.
- Şifreli/bozuk PDF'lerde ilgili kod atlanır; diğerleri devam eder.
  Sonuç ekranında eşleşen, üretilen, önbellekte bulunan ve hata
  sayıları gösterilir.

PDF kapaklarını desteklemek için resmi \`PySide6-Pdf\` bileşeni
Windows kurulumuna eklenmiştir. <https://pypi.org/project/PySide6-Pdf/>

## Kurulum ve işletim

1. Yönetici/Personel V6.4.2 kuruluyken cihaz kimliğini veya
   \`%LOCALAPPDATA%\AlfaERP\` dosyalarını silme.
2. İlgili uygulamayı tamamen kapat. Yönetici ve Personel setup dosyalarını
   kendi bilgisayarlarında mevcut uygulamanın üzerine kur.
3. Bulut bağlantısı, kitap kodları, sıfırdan başlayan üretim siparişleri,
   envanter alış partileri ve analitiği doğrula.
4. Personel uygulaması kapalıyken arka plan bildirici ile yeni sipariş
   geldiğinde seçilen tonu dinle.
5. PDF klasörü seç ve örnek birkaç kitap için kapakları doğrula.

**Canlı veritabanını yeniden sıfırlama.**
Eski kayıtlara dokunulmaz. Kapaklar ve sesler yalnızca yerel
dosyalarda saklanır; yeni bir Firebase indirme/yazma kotası oluşturmaz.

## Yayın notu

GitHub Actions Windows kurulumlarını üretir, Python sözdizimi ve
SHA-256 hesaplaması yapar. Kullanıcının önceki tercihine göre
otomatik uygulama işlev testleri **çalıştırılmaz**. Gerçek Windows
cihazında ses sürücüsü, PDF içeriği ve kapak görünümü kontrolleri
ayrıca yapılmalıdır.

GitHub ana dalındaki önceki Supabase V6.2.2 sürümü korunmuştur.
GitHub Release'e kalıcı varlık yüklemek için uygun depo/yayın
yetkisi gerekmektedir. Bu yetki sorunu nedeniyle Windows
kurulum dosyaları alternatif Drive teslimiyle de paylaşılabilir.
