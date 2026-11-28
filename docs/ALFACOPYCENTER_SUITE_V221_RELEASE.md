# ALFACOPYCENTER Suite v2.2.1

## Yerel Derlemeler: kapaklı ayrıntı, düzenleme ve sade numaralandırma

- Yönetici Siparişler üst barında tek Yerel Derlemeler sekmesi; açık ve bitmiş gruplar içeride, ayrı toplamları korunur.
- Sipariş ayrıntıları kapaklı yatay kitap şeritleri, SB/RNK adet ve sayfa bilgileriyle gösterilir; tema kontrastı düzeltilir.
- Referans, ciro, not ve kitaplar düzenlenebilir; kitap ekleme/çıkarma ve adet kontrolü. Onaylı silme kayıtları listeden kaldırır, SQLite geçmişini korur.
- D001, D002 numaraları ve D001.zip dosya adları; mevcut kimlikler ve eski ZIP dosyaları korunur. Baskı içeriği değişirse eski ZIP göstergesi temizlenir.
- ERP PR #47 kapsam ve Windows regresyon testleri başarılı; canlı Firebase, Personel iş akışı ve diğer uygulamaların iş mantığı değiştirilmedi. Gerçek kullanıcı bilgisayarında manuel ekran testi yapılmadı.

## Kurulum ve veri koruma

Tek Windows Setup: ALFACOPYCENTER_Suite_Setup_V2_2_1.exe. Mevcut AppId, kurulum yolu ve kullanıcı arşivleri korunur. Yerel SQLite deposu mevcut kayıtları ve kimlikleri koruyarak güncellenir. Silinen kayıtlar fiziksel olarak silinmez; geri yükleme arayüzü bulunmaz. Bitmiş kayıt düzenlenirse bitiş durumu korunur. Eski ZIP dosyaları yeniden adlandırılmaz veya silinmez. Aynı dosya adı varsa benzersiz ad kullanılır. Canlı Firebase Rules/Hosting değiştirilmez.

ERP kaynak PR: https://github.com/alarslan12/alfa-erp/pull/47
