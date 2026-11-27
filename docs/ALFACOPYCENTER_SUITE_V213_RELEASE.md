# ALFACOPYCENTER Suite v2.1.3

## Sipariş düzenleme, akıllı kitap arama ve kare HUD

- Sipariş düzenleme adet kutularının sayı görünürlüğü ve +/- hizalaması düzeltildi.
- Kitap adıyla aramada 6 karakterden sonra 150 ms gecikmeli filtrelenen öneriler; tam kitap koduyla doğrudan ekleme korunur.
- Kitap kartları pencere genişliğine uyarlanan soldan sağa kompakt grid kullanır.
- Personel ve Yönetici ortak 48×48 vektör ikonlu HUD ve 110×48 bulut durumu göstergesi.
- ERP PR #43 kapsam ve Windows regresyon testleri başarılı. Canlı Firebase Rules, Hosting, kullanıcı verileri ve diğer uygulamaların iş mantığı değişmedi.

## Kurulum

Tek Windows Setup: ALFACOPYCENTER_Suite_Setup_V2_1_3.exe. Mevcut kurulum yolu, AppId ve kullanıcı arşivleri korunur. Personel, Yönetici, Banner Studio ve Print Center aynı paket içindedir.

ERP kaynak PR: https://github.com/alarslan12/alfa-erp/pull/43

Canlı Firebase ve gerçek kullanıcı ekranları üzerinde manuel test yapılmadı; Windows otomatik regresyonu geçti.
