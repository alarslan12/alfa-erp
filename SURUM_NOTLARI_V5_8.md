# ALFA ERP V5.8 - Genel beta / teslim notları

## Temel değişiklikler
- Personel sipariş düzenleyicisinde eski yerel sipariş hatası, bulut nesil kimliği ile ele alındı.
- Kullanılan Supabase `alfa-erp` çalışma alanındaki test siparişleri, sipariş satırları, muhasebe günleri ve test günlükleri bir kez sıfırlandı; numaralandırma **1**'den başlar. Kitap kataloğu ve daha önce eşleştirilmiş bilgisayarlar korunur.
- V5.8 ilk eşitlemede eski yerel test siparişlerini `%LOCALAPPDATA%\AlfaERP\arsiv_eski_test_kayitlari` dizinine taşır.
- Masaüstünde siparişler/analitik/muhasebe bilgileri ortak Supabase kayıtlarından yaklaşık 4 sn'de yenilenir.
- Yönetici paneli `Yönetim` düğmesiyle açılır: cihazlar, sipariş yönetimi, analitik, Excel katalog yükleme, merkezi işlem günlüğü, sistem ayarları, envanter için ayrılan alan.
- Excel `.xlsx` dosyasındaki kodlar bulut katalog kaydıyla eşleştirilir. Var olan ID'ler korunur, kaldırılan kitaplar pasifleştirilir, yeni kitaplar eklenir.
- Mobil katalogda public kitap okuma ve sipariş yazma, sunucu işlevi ve basit oran sınırlaması ile kullanılabilir. Netlify paketini ayrıca deploy etmek gerekir.
- Personel analitik ekranı mevcut parola ile yerel olarak korunur, gerçek sunucu tarafı yetkilendirme değildir; merkezi loglar yalnızca yönetici JWT yetkisiyle sunulur.
- Her personel bilgisayarı için tek kullanımlık ve süre sınırı olmayan *ayrı bir eşleştirme bileti* üretilir. Cihaz anahtarı Windows DPAPI ile yerel saklanır. Cihazlar yönetici panelinden iptal edilebilir.
- Çalışan paketine yönetim penceresi ve yönetici log arayüzü eklenmez.

## Kurulum - yönetici laptopu
1. Önceki `%LOCALAPPDATA%\AlfaERP` klasörünü yedekleyin; V5.8 aynı profil verilerini devralır.
2. Tam proje ZIP dosyasını yeni klasöre açın. `KUR_WINDOWS.bat`, ardından `BASLAT_WINDOWS.bat` çalıştırın.
3. Üstteki `Yönetim` düğmesini kullanın; kendi Supabase yönetici hesabınızla giriş yapın.
4. İstediğiniz Excel'i `Excel katalog aktarımı` bölümünde seçip doğruladıktan sonra buluta yayınlayın.
5. `Bilgisayarlar` ekranında her personel cihazı için yeni kurulum paketi oluşturun.

## Personel için Windows Setup.exe üretimi
1. **Yönetici laptopunda** oluşturulan personel ZIP'ini yeni klasöre açın.
2. Derlemek için yönetici laptopunda Windows/Python 3.13 ve Inno Setup 6 bulunmalıdır.
3. `URET_SETUP_EXE_WINDOWS.bat` dosyasını çift tıklayın. Bu betik PyInstaller ile iki bağımsız Windows programı derler ve Inno Setup ile **tek kurulum EXE** paketler.
4. `output\ALFA_ERP_Personel_Setup_V5_8.exe` dosyasını **yalnızca tek personele ait tek bilgisayara** gönderin.
5. Personel bilgisayarında Python veya pip kurulu olması GEREKMEZ. Setup masaüstü kısayolunu ve Windows açılışında çalışan sipariş bildiricisini yerleştirir.
6. Her farklı bilgisayar için yönetici panelinde yeni bilet/kurulum paketi oluşturun. Eski bir bilet başka bir bilgisayarda kullanılamaz.

**Not:** EXE derlemesi yalnızca gerçek Windows bilgisayarında yapılabilir. Bu ZIP, çalıştırılabilir kurulum dosyasının *Windows üzerinde oluşturulması için tüm kaynakları ve betiği* içerir; hazır derlenmiş bir EXE içermez.

## Mobil kataloğu güncellemek
`ALFA_ERP_V5_8_MOBIL_NETLIFY.zip` içeriğini mevcut Netlify sitenize yayımlayın. Yeni web sayfası herkese açık katalog ve sipariş uç noktalarını kullanır; kitapları 30 saniyede bir ve sayfa tekrar odaklandığında yeniler. Web uygulamasını yeniden deploy etmek, **gelecekteki Excel yüklemelerinde gerekli olmayacaktır**.

## Canlı kullanım için sınırlar
- Windows üzerinde gerçek kurulum ve Supabase işlem testleri, kullanıcı isteği doğrultusunda ÇALIŞTIRILMADI. Bu bir beta teslimidir; önce bir personel bilgisayarında pilot kurulum yapın.
- Gerçek websocket / milisaniye anlık yayın yerine ~4 sn masaüstü ve ~30 sn mobil aralıklı otomatik yenileme vardır.
- PDF klasörü ve dosyalar cihaz bazlı yereldir; Supabase'e otomatik PDF dosyası yüklemesi yapılmaz.
- Envanter modülü sadece geleceğe ayrılan yer tutucu ekrandır, stok sistemi henüz uygulanmadı.
- Public siparişlerde sunucu tarafı oran sınırlaması bulunur ancak yüksek trafikli kullanımda CAPTCHA/Turnstile önerilir.
- Yönetici hesabının giriş bilgileri personel paketine GİRMEZ. Parola kodun açık metni değil özeti olarak dağıtılır; yerel parola kilidi güçlü sunucu yetkilendirmesinin yerine geçmez.
