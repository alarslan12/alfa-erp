# ALFACOPYCENTER Suite v2.0.3 · GitHub güncelleme bağlantısı düzeltmesi

## Güncelleme Merkezi
- GitHub Releases API isteği başarısız olursa artık genel ve belirsiz bir hata yerine HTTP, DNS, zaman aşımı, proxy veya sertifika probleminin nedeni gösterilir.
- API'ye erişilemiyorsa yalnızca GitHub'ın **resmî** `github.com/alarslan12/alfa-erp/releases/latest` adresi alternatif olarak kullanılır.
- İndirilmiş Windows kurulumunun SHA-256 doğrulaması ve güvenilir alan adı kontrolleri kaldırılmamıştır.
- Uygulama içinden tek onayla indirme, doğrulama, kurma ve yeniden başlatma sürdürülür.

## Korunan özellikler
- Gardrops'ta yeni sipariş fiyatının %90'ı ve bir üst tam TL'ye yuvarlama.
- Banner Studio v3.4 katalog grubu, alt başlık ve sade marka düzenleri.
- Kargonomi entegrasyonu yoktur. Eski sipariş tamamlanma akışı korunur.
- Sipariş, katalog, bulut eşitleme ve yerel veriler silinmez.

## Önemli
Bu sürümün düzeltmesi eski uygulamaya kendiliğinden geçmez. Eski sürüm hem API'ye hem GitHub sayfasına erişemiyorsa **bir kez** GitHub Releases üzerinden kurulum gerekebilir. Sonraki sürümlerde uygulama içinden güncelleme kullanılabilir.

Bu adayın gerçek Windows kurulum testi yapılmamıştır.
