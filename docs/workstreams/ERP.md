# ERP Personel / Yönetici — Çalışma durumu

**Sohbet:** ERP Personel / Yönetici. **Repo:** `alarslan12/alfa-erp`; üretim `firebase-rtdb-final`.

**Son doğrulanmış kararlı Suite:** v2.0.51 (21.11.2026). Yeni görevlerde GitHub Release, üretim SHA ve açık PR'ları yeniden kontrol et.

**Kod sahipliği:** `main.py`, `ekran_katalog.py`, `ekran_siparis.py`, `ekran_analitik.py`, `ekran_verimlilik.py`, `flexflow*.py`, ERP/Firebase istemcisi, analitik/muhasebe ve ilgili testler.

**Korunacaklar:** Onaylanan Katalog/Siparişler arayüzü, ortak Havuz, personel/owner rolleri, Firebase Auth/RTDB, offline işlem kuyruğu, iade/kargo/ciro hesabı, FlexFlow hareketli gün/takvim filtresi ve günlük değerlendirme.

## Son iş: Mobil checkout sipariş notunu ERP uyarı sistemine aktar
**Dal:** `integration/checkout-note-erp-rules-20261125` · PR: Bu dalın entegrasyon PR'ı.

- `alfa_rtdb.py::_adopt_checkout`: mobil `order_note` alanının tipini ve 0–2000 karakter sınırını doğrular, mevcut `siparis_uyari.clean_note` ile temizler. Boş not uyarı doğurmaz; dolu not siparişin `order_note` alanına ve `make_notice(None, order)` aracılığıyla `initial_note` / okunmamış `order_notice` uyarısına aktarılır.
- `firebase/database.rules.json`: checkout içinde isteğe bağlı `order_note` yalnız string, en fazla 2000 karakter. Mülkiyet doğrulaması, oluşturma-only koşulu, istenmeyen alan reddi ve diğer güvenlik kuralları aynı kalır. **Canlı Rules/Hosting yayını yapılmadı.**
- `tests/test_mobile_checkout_note_adoption.py`: notlu/notsuz sipariş, tam 2000 sınırı, geçersiz değer, ilk uyarı/onay ve tekrarlı checkout idempotensi için çevrimdışı test.
- **Bağımlılık:** mobil PR #29 açık ve mobil payload notları şu an bilerek gönderemiyor. Bu entegrasyon PR'ı mobil dosyaları değiştirmez. PR #29 mobil sahipliğinde tamamlanmalı; canlı notlu sipariş için ayrıca açık Rules dağıtım onayı ve mobil gönderimin etkinleştirilmesi gerekir.
- Suite sürümü ve kurulum dosyaları, canlı Firebase siparişleri ve diğer uygulamalar değişmez.

## Önceki iş: ZIP kitap miktarı öne alındı ve talimat özeti sadeleşti
**Dal:** `fix/erp-zip-quantity-prefix-summary-20261122` · **PR:** GitHub'da bu dalın PR'ı.

- `siparis_derle.py`: PDF adları `2 ADET - DOSYA_<rastgele>.pdf` (1 adet dahil) biçiminde; arşiv adından yalnız miktar ve rastgele kimlik okunur. Baskı talimatı yalnız **Sipariş Kodu**, **Toplam Sayfa Sayısı** ve **Toplam Kitap Sayısı** alanlarını içerir.
- Sayfa hesabı `Database._book_page_count` ile eşdeğer: sipariş satırındaki tarihsel `sayfa_birim` / `sayfa` değeri, yoksa katalogdaki sayfa sayısı. Siyah/renkli kopyalar ve tekrarlar adetle çarpılır. Tekli/seçili ZIP'in sayfa/kitap toplamı yalnız paket içindeki kitaplara aittir.
- `tests/test_order_compile_zip.py`: dosya adı başındaki 1/2/5 adet, üç satırlık özet, seçili sipariş, tarihsel sayfa ve katalog fallback testleri.
- PDF kaynak baytları olduğu gibi ZIP'e aktarılır; yeniden sıkıştırma/anonimleştirme ve Firebase aktarımı yoktur. Diğer Suite uygulamaları, sürüm ve kullanıcı verileri değişmez. Windows CI PR üzerinde kontrol edilir.

## Önceki iş: Fason ZIP derlemeyi hızlandırma (raster/anonimleştirme kaldırıldı)
**Dal:** `fix/erp-fast-raw-pdf-zip-20261121` · **PR:** Bu dalın GitHub PR'ı.

- `siparis_derle.py`: 300 DPI rasterizasyonu, PDF yeniden yazımı ve metaveri temizleme kaldırıldı. PDF kaynak baytları doğrudan ZIP'e, yeniden sıkıştırılmadan (ZIP_STORED) yazılır. Masaüstü ZIP adı ve Siyah/Renkli klasörleri, rastgele PDF adları, adet uyarıları, talimat dosyası, dosya eksikse işlem iptali korunur.
- `editor_siparis.py`: anonimleştirme yazıları kaldırıldı; sade orijinal PDF aktarımı ve dosya bazlı ilerleme görünür. Arayüz kilitlenmez.
- `tests/test_order_compile_zip.py`: ZIP içindeki PDF'nin kaynakla birebir aynı baytlardan oluştuğu, metaveri örneklerinin korunduğu, klasör/adet/iptal/eksik dosya akışı doğrulanır.
- **Bilgi:** Rastgele dosya adları gerçek kitap ismini yalnız ZIP giriş adından gizler; orijinal PDF metaverisi, içeriği, dosya içi filigranları artık olduğu gibi kalır. Kullanıcı belgeleri ve bulut verileri değiştirilmez. Suite v2.0.50 release halen ayrı merkezi sürüm olarak yönetilir.

