# ALFACOPYCENTER Suite v2.2.0

## Yönetici yerel derleme havuzu ve fason baskı takibi

- Yönetici kataloğundan normal sipariş yerine bağımsız yerel Derleme Havuzu'na kayıt.
- Derleme Havuzu ve Bitmiş Derleme Siparişleri gruplarında ayrı toplam ciro, sayfa, kitap ve sipariş sayısı.
- Fason baskı tamamlanınca operatör onayı; yanlış onayda havuza geri alma. Hazırlandı/Kolilendi aşamaları yok.
- Tekli/çoklu ZIP, bağımsız D-00001 numaralandırması ve son ZIP zamanı. ZIP üretimi bitiş onayı sayılmaz.
- Yerel SQLite; Firebase, Personel, genel ciro ve analitik dışında. Normal siparişler ve diğer uygulama iş mantığı korunur.
- ERP PR #45 kapsam ve Windows regresyon testleri başarılı. Gerçek kullanıcı bilgisayarında manuel test yapılmadı.

## Kurulum ve yerel veri

Tek Windows Setup: ALFACOPYCENTER_Suite_Setup_V2_2_0.exe. Mevcut AppId, kurulum yolu ve kullanıcı arşivleri korunur. Personel, Yönetici, Banner Studio ve Print Center aynı pakettedir. Yerel derleme kayıtları owner_derleme/siparisler.sqlite3 dosyasında saklanır; şifreli değildir ve normal ERP JSON yedeğine dahil olmaz. İlk sürümde ayrıntılar salt okunur; sonradan düzenleme/silme eklenmemiştir. Canlı Firebase Rules/Hosting değiştirilmedi.

ERP kaynak PR: https://github.com/alarslan12/alfa-erp/pull/45
