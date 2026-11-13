# ALFACOPYCENTER Suite v2.0.16 — Analitik erişim güvenliği

- Personel uygulamasında PIN kabul edildikten sonra analitik ekranının
  açılışında yaşanabilecek Qt/QThread pencere kapatma yarışına karşı
  GUI-thread slotları ve güvenli thread lifecycle kullanılır.
- Analitik rapor tekrar çizimi sırasında iç içe yeniden çizim ve
  görünmeyen viewport değişimlerinde gereksiz render engellenir.
- Personel PIN başarılı akışı, Analitik grafik resize ve rapor yenilemesi
  Windows kalite kontrolündeki regresyon kapsamına alınır.
- Suite Personel, Yönetici, Banner Studio ve Print Center ile güncelleme
  merkezi aynı paket sürümünü kullanır.
- Cihaz yetkileri, Firebase veritabanı, yerel sipariş kuyruğu ve diğer
  kullanıcı dosyaları değiştirilmez.

Not: C++/Qt NativeCrash kaynakları farklı olabilir. Tam kök neden için
Windows cihazındaki %LOCALAPPDATA%\\AlfaERP\\logs\\fatal_error.log ve
last_error.txt dosyaları incelenmelidir. Kullanıcı verisi içeren özel
dosyalar yüklenmeden önce gözden geçirilmelidir.
