# ALFA ERP v2.0 — Print Surveillance / Yazdırma Kontrol Merkezi

**Durum:** YAYINLANMAMIŞ, DRAFT geliştirme dalı.
**Kaynak dal:** `draft/v200-print-surveillance`
**Taban:** `draft/v112-stock-undo-staff-pdf-settings` (önceki envanter/PDF/Ayarlar
taslağını içerir).
**Kararlı:** `v1.1.1` DEĞİŞMEDİ; GitHub Release, Setup.exe, Firebase
Security Rules, canlı siparişler ve envanter **değişmedi**.

## Amaç

Windows'un tek satırlık yazdırma kuyruğunu, tüm kullanıcının erişebildiği
yerel ve bağlı yazıcılar için hafızalı, kitap/baskı modu odaklı ve
özelleştirilebilir bir üretim kontrol ekranına dönüştürmek.

Spooler bir **kaynak**, ERP geçmişi ve üretim aşamalarını daima ayrı
tutan güvenli bir **gözlemci** olacak. İzleme, Windows hizmetini,
sürücüyü, spool dizinini veya baskı işini gizlice değiştirmeyecek.

## İlk yazılan altyapı — yalnız taslak

- `alfa_print_monitor.py`: yerel Windows WinSpool API,
  `EnumPrintersW(PRINTER_INFO_4W)` ve `EnumJobsW(JOB_INFO_2W)`.
  Her yazıcıdaki kuyruk sırası, belge adı, durumu, yollanan veri boyutu,
  Windows'un bildirdiği sayfa sayacı ve sürücünün varsa verdiği
  renk/siyah-beyaz tercihine erişir. Kullanıcının görme yetkisi
  olmayan işlere ayrıcalık yükseltme uygulanmaz.
- `PrintMonitor`: Win32 çağrıları PySide6 GUI dışında QThread'de
  gerçekleştirir, yaklaşık 3 saniyede bir yerel durum örneği alır.
  Ağ bağlantısı veya sürücü cevapsızlığı GUI'yi doğrudan kilitlemez;
  ancak çok uzun bloklanan Win32 RPC çağrıları için ayrı işlem
  yalıtımı sonraki fazda gereklidir.
- `PrintJournal`: `%LOCALAPPDATA%/AlfaERP/print_monitor/print_history.sqlite3`
  altında **SQLite WAL** geçmişi. Yeni iş, durum değişimi, Windows sayfa
  sayacı değişimi, spool boyutu büyümesi ve kuyruğun kaybolması kaydedilir.
  Aynı işler her anlık taramada yeniden yazılarak disk şişirilmez;
  otomatik silme uygulanmaz.
- Kuyruktan kaybolan iş **başarılı yazdırıldı sayılmaz**:
  `kuyrukta_yok / fiziksel sonuç bilinmiyor`. Erişilemeyen ağ
  yazıcılarının işleri otomatik tamamlanmış/iptal edilmiş gösterilmez.
- Müdahale, offline, kağıt yok, engellenen iş ve büyük spool için
  Windows masaüstü uyarısı; 4 dakika Windows sayacı değişmeyen iş için
  *"Sayaç değişmedi, gerçek baskıyı kontrol et"* uyarısı.
  Bu, baskının kesin durduğu anlamına gelmez.
- `ekran_yazdirma.py`: ALFA ERP üstündeki **Yazdırma** sekmesi,
  her yazıcı için ayrı panel, yatay/dikey/ızgara yerleşim, sürükle-bırak
  yazıcı sırası, anlık durum, yerel iş geçmişi, olay günlüğü,
  uyarı eşiği, kitap adı ve SB/RNK etiketinin **kullanıcı tarafından
  doğrulanarak** kaydedilmesi.
- Personel/Yönetici PDF, Envanter, Katalog ve Siparişler sekmelerinin
  mevcut indeksleri ve Firebase verileri korunur. Yeni modül
  `QStackedWidget` içerisinde index 5 olarak eklenir.

### Kesin olmayan / mevcut teknolojiyle yapılamayan iddialar

1. Windows `JOB_INFO_2.PagesPrinted` bir spooler sayaç değeridir:
   **0 veya gecikmeli** olabilir. Kopya, çift taraf, N-up, PDF sayfa
   aralığı gibi ayarlar sonucu bu değer özgün PDF sayfa numarasıyla
   bire bir aynı olmayabilir.
2. `JOB_STATUS_COMPLETE/PRINTED` yazıcının tüm kağıtları gerçekten
   çıkardığını **kanıtlamaz**; bazı port monitorleri iş yazıcıya
   aktarıldığı anda bu bayrağı verir.
