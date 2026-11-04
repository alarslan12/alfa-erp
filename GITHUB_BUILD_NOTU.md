# ALFA ERP – GitHub Windows test ve sürüm dağıtımı

**Depoyu mutlaka Private oluşturun.** İşletmenin kitabı/kataloğu kaynak pakete dahildir. `kurulum_bilgisi.json`, Windows cihaz tokenları, sipariş JSON dosyaları ve Supabase gizli anahtarları GitHub'a yüklenmez.

Bu kaynak projenin CI akışı:

- `main` dalına yeni kod geldiğinde: Windows üzerinde Python 3.13, Qt offscreen, katalog/sipariş döngüsü, çevrimdışı kuyruk, hata sınıflandırma ve dosya kontrolü testleri çalışır. Her push'ta Setup.exe derlenmez.
- GitHub Actions sayfasında manuel `Run workflow`: testler başarılıysa 2 Windows `Setup.exe` üretir. Artifacts sekmesinden indirilebilir.
- Bir `v6.1.2` gibi sürüm etiketi push edilince: test + 2 Setup.exe derlenir; başarılıysa private GitHub Release'e eklenir. Normal güncellemelerde sabit AppId ile Windows'ta kurulu uygulama yerinde güncellenir.

## Personel dağıtımı – her PC için yeniden derleme YOK

Genel `ALFA_ERP_Personel_Setup_V6_1_2.exe` tek kez derlenir. İlk kez bağlanacak personel bilgisayarına yönetici uygulamasında **Ayarlar > Bilgisayarlar > Hazır Setup ile personel paketi hazırla** işlemiyle oluşturulan ZIP gönderilir.

ZIP içeriği: aynı Setup.exe + cihaz için tek kullanımlık `kurulum_bilgisi.json`. ZIP açılır, Setup.exe çalıştırılır; kurulum JSON dosyasını bilgisayardaki uygulama dizinine kopyalar ve ilk açılışta eşleştirme gerçekleşir. Ana kullanıcı hesabı veya Python kurulumu gerekmez. Mevcut eşleşmiş PC sonraki sürümde yalnızca yeni Setup.exe ile güncellenir; eski Windows cihaz kimliği saklanır.

**Uyarı:** Her yeni personel bilgisayarı için yeni bir defalık aktivasyon kodu gerekir. Kodu GitHub Repository Secrets'a dahi eklemeyin; artık derleme sırasında gerekli değil. Bilet dosyalarını üçüncü kişilerle paylaşmayın.

Bu test paketi gerçek Windows üzerinde CI çalıştırılınca rapor verir. CI testleri **üretim Supabase siparişlerini değiştirmez**. Sunucuyla gerçek iki-PC gecikme testi için ayrı test çalışma alanı ve fiziksel cihaz doğrulaması gereklidir.
