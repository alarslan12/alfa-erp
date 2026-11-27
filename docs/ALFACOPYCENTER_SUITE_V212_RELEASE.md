# ALFACOPYCENTER Suite v2.1.2 — Üst çubuk ve sekme etiketi düzeltmesi

## ERP Personel / Yönetici
- Mükerrer Duyurular düğmesi kaldırıldı. Tek Duyurular ve Güncelleme Merkezi sürüm geçmişini ve güncelleme denetimini korur.
- Üst araçlar 48×38, bulut göstergesi 110×38; aynı kapsülde düzenli boşluklar ve hizalama. Personel hata bildirme düğmesi korunur.
- Bildirimler & Cihazlar sekmesinde Qt'nin ampersand karakterini klavye kısayolu olarak yorumlaması düzeltildi; kullanıcıya doğru etiket görünür.
- PR #41 (https://github.com/alarslan12/alfa-erp/pull/41) Windows regresyon ve kapsam kontrolleri başarılı (https://github.com/alarslan12/alfa-erp/actions/runs/46007655421).
- Önceki dört özgün Ozan anonsu ve diğer ERP özellikleri korunur.

## Ortak Suite
Personel, Yönetici, Banner Studio ve Print Surveillance tek Windows kurulumunda kalır. Diğer uygulamaların iş mantığı, canlı Firebase Rules/Hosting, siparişler, cihaz kimlikleri ve kullanıcı arşivleri değiştirilmez. Gerçek kullanıcı ekranı ve ses çıkışı ayrıca doğrulanmalıdır.

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_1_2.exe`. Gerçek GitHub Release dosyası ve başarılı Windows build doğrulanmadan yayın tamamlanmış sayılmaz.