3. Spooler iş adı her zaman PDF dosya yolu değildir. Adobe Reader,
   tarayıcı, sürücü veya baskı sunucusu belge adını değiştirebilir.
   ALFA'nın üretim işleri için **özel job metadata köprüsü**
   olmadan hangi kitabın SB/RNK olduğu otomatik kesin bilinemez.
4. Spooler kaybolan işi fiziksel olarak yazıcıda tutuyor olabilir:
   **Windows kuyruktan silindi ≠ baskı durdu**. Otomatik yeniden yazdırma
   çift baskı riskidir; uygulanmaz.
5. Bilgisayar kapalıyken uygulama Windows Spooler'ı izleyemez.
   Açılışta eldeki geçmiş ile şu anki spool durumu karşılaştırılabilir,
   ancak kapalıyken gerçekleşen her baskı olayı geri getirilemez.
6. Ağ yazıcısı devre dışıysa Win32 çağrıları gecikebilir. Olay
   bildirimlerine bile tüm uzak yazıcılarda güvenilmez.
7. Spool bellek/veri boyutu Windows iş boyutudur. PDF dosya boyutu veya
   bellekteki gerçek sürücü render yükü değildir.

## Kalan alt sistemler / tam platform entegrasyon planı

### A. Güvenilir gözlem ve kalıcı geçmiş [temel kod yazıldı; test edilmedi]
- Yerel spooler çoklu yazıcı; iş sırası, belge adı, durum, boyut ve
  Windows ilerleme sayacı.
- Dinamik görünüm; yerel kullanıcı tercihleri; Excel veya Firebase
  sipariş geçmişini değiştirmeyen SQLite kayıtları.
- Uyarı seslerinin ayrı yönlendirme/tekrar filtreleri ve kötü durum
  iş akışlarının Windows gerçek cihaz üzerinde doğrulanması gerekir.

### B. Olay tabanlı gerçek zaman ve arka plan ajanı [planlandı]
- `FindFirstPrinterChangeNotification` /
  `FindNextPrinterChangeNotification` ile olay tetiklemeli güncelleme,
  aralık kontrollü yeniden uzlaştırma. Uzak yazıcıların güvenilirlik
  sınırlarında fallback.
- İsteğe bağlı, oturum açınca başlayan kullanıcı yetkili
  `AlfaPrintAgent.exe`; yönetici yetkisi/servis kurma zorlaması yok.
  Bir Windows hesap/cihazında tek izleyici; ALFA ERP kapalıyken bile
  o hesaba ait yazdırma geçmişini sürdürebilme.
- Windows PrintService/Operational olayları ve hizmet yeniden başlama
  tespitleri; ancak Windows event ID tek başına kağıt çıktısını kanıtlamaz.
- Remote spooler RPC bloklamasına karşı ayrı işlem izolasyonu,
  kaynak/kuyruk/SQLite sınırları, veri bozulmasında kurtarma.

### C. ALFA üretim işi / PDF kimlik köprüsü [planlandı]
- ALFA içinden yazdırılan her kitap için değişmez `print_task_id`,
  sipariş ve kitap kodu (yerel metadata), kaynak PDF fingerprint,
  hedef yazıcı, SB/RNK, kopya sayısı, sayfa aralığı, duplex/N-up
  bilgileri, Windows `JobId` eşlemesi.
- Doğrudan PDF spooling yapılmadan önce kullanıcı onayı / doğru
  kurulum/driver parametreleri. Başka uygulamalardan gelen baskılar
  yine izlenir, ama kimlik bilgisi **tahmini** etiketlenir.
- Her yazıcı için ayrı *planlanan sıradaki işler* listesi:
  henüz spooler'a yollanmamış kitaplar dahil. Yeniden başlamada
  "planlandı / spoolda / kayboldu / fiziki teyit bekliyor" ayrımı.

### D. Fiziksel yazıcı telemetrisi [donanım bazında planlandı]
- Destekleyen modeller için yerel ağda **IPP / SNMP /
  üretici SDK** ile gerçek cihaz durumu (kağıt/toner/kapak/toner
  ve varsa aktif iş/sayfa/çıktı sayaçları).
- Üreticinin iş kimliğini Windows `JobId` ile ancak **doğrulanabilir
  eşleştirme** varsa bağla. Destek yoksa en son gerçek PDF sayfası
  `Bilinmiyor` diye gösterilir. Kağıt üstündeki içerik ve baskı
  kalitesi kamera/tarama ya da cihazın açık telemetrisi olmadan
  kesin anlaşılmaz.

