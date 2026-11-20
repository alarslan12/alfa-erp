# ALFA Banner Studio Pro — Çalışma durumu

**Sohbet:** Banner Studio. **Repo:** `alarslan12/alfa-erp`, üretim `firebase-rtdb-final`.

**Başlangıç referansı:** Suite v2.0.46 (20.11.2026); güncel GitHub SHA/release'i kontrol et.

**Sahiplik:** `banner_studio/studio_server.py`, `studio_library.py`, `banner_engine.py`, `studio_lifecycle.py`, `static/app.js`, `static/index.html`, ilgili testler.

**Korunacaklar:** Tasarım/kapak arşivi ve şablonlar, yüzde yüz yerel `127.0.0.1` çalışma, arşivden tekrar düzenleme, Excel-kapak eşleşmeleri, yerel çalışma verilerinin yükseleme ile silinmemesi.

**Son tamamlanan iş:** Mevcut Suite v2.0.46 ile ortak güncelleme ve Browser Studio bileşeni; kayıt üzerine güncelleme akışını *kodda yeniden doğrula* (var olduğunu varsayma).

**Aktif PR:** Başlangıçta yok; açık GitHub PR'larını yeniden kontrol et.

**Sıradaki iş / bağımlılık:** Kullanıcı talepleri. Suite sürüm dosyalarına dokunma.

Bu durum kaydını **yalnız Banner sohbeti** kendi feature/fix PR'larında günceller.

## 20.11.2026 — Banner Studio arayüz ve dışa aktarma sadeleştirmesi
- **Dal:** `feature/banner-ui-export-simplification-20261120`; PR açılıyor.
- Veri kaynakları (Excel/kapak ZIP/klasör) ve JSON yedeği → Ayarlar > Uygulama Yönetimi.
- Swap iptal, kare kırpma, proje aç ve ayrı JPG/PNG butonları → kaldırıldı.
- Tek dışa aktarma penceresi: PNG/JPG/A4 PDF, Standart/HD/Ultra HD; Masaüstüne doğrudan yaz veya Windows dosya konumu seç.
- Dışa aktarma isimleri tüm arşivin gerçek A–Z sırası + kayıtlı tasarım adı (`0001_TasarımAdı`) olarak üretilir; tekli ve toplu PNG'lerde global sıra korunur.
- Tasarım dili yalnız Vintage Koleksiyon / Minimal Premium; kapak düzeni Akıllı / Dengeli Sıralar. Ölçek üst sınırı %100.
- Genel kapak fiyat rozeti ve katalog kodları kaldırıldı; kitap özel etiketler sağ tıkla yönetilir ve fiyat metni iki satıra kırılmaz.
- Arayüz sol üst logosu paketli `assets/branding/company.png` kaynağından servis edilir. Banner içine logo çizilmez.
- **Veri riski:** Arşiv ve kapak klasörleri korunur; yalnız kullanıcı onaylı masaüstü dosya yazması yapılır. Firebase/ERP/Mobil/Print dosyaları değişmedi.
- **CI:** PR açıldıktan sonra Workstream scope + Windows regression; Suite v2.0.48 ortak sürüm numarası değiştirilmez, Setup yayınlanmaz.
