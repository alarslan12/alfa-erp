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

## 26.11.2026 — Mobil not aktarımı etkin (PR #29)
- ERP/entegrasyon PR #30 üretim dalına 25.11.2026 tarihinde birleştirildi. `alfa_rtdb.py::_adopt_checkout` artık `order_note` değerini `clean_note` ile doğrulayıp `make_notice(None, order)` uyarısını oluşturuyor; `firebase/database.rules.json` checkout notu için 2000 karakter sınırını içeriyor.
- Yalnız Mobil PR #29'daki `mobil_panel/index.html` değiştirildi: sipariş gönderiminde boş olmayan `order_note` alanı Firebase checkout payload'ına eklenir, başarılı kayıttan sonra yerel not taslağı temizlenir; aynı işlem kimliğiyle farklı notu yeniden gönderme engellenir.
- Test/CI ve canlı Firebase Rules uygulanmış olma durumu ayrıca doğrulanmalıdır. PR açık, henüz üretim dalına birleştirilmedi ve Hosting yayını yapılmadı. Suite sürümü değiştirilmedi.

## 26.11.2026 — Kompakt mobil geçmiş, güvenli checkout doğrulaması ve not tanısı
- Dal: `feature/mobile-compact-bulk-history-tracking-20261126`; üretim başlangıcı `904ad628` (PR #31). PR açılacak.
- `mobil_panel/index.html`: geçmiş Sipariş Takip sekmesinin en üstünde varsayılan kapalı bölüm, 20 kayıt/sayfa, arama ve yenileme; mevcut 500 kayıtlık yerel geçmiş anahtarı korunuyor. Kitap adı/kodu/SB-RNK/adet, not, gerçek ERP sipariş no (yetkili cihaz ve doğrulanmış kayıt varsa) gösterilir. Eski kayıtlar aynı UID'nin kendi checkout isteğinden, ERP sipariş no/kitap adı ise deterministik UUIDv5 ile yetkili erişimden doldurulur; yetki genişletilmez, veri uydurulmaz.
- Beş toplu işlem tuşu tek satır; açıklama kaldırıldı. Katalog araması masaüstündeki kesin sayı/seri eşleşmesine uyumlu. Canlı takipte not işareti ve açılır not metni, eşzamanlı dinleyici/kimlik doğrulama yarışlarına koruma.
- Checkout: sabit ve yerelde kalıcı işlem kimliği, not dahil içerik readback karşılaştırması, doğrulama olmadan sepet ve not taslağı temizlenmez. Web Locks destekleyen tarayıcılarda aynı origin sekmeleri de seri hale gelir. Geçmiş yalnız bu tarayıcıdaki son 500 başarılı kayıt; depolama engellenirse güvenli gönderim için hata verilir, farklı cihazlarla merkezi mükerrer engeli yok.
- Test: JS sözdizimi ve 12 saf mantık kontrolü çalıştırıldı; gerçek HTML'den çıkarılan offline checkout retry/not ve geçmiş kurtarma regresyon testi `tests/test_mobile_panel_runtime.py` eklendi. Canlı Firebase/telefon ve Windows kullanıcı ortamı testi yapılmadı; CI ayrıca takip edilecek.
- **ERP bağımlılığı (GitHub issue #32):** [Not aktarımı release ve eski not kurtarma](https://github.com/alarslan12/alfa-erp/issues/32). Son Windows Suite release v2.0.52 etiketinde checkout importer `order_note` işlemez; PR #30 sonrası yeni kurulum release'i gerekiyor. Eski sürümün aktardığı siparişler için güvenli ayrı ERP kurtarma/denetim gerekli olabilir. Bu PR yalnız mobil kaynakları ve mobil test/dokümanı değiştirir; Firebase Rules ve canlı veriler değişmedi. Hosting yayını açık onay bekler.
