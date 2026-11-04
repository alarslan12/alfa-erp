# ALFA ERP V6.1.8 — Yönetici Girişi Donması Onarımı

## Gerçek sorun
V6.1.7 yönetici giriş akışı iki uzak hizmete bağımlıydı: Supabase Auth giriş doğrulaması ve Edge Function `admin_status` erişimi. Canlı kayıtlarda parola doğrulaması 200 yanıtı verirken ikincil Edge isteği ağ düzeyinde tamamlanmıyordu. Dahası ikinci çağrı Qt GUI iş parçacığında 25 saniye kadar bekliyordu. Bu yüzden doğru e-posta/şifre ile giriş formu donuyor ve genel ağ/işlem kuyruğu hatası gösteriyordu.

## Düzeltmeler
- E-posta/parola doğrulaması Supabase Auth üzerinde kalır.
- Yönetici rolü doğrudan PostgREST'in kullanıcıya özel RLS politikaları ile **iki küçük SELECT** sorgusundan doğrulanır. `admin_status` Edge isteği girişin ön koşulu değildir.
- Yetkisiz, pasif veya viewer rolündeki kullanıcılar reddedilir. Yetki atlaması ya da gömülü yönetici şifresi eklenmez.
- Giriş ve bağlantı testleri Qt arayüzünde değil, ayrı QThread üzerinde çalışır. Pencere ağ gecikmesi sırasında etkileşime açık kalır.
- Giriş penceresi ancak çalışan QThread tamamen sonlandıktan sonra kapatılır; Qt erken iş parçacığı kapatma sorunu giderildi.
- Temiz kurulum sonrası yönetici cihaz anahtarı yoksa, cihazı yeniden eşleştirme çağrısı da GUI dışında 8 saniyelik sınırlı istekte yapılır.
- Eğer Auth ve RLS geçer ama Edge erişilemezse yöneticiye ait kimlik doğrulaması başarılı kalır; arayüzde cihazın henüz eşleşmediği açıkça gösterilir ve siparişlerin buluta yazılabilir olduğu iddia edilmez.
- Hata mesajlarında yönetici Edge bağlantı sorunu ile gerçek sipariş gönderim kuyruğu birbirinden ayrılır; DNS/SSL/zaman aşımı ayrıntıları gösterilir.
- Siparişler, envanter, cihaz yetkileri, hazırlama kuyruğu ve bulut kayıtları korunur.

## Doğrulamalar
- Windows 2022 üzerinde 36 çevrimdışı birim/GUI/protokol testi başarıyla tamamlandı.
- Doğrudan RLS doğrulama, arka plan giriş iş akışı ve cihaz eşleştirmesi için ilave regresyon kontrolleri.
- Yönetici ve personel EXE paketlenmiş açılış testleri; kitap/ekran doğrulaması.
- Uygulama testlerinde kullanıcının gerçek parolası kullanılmadı; Supabase üzerinde gerçek bir yönetici oturumuyla giriş testi **henüz yapılmadı**.

## Kurulum
Yönetici ve personel uygulamalarını tamamen kapatıp mevcut kurulumların üstüne V6.1.8 Setup.exe yükle. Yerel veri klasörünü silme ve ALFA_TEMIZ_KURULUM.bat dosyasını yeniden çalıştırma.
Önce yönetici girişini dene. Hâlâ Edge ağ sorunu çıkarsa hata artık neye erişilemediğini gösterecek. Yönetici cihaz eşleştirilmeden yeni sipariş/ilerleme işlemlerini buluta yazıyor gibi davranma.

## Bilinen sınır
Supabase Edge Function'a kullanıcının bilgisayarından ağ erişimi gerçekten engelleniyorsa, bu sürüm onu kendiliğinden açmaz: yalnızca yönetici girişini Edge'den bağımsız kılar ve donmayı önler. Yönetici cihaz eşleştirme ve sipariş senkronizasyonu için Edge yolunun erişilebilir olması gerekir.
