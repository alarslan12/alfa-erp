# ALFACOPYCENTER Suite v2.0.21 — Kapak görünürlüğü ve eşleştirme

## Düzeltilenler
- PDF taramasının ürettiği küçük ancak geçerli JPEG kapaklar artık eski 1500 bayt eşiği yüzünden gizlenmez.
- PDF dosya adlarının tam katalog başlığıyla eşleşmesi ve `kapak`/`baski` gibi güvenli ekler desteklenir.
- Otomatik PDF kapak önbelleği v5 ile yenilenir; eski yanlış yönlü veya geçersiz önbellek girdileri yeniden taranabilir.
- Yatay PDF ilk sayfaları −90° döndürülür; manuel kapaklar ve dikey PDF kapakları değiştirilmez.

## Güncellemeden sonra
Personel/Yönetici → Ayarlar → Kitap PDF klasörü → Tara ve kapakları güncelle.

Eksik kitap veya render hatalarında ayrıntı:
`%LOCALAPPDATA%\AlfaERP\alfa_pdf_kapak_tarama_raporu.json`

## Korunanlar
Firebase sipariş ve katalog verileri, Katalog/Siparişler düzeni, Banner Studio arşivi,
Print Center ve personel/yönetici izinleri korunur. Var olan kullanıcı verisi silinmez.

Not: Kullanıcının bilgisayarındaki gerçek PDF dosyaları bu depoda yer almaz.
GitHub Actions paketleme ve doğrulaması geçmeden Setup kullanılmamalıdır.
