# ALFA ERP — Yayınlanmamış geliştirme taslağı

**Durum:** Taslak dal `draft/v112-stock-undo-staff-pdf-settings`.
**Mevcut kararlı sürüm:** v1.1.1; değişmedi. Yeni EXE, yeni GitHub Release
veya canlı Firebase dağıtımı **YAPILMADI**.

## Kullanıcı tarafından talep edilen düzeltmeler

### Yönetici — envanter
- Yeni alım partisi formundaki karanlık/kaymış Windows QSpinBox okları
  kapatıldı; miktar ve maliyet için aynı satırda, her temada okunabilen
  ayrı `−` ve `+` düğmeleri eklendi.
- Envanter kartı → **Ürün ve alım partileri** → bir parti seç →
  **Seçili yanlış alımı geri al**. Yalnızca satış bağlantısı olmayan,
  tamamen kullanılmamış alım geri alınabilir. ETag ile başka cihazın
  güncellemesini ezmez. Kalan stok ve önerilen son alım maliyeti
  yeniden hesaplanır; önceki parti kaydı `voided_at/by/reason` ile
  korunur, asla hard-delete yapılmaz.
- Stok 0 ise → **Envanterden çıkar**; ürün genel katalogda ve
  satış/alım geçmişinde kalır. Yeni alım partisi eklendiğinde envantere
  tekrar girer.
- **Katalogdan arşivle:** kart ayrıntısından erişilir. Stok
  silinmez, ürün aktif listelerde gizlenir. Genel Ürünler →
  **Arşivlenenleri göster** → **Ürünü geri getir** ile açılır.
- Envanterden çıkarılmış ürünün geçmiş satışları analitik rapordan
  düşürülmez.

### Personel — sağ üst ayarlar pillbox
- Ayrı üst panel açık/koyu tema anahtarı, Hata Bildir ve Cihaz
  Yetkisi düğmeleri yerine **⚙ Ayarlar** bulunur.
- **Görünüm ve bildirimler:** açık/koyu/yüksek kontrast, sipariş
  bildirim sesleri, güncelleme kontrolü.
- **Kitap PDF klasörü:** önceki PDF klasörü seçme ve artımlı
  PDF ilk sayfa → JPEG kapak üretme özelliği korunur.
  Yeni **PDF dosyalarını içe aktar** ile birden fazla PDF dosyası
  seçilebilir. Dosyalar yalnız yerelde seçilen klasöre, klasör
  yoksa `%LOCALAPPDATA%/AlfaERP/pdf_ice_aktarilanlar` klasörüne
  kopyalanır. Aynı isimdeki mevcut PDF asla üzerine yazılmaz.
  Uzun kopyalamalar ayrı QThread içinde yapılır, sonra PDF
  taraması/kapak önbelleği güncellenir.
- **Cihaz ve destek:** mevcut Firebase kimlik/yetki penceresi
  ve kategorizasyonlu Hata Bildir ekranına geçiş. Firebase
  yetkileri değiştirilmez.

## Bilinçli güvenlik sınırları
- Satış yapılmış veya kısmen tüketilmiş parti otomatik geri alınmaz;
  önce önceki işlemler incelenir.
- Envanterden çıkarma yalnız stok 0 iken yapılır.
- Hiçbir ürün, stok partisi, satış kaydı veya sipariş silinmez.
- Yeni Firebase Security Rules, Cloud Functions, ek ücretli servis,
  Firestore tabloları veya canlı veritabanı değişikliği gerekmez.
- Kullanıcının hızlı döngü talebi uyarınca **otomatik test çalıştırılmadı**.
  Gerçek Windows görsel/işlev testi ve kullanıcı onayı gelmeden
  birleştirme veya sürüm yayını yapılmayacak.

## Sonraki birikimli güncelleme
Kullanıcı yeni notlar ekledikçe **aynı taslak dal** üzerinden devam edin.
Önceden kararlı `firebase-rtdb-final` kodunu değiştirmeyin.
Her yeni talep geldiğinde PDF/Katalog/Siparişler tasarımını koruyun.