## Önceki iş: Fason baskı için yerel anonim ZIP derleme
**Çalışma dalı:** feature/erp-local-order-anonymous-zip-20261120 · **PR:** https://github.com/alarslan12/alfa-erp/pull/23.

- editor_siparis.py: Havuz, Aktif ve Tamamlanan ayrıntılarının başlığından tüm siparişi; tek kitap kartından tek kitabı; aktif takip seçiminden seçilen kitapları tek tıkla ZIP'e derler. Uzun PDF dönüşümü QThread ile GUI dışında yapılır ve iptal/ilerleme gösterilir.
- siparis_derle.py: PDF kütüphanesini yalnız yerelde tarar; seçilen her SB/RNK türünü 300 DPI resim tabanlı yeni PDF'ye dönüştürür. Kaynak Info/XMP, gömülü ekler, form/JS/gizli metin/katmanlar, yer işaretleri ve dosya yolları ZIP'e kopyalanmaz. SB gri tonlama, RNK renkli. Baskı adetleri rastgele dosya adında ve BASKI_TALIMATI.txt içinde belirtilir. Sipariş N.zip Masaüstüne otomatik oluşturulur; önceki ZIP ezilmez.
- tests/test_order_compile_zip.py: varyant/çoklu adet, seçili kitap, özel ad, yanlış/eksik dosya, iptal, PDF kaynak metadata anonimleştirme doğrulamaları.
- Eksik/bozuk PDF varsa ZIP üretimi iptal edilir, geçici dosyalar silinir. PDF'ler sunucuya gönderilmez ve orijinaller değiştirilmez. Görünür sayfa filigranları/gizli işaretler piksel olduğu için silinemez; çıktı rasterdır, arama/vektör niteliği kaybolur ve dosya boyutu büyüyebilir.
- Suite sürüm/Setup, Firebase, diğer uygulamalar ve kullanıcı yerel geçmişi değişmez. Gerçek fason/yazıcı denemesi yapılmadı.

## Önceki iş: Analitik HTML raporu / doğrudan yazdır
**Dal:** `fix/erp-analytics-desktop-print-20261120`. **PR:** Açık PR'dan takip edilir.

- `ekran_analitik.py`: kaydetme diyaloğu kaldırıldı; rapor Windows Masaüstü konumuna benzersiz adla kaydedilir ve varsayılan tarayıcıda otomatik yazdırma diyaloğu tetiklenir.
- Yazıcıya izinsiz çıktı gönderilmez; kullanıcı tarayıcının yazdırma ekranında onaylar. Browser ayarlarına bağlı olarak otomatik yazdırma engellenebilir.
- Muhasebe/iade/kargo/Firebase/yerel veriler, diğer uygulamalar ve Suite sürüm sistemi değiştirilmedi. Donanım testi yapılmadı.

## Önceki iş: İki vardiya arasında üretim yükü dağıtımı
**Çalışma dalı:** `feature/erp-flexflow-shift-workload-allocation-20261120`.
**PR:** Bu işin PR'ı GitHub'dan doğrulanır; açık PR listesini kontrol et.

- `flexflow_emek.py`: biten siparişlere ait sayfa, SB/RNK, delme, spiral, kolileme iş yükü için teorik *standart dakika* hesabı; referans olarak tamamlanmış sayfa-bilgili siparişlerin medyan iş yükü. Günlüğü mevcut hazırlama/kolileme aşamaları olay gününe, yalnızca önceki gün aktife alınmış ve eksik zamanlı hazırlama aşamaları iki günlük vardiyaya **tahmini** dağıtılır; ideal paralel kapasite baskısı da dikkate alınır.
- `flexflow_operasyon.py`: gerçek tamamlanan siparişler değişmeden her gün için üretim eşdeğeri ve kayıtlı/tahmini katkılar; teori-mesai uyumsuzluğu açıklaması.
- `ekran_verimlilik.py`: gerçek tamamlanan sipariş ile tahmini üretim eşdeğerini ayrı renklerde gösteren ek grafik, günlük açıklama ve tablo sütunları.
- `flexflow_rapor.py`: CSV/HTML kayıtlı–tahmini iş ayrımı, devreden model dakika.
- `tests/test_flexflow_shift_workload.py`: önceki gün hazırlama kaydı, bir gün sonraki toplu kapanma, eksik sayfa, ideal kapasite aşımı, konservatif belirsizlik testleri.

**Sınırlar:** Bu bir vardiya **tahmini**; gerçek çalışan/makine telemetrisi değil. Kayıtlı aktivasyon veya olay yoksa dünkü çalışma uydurulmaz. Tamamlanan sipariş adedi ve tarihleri, Firebase, kullanıcı verileri değişmez. Print Surveillance'ı etkilemez.

**Bir sonraki adım:** PR otomatik kalite testleri ve birleştirme sonrası **merkezi release** sürecinde tek Suite v2.x sürüm yükseltmesi. Bu ERP PR'ı ortak sürüm dosyalarını değiştirmez.

Bu dosyayı yalnız ERP sohbeti kendi sonraki PR'larında günceller.
