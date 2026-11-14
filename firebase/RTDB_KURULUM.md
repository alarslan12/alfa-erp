# Firebase RTDB cihaz kurulumu ve işletim kontrolü

Proje kimliği: \`alfa-erp-8700c\`
Veritabanı: \`https://alfa-erp-8700c-default-rtdb.europe-west1.firebasedatabase.app\`

## İlk kurulum

1. Firebase Console'da Authentication → Sign-in method bölümünde
   Anonymous sağlayıcısının açık olduğunu doğrulayın.
2. Realtime Database → Rules altında \`firebase/database.rules.json\` sürümünün
   güvenle yayımlandığını doğrulayın. Tüm veritabanını herkese açmayın.
3. Yönetici cihazında ALFA ERP açılır; **Cihaz yetkisi** penceresinden
   Firebase UID oluşturulur. Bu UID'nin owner rolü yalnızca
   yetkili proje operatörü tarafından onaylanmalıdır.
4. Personel cihazı kendi UID'sini alır. Yönetici panelinden bu UID
   personel olarak yetkilendirilir. Kişisel bilgileri sohbetlere,
   GitHub'a veya herkese açık dosyalara eklemeyin.
5. Her iki cihazda ilk başarılı eşitleme yapılmalıdır. Yeni cihaz
   henüz eşitlenmemişse çevrimdışı sipariş yazması güvenlik için kapalıdır.

## Çevrimdışı çalışma

- Başarılı ilk eşitlemeden sonra uygulama internet yokken açılır.
- Sipariş işlemleri yerel diske ve tekrar deneme kuyruğuna yazılır.
- Uygulama kapatılsa da bekleyen işlemler korunur.
- Bağlantı geldiğinde önce doğru Firebase çalışma alanı doğrulanır,
  ardından bekleyen işlemler güvenli sırayla gönderilir.
- Aynı sipariş iki cihazda farklılaştırılmışsa çakışma kaydı incelemeye alınır.

## Doğrulanmamış koşullar

Dosya düzeyindeki testler, gerçek bir Firebase projesine bağlanan iki
Windows cihazının uçtan uca testinin yerini tutmaz. Google hesabına
bağlanmadan canlı Auth sağlayıcısının etkinliği, Rules sürümü veya gerçek
sipariş senkronizasyonu uzaktan garanti edilemez.


## Google Cloud Shell üzerinden owner yetkilendirmesi

Suite kurulumunda Yönetici bileşenini seçerken yerel kurulum şifresi girilir.
**Bu şifre Firebase owner yetkisi sağlamaz.** Owner rolünü yalnızca
Firebase projesinin yetkili operatörü Google Cloud Shell'den verir.

1. ALFA ERP Yönetici > Cihaz yetkisi > Cihazı kaydet / kimliği göster
   ekranından yönetici bilgisayarının Firebase UID değerini al.
2. https://console.cloud.google.com/cloudshell/editor?project=alfa-erp-8700c
   adresinden Cloud Shell'i, projede yetkili Google hesabınla aç.
3. Güncel Firebase koduna eriş:

~~~bash
gcloud config set project alfa-erp-8700c
git clone --depth 1 --single-branch --branch firebase-rtdb-final https://github.com/alarslan12/alfa-erp.git alfa-erp-firebase
cd alfa-erp-firebase
python3 -m venv "$HOME/.venvs/alfa-erp-firebase"
source "$HOME/.venvs/alfa-erp-firebase/bin/activate"
python -m pip install firebase-admin
gcloud auth application-default login
~~~

4. Sadece **Yönetici uygulamasında görünen UID** ile önce dry-run,
   ardından gerçek onayı çalıştır:

~~~bash
python tools/rtdb_authorize.py --uid "BURAYA_YONETICI_UID" --role owner
python tools/rtdb_authorize.py --uid "BURAYA_YONETICI_UID" --role owner --apply
~~~

5. ALFA ERP Yönetici'de Yönetici onayını kontrol et ve ardından
   Bağlantıyı başlat düğmelerine bas.

Araç, cihaz kimliğinin daha önce device_requests altında kaydedilmesini
ve veritabanı meta/schema işaretinin rtdb-v1 olmasını bekler.
Mevcut owner üyeliğini otomatik değiştirmez; yeni üye eklemesi yapılır.
Cloud Shell'de depo önceden varsa tekrar klonlamak yerine branch'i
güncelleyebilirsin.

**Önemli:** Firebase Admin yetkisi yalnız proje operatöründe bulunmalı.
Servis hesabı anahtarı, Setup, GitHub veya mesajlaşma platformuna eklenmez.


## v2.0.15 katalog yükleme ve kayıt temizleme kuralları

Yeni Personel Excel yükleme, Yönetici hata temizleme ve pasif cihaz kaydı
silme işlemleri için güncel Firebase Realtime Database Rules yayınlanmalıdır.
GitHub'da kaynak kodun güncellenmesi tek başına Firebase Rules'u değiştirmez.

Yetkili Google Cloud Shell'de doğru projeyi ve Rules farkını inceleyerek:

~~~bash
gcloud config set project alfa-erp-8700c
cd ~/alfa-erp
git checkout firebase-rtdb-final
git pull --ff-only origin firebase-rtdb-final
cd firebase
firebase deploy --only database --project alfa-erp-8700c
~~~

Cloud Shell'de firebase komutu yoksa Firebase CLI kurulumu gerekebilir.
Bu adım canlı Firebase Security Rules'u değiştirir. Mevcut kuralları
Firebase Console'dan yedekleyip farkı kontrol etmeden çalıştırmayın.
Yalnız yetkili staff UID'leri kitap kataloğuna yazabilir. Anonim mobil
ziyaretçiler için katalog yazma yetkisi açılmaz.

## v2.0.17 kitap kodu ve sayfa bilgilerinin kurtarılması

Firebase kataloguna yanlış 508/509/510 isimleri kaydedilmişse önce
Yönetici → Excel kataloğu → Buluta güncelle yoluyla doğru .xlsx dosyasını
seçin. Sunucu verilerinin yedeği alınır ve güncelleme doğrulanır.

Yönetici yüklemesi izin hatası verirse Google Cloud Shell'de:

~~~bash
cd ~/alfa-erp
git checkout firebase-rtdb-final
git pull --ff-only origin firebase-rtdb-final
source .venv/bin/activate
python -m pip install firebase-admin openpyxl
gcloud config set project alfa-erp-8700c
gcloud auth application-default login
~~~

Excel dosyanızı Cloud Shell Files → Upload ile klasöre yükleyin.
Aşağıdaki dosya adını yüklediğiniz Excel ile değiştirmeyi unutmayın.

~~~bash
# Önce yalnızca farkları gösterir; canlı veri değişmez.
python tools/firebase_catalog_repair.py --excel 'kitaplar_sablonu.xlsx'

# Farklar doğruysa açık onayla uygular; önce yedek alır.
python tools/firebase_catalog_repair.py --excel 'kitaplar_sablonu.xlsx' --apply --confirm-project alfa-erp-8700c
~~~

Doğru kaynak Excel örneği: 346 TIPDEMY SST Patoloji (386 sayfa),
508 TIPDEMY Patoloji HT (118), 509 TIPDEMY Patoloji Konu (353),
510 TIPDEMY Protetik SST (192). Bu işlem siparişleri silmez;
eski siparişlerdeki fiziksel kitap tercihini gerektiğinde ayrıca doğrulayın.


## v2.0.29 — Kargo fişleri için kuralların güncellenmesi

- Açık adres sipariş kartındaki Kargo fişi düğmesi: Yönetici PDF yükler/değiştirir, Personel indirip kaydeder. Yönetici de PDF indirebilir ancak kendi indirmesi personel onayı yerine geçmez.
- PDF en fazla 512 KB; özel RTDB alanında tutulur, normal sipariş eşitlemesine dosya içeriği dahil edilmez. İndirme sırasında boyut ve SHA-256 kontrol edilir; başarılı yerel kayıttan sonra yetkili personel UID'si ve zaman bilgisi kaydedilir.
- Fiş yenilendiğinde/eski adres değiştiğinde indirme onayı geçersiz olur. Açık adres siparişi kolileme VE güncel fişin personel tarafından indirildiğine dair kayıt olmadan tamamlanamaz. Mevcut tamamlanmış siparişler geriye dönük zorlanmaz; Dolap/Gardrops korunur.
- Yeni Firebase Realtime Database kurallarının canlı projeye yayımlanması ZORUNLUDUR. Önce her iki uygulamayı güncelle, bekleyen işlemlerin tamamlanmasını sağla, Firebase Console'daki mevcut Rules içeriğini yerel dosyaya yedekle. Sonra v2.0.29 etiketindeki firebase/database.rules.json dosyasını Firebase Console > Realtime Database > Rules bölümüne aktar ve Publish seç. Önce CI emülatör testlerinin ve Windows sürümünün başarıyla tamamlandığını doğrula. Proje: alfa-erp-8700c. Veritabanını veya üyeleri silme. Kurallar uygulanmadıysa fiş yükleme reddedilir.
- Yeni Firebase Storage/Blaze planı gerekli değildir. İnternet bağlantısı gereklidir. İndirme kaydı fiziksel baskının kanıtı değildir; dosya yetkili personel uygulaması tarafından doğrulanıp kaydedilir. Gerçek iki-PC testi ayrıca yapılmalıdır.
