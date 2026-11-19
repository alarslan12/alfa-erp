# ALFACOPYCENTER Suite — Çok sohbetli geliştirme protokolü

## Her görevden önce
1. GitHub repo `alarslan12/alfa-erp`, gerçek üretim dalı `firebase-rtdb-final`, son commit ve son GitHub Release'i oku; `main`'i referans alma.
2. [Ortak durum](WORKSTREAM_STATUS.md), **kendi** `docs/workstreams/<ALAN>.md` dosyanı ve [açık PR'ları](https://github.com/alarslan12/alfa-erp/pulls) kontrol et.
3. Aynı dosyada başka bir açık PR varsa onun değişikliğini ezme; çatışmayı uzlaştır veya diğer PR'ı bekle.
4. Başka sohbetin belleğine güvenme: kaynak hakikati GitHub ve doğrulanmış canlı uygulama davranışıdır.

## Dallar ve sahiplik
- ERP: `feature/erp-...` veya `fix/erp-...`; ör. `main.py`, `ekran_siparis.py`, `ekran_analitik.py`, `ekran_verimlilik.py`, `flexflow*.py`, ilgili muhasebe/Firebase istemcileri ve ERP testleri.
- Banner: `feature/banner-...` veya `fix/banner-...`; `banner_studio/**` ve ilgili testler.
- Mobil: `feature/mobile-...` veya `fix/mobile-...`; `mobil_panel/**`, `mobil_siparis_donusum.py`, mobil Hosting betikleri ve ilgili testler.
- Print: `feature/print-...` veya `fix/print-...`; `alfa_print_*.py`, `ekran_yazdirma.py`, `ekran_baski_plani.py`, ilgili testler.
- Birden çok birimi etkileyen onaylı değişiklik: `integration/...`.
- Sürüm ve Setup: **yalnız** `integration/release-...`.
- Altyapı/koordinasyon: `chore/coordination-...`.

Yalnızca ilgili sohbetin `docs/workstreams/<ALAN>.md` dosyasını her PR'da güncelle; dosyaya son PR/iş/güncel bağımlılık yaz. Ortak `WORKSTREAM_STATUS.md` her PR'da tekrar yazılmaz. PR açıklamasına gerçek değişen dosyalar, testler, veri riski, başka birimin bağımlılığı ve release isteğini ekle.

## Çakışma ve ortak dosyalar
`ALFACOPYCENTER_Suite.iss`, `ALFA_BUILD_SUITE_WINDOWS.ps1`, `ALFA_BUILD_WINDOWS.ps1`, `.github/workflows/**`, `surum_gecmisi.py`, `CHANGELOG.md`, `README.md`, `firebase/database.rules.json`, ortak sürüm dokümanları ve sürüm **sabitleri** birim PR'ında değiştirilmez. Bunlar merkezi entegrasyon sorumluluğudur.

Ortak `tema.py`, `takvim.py`, `alfa_rtdb.py` gibi dosyalarda düzenleme gerekiyorsa çalışma alanı etkisini PR'a açıkça yaz; kapsam doğrulayıcısı bu temel ERP dosyalarını ERP sorumluluğu sayar. Diğer bileşenler böyle bir değişiklik için `integration/*` kullanır.

## Kontroller ve yayın
- PR'larda `Workstream scope` ve `Windows regression tests` iş akışı bulunur; **Setup veya GitHub Release üretmez**.
- Birim PR'ları tek Suite sürüm numarasını **yükseltmez**.
- Windows kurulum workflow'u, üretim dalına **Suite manifesti (`ALFACOPYCENTER_Suite.iss`) değişikliği** geldiğinde tetiklenir; sıradan özellik PR'ları yüzünden tekrar aynı sürüm yayınlanmaz.
- Entegrasyon/release PR'ında sürüm etiketleri (main.py, Banner, Inno, PowerShell, workflow, README, CHANGELOG, release notes, geçmiş) birlikte yükseltilir.
- Her CI başarısı gerçek Firebase yetki testleri, iki-PC canlı eşitleme veya gerçek yazıcı fiziksel çıktısı yerine geçmez.
- GitHub branch protection/ruleset yöneticisi gerekli PR denetimlerini kendi hesabından **zorunlu** kılmalıdır; yalnız workflow bulunması sunucu tarafı merge engeli değildir.

## Veri koruma
`%LOCALAPPDATA%\AlfaERP`, `%LOCALAPPDATA%\ALFA_Banner_Studio_Pro`, canlı Firebase RTDB, cihaz kimlikleri, siparişler ve yazıcı SQLite verileri korunur. Production Hosting deploy, Rules değişikliği veya veri temizleme özel onay olmadan yapılmaz. Parola, servis anahtarı, gizli token veya kullanıcı özel verisi GitHub'a eklenmez.

## Kısa son mesaj şablonu
“Dal/SHA; değiştirilen dosyalar; PR; CI sonucu; henüz yayınlanmadı/yayın linki; başka sohbeti etkileyen bağımlılıklar.”
