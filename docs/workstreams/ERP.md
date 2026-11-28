# ERP Personel / Yönetici — Çalışma durumu

**Sohbet:** ERP Personel / Yönetici. **Repo:** `alarslan12/alfa-erp`; üretim `firebase-rtdb-final`.

**Son doğrulanmış kararlı Suite:** v2.2.0 (28.11.2026). Yeni görevlerde GitHub Release, üretim SHA ve açık PR'ları yeniden kontrol et.

**Kod sahipliği:** `main.py`, `ekran_katalog.py`, `ekran_siparis.py`, `ekran_analitik.py`, `ekran_verimlilik.py`, `flexflow*.py`, ERP/Firebase istemcisi, analitik/muhasebe ve ilgili testler.

**Korunacaklar:** Onaylanan Katalog/Siparişler arayüzü, ortak Havuz, personel/owner rolleri, Firebase Auth/RTDB, offline işlem kuyruğu, iade/kargo/ciro hesabı, FlexFlow hareketli gün/takvim filtresi ve günlük değerlendirme.

## Son iş: Yerel Derlemeler ayrıntı, düzenleme, silme ve tek sekme
- Dal: `fix/erp-local-derleme-detail-edit-20261128` · PR: bu dalın GitHub PR'ı.
- `main.py`: üstte tek Yönetici sekmesi Yerel Derlemeler; içeride Derleme Havuzu ve Bitmiş Derleme Siparişleri geçişi, gruba özel toplamlar korunur.
- `ekran_derleme_havuzu.py`: okunamayan salt metin popup yerine mevcut kitap kapak bileşeni, yatay şerit, SB/RNK adet ve sayfa bilgisi; düzenleme ekranında referans, ciro, not, kitap arama/ekleme, kaldırma ve adet kontrolü. Tekli düzenleme, çoklu onaylı silme. Bitmiş kayıt düzenlenirse bitiş durumu korunur; baskı içeriği değiştiğinde eski ZIP göstergesi temizlenir, dosya silinmez.
- `siparis_derleme_havuzu.py`: mevcut SQLite kayıtlarını ve sayacı koruyan deleted_at kolon geçişi, atomik soft delete, snapshot korumalı edit, eski ZIP sonucunun yeni kaydı ezmesini önleyen kontrol. Eski ID'ler yeniden numaralanmaz; görünüm D001, D002... olur. Silinen kayıtlar iki listeden ve toplamdan çıkar, veritabanında saklanır; geri yükleme arayüzü eklenmedi.
- `siparis_derle.py`: yeni yerel ZIP adı D001.zip; eski ZIP dosyaları yeniden adlandırılmaz/ezilmez. Aynı isim varsa mevcut benzersiz ad mantığı korunur. Normal ERP ZIP adları aynı.
- `tema.py`, `ayar_yonetimi.py`: yerel tablo seçili satır ve adet bilgisi okunaklı; notlar mevcut tema uyumlu OrderNoteInput. Normal iş akışı, Personel ve Firebase etkilenmez.
- `tests/test_derleme_havuzu.py`, `tests/test_gui_windows.py`: SQLite migration, snapshot/edit, soft delete, yeni ZIP adı, iç sekme ve kapak/adet UI regresyonları. Gerçek Windows cihazı/ekranı manuel test edilmedi. CI ve ortak yayın ayrı doğrulanır.

## Önceki iş: Yönetici yerel derleme havuzu ve bitiş onayı
- Dal: `feature/erp-local-derleme-pool-20261128` · PR: bu dalın GitHub PR'ı.
- `siparis_derleme_havuzu.py`: ayrı `owner_derleme/siparisler.sqlite3` deposu, bağımsız D-00001 numaraları, tarihsel kitap/sayfa fiyat snapshot'ı, kuruş cinsinden ciro, açık ve bitmiş siparişler. Toplu bitiş/geri alma tek SQLite transaction ile yapılır; hazırlama ve koli alanları yoktur.
- `ekran_derleme_havuzu.py`: aynı ekranın iki alt grubu, her grubun tüm kayıtları üzerinden dört toplam, sipariş ayrıntısı, çoklu seçili ZIP derleme, son ZIP tarihi ve operatör bitiş onayı. ZIP üretimi bitiş onayı değildir. Her sipariş ayrı ZIP, mevcut orijinal PDF paketleme sistemi korunur.
- `ekran_katalog.py`, `main.py`: Yöneticiye özel yerel kaydetme düğmesi ve iki Siparişler alt sekmesi, ortak ERP sipariş oluşturma fonksiyonuna uğramaz. Personel düğme/sekme/depo oluşturmaz; yerel kayıtlar genel ciro, analitik, bildirim ve RTDB kuyruğuna dahil edilmez. Normal sipariş rotası korunur. Aynı Windows kullanıcı hesabından dosya sistemi erişimi engellenmiş değildir; bu bir şifreli kasa değildir.
- `siparis_derle.py`: yerel ZIP adı ayrı (`Derleme D-00001.zip`); orijinal normal sipariş ZIP adı değişmez. Yerel PDF kitaplık ayarları yeniden kullanılır. Bu ilk sürüm ayrıntıyı salt okunur gösterir; yerel kayıt düzenleme/silme ve buluta aktarım eklenmedi.
- `tests/test_derleme_havuzu.py`, `tests/test_gui_windows.py`: kalıcılık, bağımsız toplamlar, atomik onay, ZIP'in tamamlamaması, Personel yalıtımı ve normal ERP oluşturma fonksiyonunu atlama testleri. Gerçek kullanıcı bilgisayarı ve canlı Firebase testi yapılmadı.
- Özellik sürümü için merkezi hedef v2.2.0; bu PR ortak Suite sürüm dosyalarını, kurulum sistemini veya canlı veriyi değiştirmez. Yerel verinin yedeği ayrı SQLite dosyasıdır; normal sipariş JSON yedeğine dahil edilmez.

