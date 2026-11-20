# ALFACOPYCENTER Suite v2.0.49 — Banner Studio düzenlemeleri

## Yeni Banner Studio v3.17
- Veri Kaynakları'ndaki Excel katalogu, kapak klasörü, kapak ZIP ve JSON yedeği işlemleri Ayarlar → Uygulama Yönetimi bölümüne taşındı.
- JPG indir/PNG indir yerine tek “Dışa Aktar”: PNG, JPG, A4 PDF; Standart/HD/Ultra HD kalite seçimi.
- Windows Masaüstü'nün gerçek konumuna doğrudan kaydetme veya dosya konumu seçme imkânı. Aynı adlı dosya varsa üzerine yazma onayı istenir.
- Dosya adında Tasarım Arşivi'nin A–Z sırasını temsil eden dört haneli numara ve kayıt adı kullanılır: `0001_TasarimAdi.png`. Toplu PNG arşiv indirmeleri aynı global sırayı takip eder.
- Swap iptal, kare kırpma kontrolü, proje aç ve ayrı indirme butonları kaldırıldı.
- Tasarım dili: Vintage Koleksiyon ve Minimal Premium; kapak dizilimi: Akıllı ve Dengeli Sıralar; açılır listeyle seçim.
- Kapak ölçeği %65–100 olarak sınırlandı; %100 teorik üst sınırdır.
- Varsayılan kapak fiyat farkı rozeti ve afiş üstü katalog kodları kaldırıldı; kitap özel fiyat/baskı sağ tıkla yönetilir. Fiyat etiketi taşmayı önlemek için tek satıra ölçeklenir.
- Üst sol uygulama alanında ALFACOPYCENTER şirket logosu gösterilir; banner görseline logo eklenmez.

## Arşiv ve verilerin korunması
- Var olan arşiv tasarımları, yerel kapaklar, Excel kaynakları, kullanıcı ayarları ve taslaklar silinmez.
- Yeni özellikler `809ff9cdcbcde15e2cdcf55d30d3da90800e2505` commit'inde birleştirilen Banner PR #20'den gelir.
- ERP Personel, ERP Yönetici, Mobil Katalog ve Print Surveillance iş mantığı değiştirilmedi.
- Firebase Rules, Hosting, gerçek zamanlı sipariş verileri ve yazıcı geçmişi korunur.
- Tek ortak Inno Setup kurulum/güncelleme akışı ve AppId değişmez.

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_49.exe`.
