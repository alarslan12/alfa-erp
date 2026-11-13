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
