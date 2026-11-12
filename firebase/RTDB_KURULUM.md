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
