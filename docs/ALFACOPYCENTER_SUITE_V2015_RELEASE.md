# ALFACOPYCENTER Suite v2.0.15 — Geçmiş, Excel ve kayıt temizliği

- Personel/Yönetici Duyurular ve Güncelleme Merkezi artık v1.x ve v2.x
  sürüm geçmişini paket içinde tutar; internetsiz de okunur.
- Onaylı Personel cihazı artık Ayarlar → Excel Katalog sekmesinde .xlsx
  dosyasını önizler ve kullanıcı onayıyla ortak Firebase kataloğuna aktarır.
  Güncel Excel, tüm yetkili cihazlar ve mobil katalog için geçerli olur.
- Yönetici → Bilgisayarlar varsayılan olarak yalnız aktif cihazları gösterir.
  Pasif kayıtlar isteğe bağlı açılır ve açık onayla Firebase'den temizlenir.
  Kullanımdaki owner cihazı ve diğer aktif cihazlar temizlenmez.
- Yönetici → Hata Merkezi tek raporu silmeye veya yalnızca incelenmiş,
  görünen hata kayıtlarını temizlemeye izin verir. İncelenmemiş hatalar
  toplu temizlikte korunur.
- Dört bileşenli Suite Setup, Firebase RTDB, çevrimdışı sipariş kuyruğu,
  Banner Studio tasarım arşivi, Print Center geçmişi ve Yönetici kurulum
  şifresi korunur.
- Firebase Rules tarafında onaylı staff için katalog yazma ve owner için
  güvenli kayıt temizleme yetkileri eklenmiştir. Bu kurallar GitHub
  commit'iyle otomatik olarak canlıya yayımlanmaz. Yetkili proje operatörü
  Cloud Shell üzerinden kuralları doğrulayıp ayrıca deploy etmelidir.

## İşletim uyarısı

Personel Excel aktarımı aktif personel UID'sini gerektirir ve internet yoksa
katalog yazmaz. Kayıt temizleme kalıcıdır, işlem öncesi onay istenir.
Kullanıcı dosyaları, sipariş veritabanı ve cihaz kimliği dosyaları silinmez.
