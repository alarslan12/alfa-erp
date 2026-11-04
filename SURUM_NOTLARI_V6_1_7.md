# ALFA ERP V6.1.7 — Yönetici Girişi ve Personel Cihaz Eşleştirme Düzeltmesi

Bu bakım sürümü, V6.1.6 temiz kurulumunun ardından görülen iki başlangıç sorununu giderir. Siparişler, envanter, kitaplar, kuyruk ve sunucu veritabanı bu sürümde sıfırlanmaz.

## Yönetici girişi
- E-posta ve parola Supabase Auth ile doğrulanır; mevcut yönetici rolü değiştirilmez.
- Oturumdan sonra dört ayrı, ağ bağlantısı kesilirse başarısız olabilen tablo sorgusu yerine tek bir Edge Function `admin_status` çağrısı kullanılır.
- `admin_status` yalnızca gerçek oturum JWT'si ve aktif `workspace_members.role='admin'` kaydını doğruladıktan sonra başarılı cevap verir.
- Geçici DNS/SSL/zaman aşımı bağlantı sorunlarının ayrıntısı kullanıcı dostu mesajla açıklanır; oturum açma bir kez yeniden denenir.
- Yönetici Girişi penceresine `Supabase bağlantısını kontrol et` düğmesi eklendi. Bu düğme parolaya gerek olmadan Auth sunucusuna HTTPS erişimini kontrol eder.

## Personel ilk kurulumu
- Yeni, genel Personel Setup.exe artık zorunlu `kurulum_bilgisi.json` dosyası arayıp uygulamayı hata ile kapatmaz.
- Otomatik eşleşme bileti varsa eski yöntem korunur; yoksa ilk açılışta 48 karakterli tek kullanımlık kodu girmek için modal pencere açılır.
- Yönetici uygulamasında `Ayarlar → Bilgisayarlar → Yeni cihaz kodu` ile kod üretilebilir.
- Girilen kod Supabase üzerinden doğrulanır. Başarılı eşleşme DPAPI ile cihazın Windows kullanıcı hesabında saklanır ve normal açılışta tekrar sorulmaz.
- Eşleşme başarıyla tamamlanana kadar sipariş uygulaması bulut bağlantısı varmış gibi çalıştırılmaz.
- Yönetici / personel kurulumlarını yeniden paketlemeden sonraki yeni personel bilgisayarlarını manuel kodla eşleştirmek mümkündür.

## Güvenlik ve testler
- Kullanıcı şifresi ve tek kullanımlık cihaz kodu kaynak koda veya Setup.exe içine gömülmez.
- Supabase servis anahtarı Windows istemcilerine yerleştirilmez.
- Windows Qt GUI testlerinde yeni cihaz eşleştirme, geçersiz kod reddi, tek istekle yönetici rolü doğrulama ve internet bağlantı testi kontrol edilir.
- Paketlenmiş iki Windows EXE açılış kontrolünden geçirilir.

## Kurulum
1. Yönetici ve personel uygulamalarını ve sistem tepsisindeki bildirim ajanını kapat.
2. V6.1.7 yönetici Setup.exe'yi kendi bilgisayarına, personel Setup.exe'yi diğer bilgisayara mevcut kurulumun üzerine kur. Eski verileri silme, temizleme BAT'ini tekrar çalıştırma.
3. Yönetici ekranında sorun olursa `Supabase bağlantısını kontrol et` düğmesine bas ve gerekirse VPN / güvenlik duvarı / DNS sonucunu incele.
4. Yönetici girişinden sonra `Ayarlar → Bilgisayarlar → Yeni cihaz kodu` seç ve verilen kodu personel uygulamasındaki yeni eşleştirme penceresine gir.
5. Siparişler buluttan geldikten sonra iki bilgisayarda küçük bir sipariş hareketini kontrol et.

## Sınırlama
Bu sürümde kullanıcıların iki gerçek Windows bilgisayarı üzerinden uzun süreli eşzamanlı çalışması yeniden ölçülmedi. Bağlantı tanısı, zaman aşımı veya DNS hatası gösterirse yerel ağ/yönetilen güvenlik duvarı ayrıca incelenmelidir.

Bu yayınlama komiti, Windows birim/GUI testleri geçerse yönetici ve personel Setup.exe dosyalarını otomatik üretir. [build-installers]
