# ALFACOPYCENTER Suite v2.0.1 — Sipariş eşitleme yaması

Bu sürüm v2.0.0 üzerine kurulur. Yönetici ERP, Personel ERP, Banner Studio
ve Yazdırma Kontrol Merkezi aynı birleşik Setup.exe içinde kalır.

## Düzeltmeler
- Personel ve Yönetici artık Firebase Realtime Database içinde doğrudan
  /orders dalını da Server-Sent Events ile izler. Sipariş yazımı buluta
  ulaşıp meta/revisions sayaç güncellemesi gecikse bile diğer cihaz
  değişiklik haberi alır.
- Çabuk yapılan Hazırlandı/Kolilendi güncellemeleri 450 ms içinde birlikte
  değerlendirilir. Bir ağ GET işlemi yürürken gelen yeni değişiklik,
  işlem tamamlanınca tekrar okunur. İşlem kaybı yaratacak yarış engellendi.
- Aynı miktar başka cihaz tarafından zaten işlendiyse ek +1 uygulanmaz.
  Böyle bir onay op_id ile bulutta kaydedilir, sonraki denemede yanlışlıkla
  yeniden sayı artırılmaz.
- Sıra bekleyen hareketler ve gerçek çakışmalar kaybolmaz, otomatik
  silinmez veya kullanıcı onayı olmadan tekrar basılmaz.
- Sağ üstteki eskiden kalma "2 geçmiş çakışma" uyarısı artık daimi değildir.
  Yeni bir hata 8 sn görünür ve çevrim içiyse "Bulut bağlı" metnine döner.
  Eski hata kayıtları İşlem Günlüğü/Hata Merkezi'nde korunur.
- Bulut durumunun yanındaki ↻ tuşu mevcut bekleyen işleri silmeden
  siparişleri hemen tekrar okutur.
- SSE bağlantısı kopsa bile 12–15 sn etkin/30–35 sn boşta durum
  kontrolleri ile ve 2–3 dk periyodik kesin tam doğrulama ile onarılır.

## Sınırlar ve veri güvenliği
Gerçek zamanlı gecikme ağ kalitesi, izinler ve Firebase servis durumuna
bağlıdır; sıfır gecikme garanti değildir. Başarısız ve arşivlenen işlemler
kullanıcı onayı olmadan bulutta yeniden oynatılmaz. Rapor/cihaz geçmişi,
mevcut siparişler, yerel cihaz oturumu, envanter ve tasarım arşivleri korunur.
Firebase veri tabanına test komutu gönderilmez.

Bu değişiklik yalnız ALFA ERP senkronizasyonu ve hata belirticisi için
yapılmıştır. Yazdırma programının fiziksel cihaz sınırlamaları aynıdır.