### E. Yetkili kontrol ve hata sonrası kurtarma [planlandı]
- `SetJob` ile **duraklat / sürdür / manuel sil** (yalnız
  Windows'un gerçekten izin verdiği kullanıcı/işlerde, ikinci
  onay ve tüm işlemler için audit).
- Baskıyı tekrar gönderme ayrı onay ve önceki işin yazıcıda
  devam etmediğinin teyidi ile; **otomatik yeniden basma yok**.
- Yazdırma hizmetini yeniden başlatma, tüm spool klasörünü
  boşaltma, korumalı servis/driver izinlerini yükseltme gibi
  yıkıcı işlemler yapılmaz. Windows spooler izinleri aşılmaz.
- Elektrik/ağ kesintisinden sonra "ne gözlemlendi / ne belirsiz"
  listesi; operatörün her işi tek tek doğrulamasına imkân.

## Ekran düzeni

| Mod | Görünüm |
| --- | --- |
| Kutucuk | Yazıcı başına kart; ekran enine göre 1, 2, 3 sütun |
| Dikey | Yazıcı sıraları yukarıdan aşağı |
| Yatay | Yazıcılar yan yana; yatay kaydırma |
| Sürükle-bırak | Yazıcı kartlarının görüntü sırasını belirleyen modal liste |
| Yerel etiketleme | Windows belge adının üstüne kitap adı ve SB/RNK iş etiketi |
| Geçmiş | Windows kaybolsa da saklanan eski işler ve olay günlüğü |

Gelişmiş serbest panel boyutlandırma, cihaz grupları, odalara göre
yerleşim, filtreler ve kaydedilmiş birden fazla dashboard profili
sonraki geliştirme fazında eklenebilir.

## Gizlilik ve güvenlik

- PDF byte'ları, spool SHD/SPL dosyaları veya içerikleri okunmaz.
- Windows'un sunduğu belge/kitap adları **kişisel bilgi içerebilir**;
  yalnızca yerel Windows hesap dizinindeki SQLite dosyasında tutulur.
- Firebase'e, Google Cloud'a, hata raporlarına veya GitHub'a
  yazdırma iş adları, dosya yolları, şifreler, müşteri detayları
  otomatik **yüklenmez**.
- Önceden var olan yazıcı işi silinmez, yazıcı sürücüsünün
  ayarları veya Windows Print Spooler servisi değiştirilmez.
- Çok cihazlı ortak baskı görünümü ileride **onaylı,
  yetkilendirilmiş ve veri minimizasyonlu** bir senkronizasyon
  özelliği olarak ayrı planlanmalıdır; varsayılan yereldir.

## Kabul ölçütleri (yayından önce)

1. 2-3 gerçek Windows yazıcısıyla eşzamanlı boş/siyah-beyaz/renkli,
   aynı adlı ve büyük PDF baskıları; tüm yazıcılar tek panoda.
2. `PagesPrinted=0` veya `Complete` bildiren sürücülerde
   **fiziksel baskı tamamlandı** diye yanlış mesaj çıkmaması.
3. Sıradaki iş durumu, kullanıcı etiketleri ve panel yerleşimi
   ERP yeniden açıldığında korunur.
4. Uzak yazıcı fişi/ağ bağlantısı kesildiğinde GUI donmaz;
   eski işler otomatik tamamlandı diye işaretlenmez.
5. Çoklu ERP instance, SQLite WAL eşzamanlı erişim, rapor
   birikimi, Windows hızlı yeniden başlama, tray uyarı tekrarları.
6. Windows masaüstü permissions: okuma, job kontrol izni yoksa
   güvenli hata; ekstra yönetici izinleri talep edilmez.
7. Ücretsiz altyapı: yalnız yerel Windows ve Qt, Firebase
   aktarımı ve ücretli servis eklenmez.

**Bu ilk kaynak taslağında hiçbir test yapılmadı ve hiçbir
yükleyici/kararlı sürüm yayımlanmadı.**
Kaynak API notları:
- https://learn.microsoft.com/en-us/windows/win32/printdocs/enumprinters
- https://learn.microsoft.com/en-us/windows/win32/printdocs/enumjobs
- https://learn.microsoft.com/en-us/windows/win32/printdocs/job-info-2
- https://learn.microsoft.com/en-us/windows/win32/printdocs/setjob
- https://learn.microsoft.com/en-us/windows/win32/printdocs/findfirstprinterchangenotification
