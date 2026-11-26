# ALFACOPYCENTER Suite v2.1.1 — ERP ayarlar ve bildirim yenilemesi

- Uygulama Ayarları: PDF kitaplığı ve Excel kataloğu eş hizalı kartlarda, görünüm seçenekleri altında. Sekmeler eş yükseklikte pillbox görünümünde.
- Bildirimler & Cihazlar: solda dört Ozan anonsu için ayrı dinleme ve rastgele dinleme; sağda Yönetici cihaz yönetimi veya Personel kendi cihaz bilgisi.
- Otomatik Personel sipariş bildirimi yalnız dört özgün Ozan M4A anonsundan rastgele seçilir. Eski ses seçenekleri, Windows TTS ve uyarı tonu kaldırıldı. Sesler yerel ve çevrimdışı çalışır.
- Üst HUD: eş boyutlu cihaz yetkisi, güncelleme, ayarlar ve mevcut diğer araçlar; renkli bağlantı durumu, dar ekranda ikinci gezinme satırı.
- Yönetici cihaz panelinin Windows QSplitter yerleşimi düzeltildi. PR #39 (https://github.com/alarslan12/alfa-erp/pull/39) son commitinde Windows regresyon ve kapsam kontrolleri başarılı: https://github.com/alarslan12/alfa-erp/actions/runs/45875218104. Önceki başarısız test nedeniyle kalite kapısı atlanmadı.

## Koruma ve dağıtım
Personel, Yönetici, Banner Studio ve Print Surveillance tek ortak kurulumda kalır. Diğer uygulamaların iş mantığı, siparişler, yerel arşivler, cihaz kimlikleri, canlı Firebase Rules ve Hosting değiştirilmez. Gerçek Windows cihazında ses çıkışı ve canlı Firebase yetkisi ayrıca kullanıcı ortamında doğrulanmalıdır.

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_1_1.exe`. GitHub Release dosyası ve başarılı build doğrulanmadan yayın tamamlanmış sayılmaz.
