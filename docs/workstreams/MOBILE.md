# ALFA Mobil Katalog / Sipariş Takip — Çalışma durumu

**Sohbet:** Mobil katalog. **Repo:** `alarslan12/alfa-erp`, üretim `firebase-rtdb-final`.

**Başlangıç referansı:** Suite v2.0.46 (20.11.2026); GitHub ile canlı Hosting durumu birbirinden farklı olabilir.

**Sahiplik:** `mobil_panel/index.html`, `manifest.webmanifest`, `mobil_siparis_donusum.py`, Firebase Hosting önizleme/production betikleri ve ilgili mobil testler.

**Korunacaklar:** Gerçek kod+kitap isimleri, SB/RNK, Sipariş Havuzu'na doğrudan gönderim, doğru bulut/yerel sipariş numaraları, mobil kompakt açılır-kapanır kitaplar, Firebase Security Rules/authorized mobile tracking.

**Yayın güvenliği:** `tools/firebase_mobile_preview.sh` önizlemesi ayrı; `tools/firebase_mobile_production.sh` canlı Hosting'i değiştirebilir ve **açık onay** gerekir. Kaynak kodun git üzerinde olması canlı siteye yayımlandığı anlamına gelmez.

**Teknik geçmiş notu:** `mobil_panel/README.md` gibi eski Supabase belgeleri güncel Firebase istemcisinin kaynağı değildir; gerçek `mobil_panel/index.html` ve Firebase RTDB yapılandırmasını esas al.

**Aktif PR:** Başlangıçta yok; GitHub üzerinden tekrar kontrol et.

**Sıradaki iş / bağımlılık:** Kullanıcı talepleri. Windows Suite Setup sürümünü bağımsız değiştirme.

Bu durum kaydını **yalnız Mobil sohbeti** kendi PR'larında yeniler.

## 24.11.2026 — Mobil sipariş girişinde yerel geçmiş ve Dolap kodu
- Dal: `feature/mobile-order-history-dolap-code-20261124`; PR: [#29](https://github.com/alarslan12/alfa-erp/pull/29).
- `mobil_panel/index.html`: Dolap kodu son dört hane ayrı blok; kategori açılır menüsü ve hızlı kategori düğmeleri kaldırıldı; cihazda `localStorage` tabanlı son 500 başarılı gönderim kaydı, 50 kayıt görünümü ve cihaz içi mükerrer kod engeli eklendi.
- Kapsam: yalnız bu tarayıcı/cihaz. Önceden girilmiş siparişler geriye dönük alınmaz; farklı cihaz/masaüstü siparişleri kontrol edilmez. Tarayıcı site verisi silinirse geçmiş kaybolur. Yeni Firebase izinleri, sunucu fonksiyonları, merkezi mükerrer koruması veya Rules değişikliği yok.
- Test/CI: test çalıştırılmadı; PR CI durumu ayrıca doğrulanacak. Üretim dalına birleştirilmedi, Hosting'e yayımlanmadı; Suite sürümü değiştirilmedi.

## 25.11.2026 — Mobil sipariş notu hazırlığı (PR #29)
- Mobil sipariş ekranına isteğe bağlı `order_note` taslak alanı eklendi, maksimum 2000 karakter; taslak bu tarayıcının `localStorage` alanında saklanır.
- **Entegrasyon bekliyor:** `firebase/database.rules.json` checkout yolunda `order_note` alanını kabul etmiyor; `alfa_rtdb.py` `_adopt_checkout` mobil istekteki notu siparişe taşımıyor ve `siparis_uyari.make_notice` oluşturmuyor. Bu iki paylaşılan/ERP dosyası Mobil PR kapsamında değiştirilmedi.
- Not içeren siparişin notu kaybolmasın diye gönderim bloke ediliyor; boş not ile mevcut sipariş akışı aynı kalıyor. Not gönderimi/ERP görünümü henüz çalışır ilan edilmemeli.
- Bağımlılık: ERP/entegrasyon sohbetinde mobil checkout `order_note` (0..2000) için sunucu eşleştirmesi ve kurallarda açık onaylı doğrulama. Ardından mobil PR'da not payload'a eklenmeli.
- Test/CI: henüz doğrulanmadı; PR birleştirilmedi, canlı Hosting'e yayımlanmadı.
