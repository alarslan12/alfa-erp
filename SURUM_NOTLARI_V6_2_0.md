# ALFA ERP V6.2.0 — Girişsiz Açılış, Özel Kurulum ve Analitik PIN

## Kullanım
- Yönetici ve Personel uygulamaları açılışta e-posta, parola veya cihaz kodu sormadan doğrudan ERP ekranını gösterir.
- Bulut yetkisi henüz yoksa uygulama bunu dürüstçe gösterir; yanlışlıkla bağlıymış gibi davranmaz.
- Genel/public Setup.exe ile ilk bulut eşleştirmesi gerekirse üst çubuktaki **Buluta bağla** üzerinden yapılır.
- Bu sürüm için ayrıca hazırlanabilen **özel tek kullanımlık kurulum paketleri**, kurulum biletini yanında taşır. İlk açılışta bilet arka planda otomatik kullanılır; kullanıcıya parola veya token sorulmaz. Bağlantı yoksa bilet korunur ve yeniden denenir.
- Özel bilet `replace_existing=true` içerirse eski veya yanlış cihaz eşleştirmesini günceller. Başarılı eşleşmede bilet dosyası silinir.
- Yetki anahtarları Windows DPAPI ile kullanıcı hesabına özel korunur. Yönetici ve Personel anahtarları ayrı dosyalarda tutulur.
- Kullanıcı bilgisayarına **Python kurulması gerekmez**; Setup.exe bütün gerekli çalışma bileşenlerini içerir.

## Güvenlik
- Supabase'de cihaz rollerine göre yetkilendirme uygulanır: personel anahtarı sipariş operasyonlarında çalışır, yöneticiye özel işlemlerde 403 alır.
- Yönetici cihazı rolü ancak önce kimliği doğrulanmış yöneticinin ürettiği kısa ömürlü `admin_owner_code` biletiyle veya proje sahibine özel, sunucuda güvenli biçimde kayıtlı kurulum biletiyle verilebilir.
- Genel GitHub Setup.exe, public kaynak kod ve EXE içerisine yönetici şifresi, servis anahtarı veya özel cihaz tokeni gömülmez.
- Yönetici ayarları, bilgisayar listesi, envanter güncellemeleri, Excel katalog yüklemesi ve denetim günlükleri artık her açılışta JWT almadan yetkili cihaz anahtarıyla çalışır; sunucu rolü her istekte doğrular.
- İşlem geçmişi, siparişler, ürünler, mevcut personel kayıtları ve eşleştirmeler silinmedi.

## Analitik
- Analitik hem yönetici hem personel için varsayılan olarak kilitlidir.
- İlk kullanımda yönetici **Analitik → Yönetici: PIN oluştur veya değiştir** ile 6–12 rakamlı PIN belirler.
- Personel bu PIN'i yalnızca doğrulayabilir; oluşturamaz veya değiştiremez.
- PIN düz metin veya PIN özeti Setup.exe'de saklanmaz. Sunucu PIN'i tuzlanmış PBKDF2-SHA256 özetiyle karşılaştırır.
- Bir cihazda 5 başarısız denemeden sonra 60 saniyelik PIN deneme kilidi uygulanır.
- PIN internet bağlantılı, yetkili bir cihazda kontrol edilir. Yerel PIN ekranı cihazdaki dosyalara erişimi engelleyen genel işletim sistemi güvenliği yerine geçmez.

## Performans / eşitleme
- Önceki V6.1.6 senkronizasyon iyileştirmeleri, tekrar denenebilir 503 zaman aşımları ve yaklaşık 45 saniyelik yetkili sipariş durumu doğrulaması korunur.
- Uygulama başlangıcı bir Supabase ağ çağrısına bağlı değildir.
- İlk eşleştirme arka planda yürütülür; servis geçici olarak erişilemezse uygulama açılmaya devam eder.
- Bulut bağlantısı sağlanmadan yapılan işlemler için uygulamanın bulut ile eşitlendiği iddia edilmez.
- Arşivlenmiş/eski hatalar ve işlem kuyrukları otomatik topluca silinmez.

## Temiz kurulum
1. Yönetici ve Personel için ayrı, özel kurulum ZIP dosyalarını kendi bilgisayarlarında aç.
2. ZIP içindeki `Setup.exe` ile `kurulum_bilgisi.json` dosyasının **aynı klasörde** olduğunu doğrula; Setup.exe'yi çalıştır.
3. Uygulamayı aç. ERP hemen görünür. Özel cihaz bileti eşleştirmeyi arka planda yapar.
4. İlk bulut eşitlemesi için üst çubukta **Bulut bağlı** yazmasını bekle; çevrimdışı uyarısı varken bulut işlemleri yapılmış sayılmaz.
5. Yönetici uygulamasında Analitik'e gir, bir PIN belirle. Personelde aynı PIN ile Analitik açılır.
6. Eski yerel kayıtlardan sıfırdan başlamak istersen `ALFA_TEMIZ_KURULUM.bat` kullan; önce yedek alır, **Supabase'deki gerçek siparişleri silmez**.

## Sınırlar
- Bilgisayarlarda fiziksel uzun süreli ağ kesintisi testi yapmadan %100 gerçek ortam garantisi verilmez.
- Özel kurulum bileti tek kullanımlıktır; kimseyle paylaşılmamalıdır. Yeniden kurulurken yenisi oluşturulabilir.
- Önceden istenen özgün yapay zekâ anonslarının ve kapsamlı grafik marka yenilemesinin tamamı bu giriş/kurulum sürümünün kapsamında değildir.