## Önceki iş: Sipariş düzenleme kartları, arama ve kare HUD
- Dal: `fix/erp-order-editor-grid-hud-20261127` · PR: bu dalın GitHub PR'ı.
- `editor_siparis.py`: iç miktar editörü ayrı stil, sabit boyut ve sıfır iç boşluk; mevcut +/- ve doğrudan yazma korunur. Kartlar mevcut miktar widget'ları kaybedilmeden viewport genişliğine göre soldan sağa yerleşir.
- Kitap önerileri 6 karakterden sonra 150 ms gecikmeyle mevcut katalog arama mantığıyla filtrelenir, en fazla 60 sonuç gösterilir. Tam kitap kodu (# ile veya olmadan) doğrudan eklenebilir. SB/RNK doğrulaması ve sipariş kayıt mekanizması korunur.
- `main.py`, `tema.py`, `ayar_yonetimi.py`: Personel/Yönetici ortak 48×48 vektör ikonlu HUD, tema uyumlu arama/adet kontrolü. Bulut durum etiketi ayrı 110×48; diğer uygulamaların iş mantığı değişmez.
- `tests/test_gui_windows.py`: yeni regresyon senaryoları eklendi; Windows CI sonucu PR üzerinden doğrulanmalı. Yerel/gerçek Windows ekran ve canlı Firebase testi yapılmadı.
- Veri, canlı Firebase Rules/Hosting ve ortak Suite sürüm dosyaları değiştirilmedi. Patch sürümü v2.1.3 ayrı merkezi release PR'ı ile, kalite kapıları geçtikten sonra hazırlanabilir.

## Önceki iş: v2.1.1 HUD sadeleştirme ve Qt ampersand düzeltmesi
- Dal: `fix/erp-hud-single-update-mnemonic`. Tek Duyurular ve Güncelleme Merkezi düğmesi, daha geniş 48×38 kontroller, 110 px bulut göstergesi; Personel hata bildirimi korunur.
- Qt QPushButton literal ampersand için `&&` kullanır; kullanıcıya Bildirimler & Cihazlar görünür. Yönetici/Personel smoke testleri güncellendi.
- Yeni Suite sürümü bu PR'da yükseltilmez; canlı veriler ve diğer uygulamalar değişmez.

### GitHub erişimi / yeni sohbet başlangıcı
- Doğrudan bağlı GitHub araçlarıyla depo, gerçek üretim dalı `firebase-rtdb-final`, latest release ve açık PR'ları kontrol et. Varsayılan `main` kullanılmaz.
- GitHub bağlayıcısının okuma/yazma, branch ve PR işlemlerini önce keşfet ve gerçek repo yanıtındaki izinleri doğrula. Genel web veya git clone erişim hatası tek başına bağlayıcının yetkisiz olduğu anlamına gelmez.
- Erişim yok demeden önce bağlı GitHub araçlarıyla dene, gerçek hata kodunu belirt. Başarılı olmayan commit/merge/release için tamamlandı deme.

## Önceki iş: Çalışma ayarları, birleşik cihaz/bildirim sekmesi ve HUD

- v2.1.0 kullanıcı ekran görüntülerine göre PDF ve Excel eş hizalı kartlar; ortak görünüm kartı, eş yükseklikte pillbox gezinme ve temaya uyumlu HUD.
- Yönetici ve Personel: Bildirimler & Cihazlar; sol dört gerçek Ozan anonsunun ayrı dinleme düğmeleri ve rastgele dinleme, sağ Yönetici cihaz yönetimi veya Personel kendi cihazı. Güncelleme merkezi üst HUD'da, cihaz kalkanıyla ayarlar yanında; küçük ekranlarda ana gezinme ikinci satıra iner.
- Otomatik Personel anonsu yalnız dört Ozan kaydından rastgele biri. Eski ses seçenekleri ve Windows TTS/ton fallback kaldırıldı; eski ayarlar otomatik yeni moda geçer. Yönetici önizleme sipariş oluşturmadan çalışır. Başka uygulama, Firebase, canlı veriler ve Suite sürüm numarası değiştirilmez.
- Ayrı entegrasyon PR'ı; otomatik kontroller ve Setup yayını ayrı doğrulanır.

## Önceki iş: Canva Ozan M4A yerel anons desteği (v2.1.0)

- Canva Türkçe Ozan sesinin indirilen M4A dosyaları doğrudan desteklenir; `ozan_1.m4a`–`ozan_4.m4a` tercih edilir. WAV ve MP3 alternatifleri de korunur. Qt Multimedia yerel oynatma, asenkron hata sonrası WAV/Windows Türkçe ses/ton fallback'i ve oynatıcı ömrü yönetimi eklendi.
- Personel, Yönetici ve AlfaBildirim paketlerine Qt Multimedia ve assets dahil edilir; ElevenLabs bağlantısı geri eklenmez. Dört gerçek Canva Ozan M4A çıktısı kullanıcı tarafından depoya eklendi; boyutları ve SHA-256 değerleri özgün dosyalarla birebir eşleşiyor.
- Mevcut canlı Firebase Rules değiştirilmedi. Yayındaki Suite v2.0.53, merkezi 2.1.0 taslak PR #37 henüz yayınlanmadı. Bu değişiklik ayrı entegrasyon PR'ıyla birleştirilip sürüm adayına dahil edilir.

## Önceki iş: v2.1.0 Yönetici / Personel sadeleştirme ve kararlılık
**Dal:** `integration/erp-v210-admin-refurb` · ERP + ortak Rules/kurulum hazırlığı içeren entegrasyon PR'ı. Mobil, Banner ve Print iş mantığı değiştirilmez.

- Kullanıcı isteğiyle geçmiş checkout notlarının otomatik kurtarması tamamen kaldırıldı. Yeni mobil siparişlerde `order_note`, 2000 karakter ve ilk uyarı davranışı korunur. Mevcut siparişler ve geçmiş notlar yeniden yazılmaz. ETag sayaç/revision çakışmasının tekrarı 503 geçici durumudur; iş kuyruğu kalıcı reddedilmiş sayılmaz.
- Hata Merkezi: çoklu seçim, arama, filtre, toplu inceleme/silme, görünür incelenmiş kayıtların temizlenmesi, HTTP kodu ve yeni raporlarda güvenli işlem aşaması. Eski bulut çakışma arşivi buraya taşındı. Rapor silinmeden inceleme onayı silinmez; başarısız kayıtlar HTTP koduyla gösterilir.
- Cihazlar: isim/UID araması, kısa UID, kendi cihazı etiketi, kayıt zamanı/varsa son bağlantı, yeniden adlandırma ve pasif kayıtların ETag korumalı temizlenmesi. Etkin owner rolü zorunlu, aktif cihazlar ve kendi cihazı korunur. Personel onayında mevcut owner rolü ezilmez. Repo Rules üyelik silmeyi yalnız pasif diğer üyeyle sınırlar; canlı Rules **yayımlanmadı**.
- İşlem günlüğü: tarih başlıkları, yeni/eskiden yeniye göre zaman gruplaması, aynı sipariş/cihaz/aktivitenin 120 saniyelik grupları, her hareketin gerçek zaman damgası, arama/aktivite filtresi, temaya uygun renk/hover. Erişilemeyen eski audit kaydı yeni işlem listesini bozmaz. Sistem sağlığı ekranı kaldırıldı.
- Derleme yalnız Yönetici'de: bütün ZIP kontrolleri ve giriş koruması, Personel PyInstaller paketinde `siparis_derle` modülü hariç bırakıldı. Personel PDF açma/kapak işlemleri korunur.
- Uygulama Ayarları: PDF kitaplık sol, Excel katalog sağ, temalar ve kontrast altında; ayrı Bildirimler ve Güncelleme tabı. Sağ üstte kalkan cihaz yetkisi ve en sağda ayarlar, çakışma uyarısı 14 saniye.
- ElevenLabs ağ/API ve UI entegrasyonu kaldırıldı. Dört sabit Türkçe anons metni, yerel WAV oynatma ve yüklü Windows Türkçe sesi/ton fallback'i. Canva Ozan gerçek ses varlıkları PR #38 kapsamında sonradan temin edildi. Eski şifreli dosyalar ve kullanıcı ayarları zorla silinmedi.
- **Denetim:** Başlangıçta 52 dal ve sıfır açık PR incelendi; kapatılmış PR kayıtları ve 11 seçili eski ERP/Firebase dalının ancestry/diff özeti kontrol edildi. Eski ayrışmış dallar yeniden merge edilmedi; diğer workstream'ler değiştirilmedi. Artık depoda olmayan auto_eslestir modülüne bağlı eski Personel giriş dosyası güncel, yetki ayrımlı girişe uyarlandı. Kullanıcı isteğine uygun elle test/Windows derlemesi çalıştırılmadı; otomatik PR kapıları devreye girebilir. Gerçek Firebase canlı izinleri ve kullanıcı bilgisayarları test edilmedi.
- **Yayın:** Hedef 2.1.0 ayrı merkezi release dalında hazırlanacak. PR/CI/Release ve canlı Rules onayı ayrı tutulur. Ozan M4A kaynakları PR #38'de doğrulandı; canlı yetkiler ve Setup yayını ayrıca doğrulanır.

## Önceki iş: Issue #32 — Eski mobil checkout notlarını zarar vermeden kurtarma (kaldırıldı)
**Dal:** `fix/erp-reconcile-mobile-checkout-notes-issue32` · **PR:** Bu dalın ERP PR'ı.

- **Kök neden:** Son yayımlanan Suite v2.0.52, PR #30'un not aktarımını ve PR #31'in ZIP notunu içermiyordu. Mobil PR #33 üretime birleştirildi; ERP kurulumunun güncellenmesi gerekiyor.
- `alfa_rtdb.py`: `_adopt_checkout` mevcut UUIDv5 checkout order'ı için orijinal istekte dolu not varsa ETag korumalı salt alan onarımı yapar. Sadece mevcut `id`, `workspace_id`, `client_request_id` eşleşiyorsa; `order_note` ve `order_notice` anahtarları hiç yoksa onarım yapılır. Başka not, mevcut/okunmuş uyarı, silinmiş sipariş, sahipsiz kayıt korunur.
- Kurtarılan note + `make_notice(None, order)` ile `initial_note` bir defada eklenir; sadece `version`, `updated_at` güncellenir. Mevcut sipariş numarası, kitaplar, hazırlık/koli, durum, ciro, kargo, geçmiş ve event_log dokunulmaz. ETag yarışında yeniden kontrol edilir; yinelenen order oluşturulmaz.
- Bellek içi `_checkout_notes_checked` aynı oturumda eski checkout kayıtlarının sürekli yeniden sorgulanmasını azaltır; tekrar başlatma/retry idempotenttir.
- `tests/test_checkout_note_recovery_erp.py`: önceden notsuz içe alınmış sipariş, mevcut farklı not/uyarı/okunmuş uyarı/silinmiş/mismatch kayıt, tekrar çalışma, kaynakta not yoksa onarımsız bırakma testleri.
- **Sınırlar:** Yalnız Firebase checkout isteğinde hâlâ saklı not kurtarılabilir. Kaynak checkout notu yoksa uydurulmaz. Canlı Firebase erişimi veya veri onarımı bu PR'da yapılmadı; düzeltilmiş importer ancak güncellenen Windows kurulumundan sonra çalışır. Canlı Rules ve Hosting değiştirilmez.
- Mobil PR #33 dosyalarına dokunulmaz. Merkezi Suite Release ayrı `integration/release-...` PR'ıyla yürütülür.

## Önceki iş: Sipariş notunu fason baskı talimatına ekleme
**Dal:** `fix/erp-compile-print-instruction-order-note-20261126` · **PR:** GitHub'da bu dalın PR'ı.

- `editor_siparis.py`: derleme worker'ının sipariş snapshot'ına mevcut `order_note` alanı eklenir.
- `siparis_derle.py`: `BASKI_TALIMATI.txt` önceki sipariş kodu / toplam sayfa / toplam kitap özetini korur; not varsa boş satır ve **Sipariş Notu:** başlığı altında tam metni ekler. Boş notta üç satırlık çıktı değişmez.
- `tests/test_order_compile_zip.py`: çok satırlı Türkçe notun ZIP'e aktarıldığı ve boş notun çıktıyı değiştirmediği kontrolü.
- Kapsam yalnız ERP Personel/Yönetici, yerel ZIP; Firebase, mobil katalog, diğer Suite uygulamaları, ortak sürüm ve veri kayıtları değiştirilmez.

## Önceki iş: Mobil checkout sipariş notunu ERP uyarı sistemine aktar
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
