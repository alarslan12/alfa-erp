# ALFACOPYCENTER Suite — Tek merkezden Windows sürüm yayını

## Roller
- Dört geliştirme sohbeti kendi alanında feature/fix PR açar, PR testlerini geçtikten sonra kodunu üretim dalına alabilir.
- **Birim sohbetleri** `VERSION`, `SUITE_VERSION`, Setup sürümü, workflow sürümü veya ortak `surum_gecmisi.py` alanlarını bağımsız yükseltmez.
- **Merkezi yayın** gerektiğinde ayrı `integration/release-<hedef-sürüm>` dalı/PR'ı oluşturulur. Birden fazla birimin en son birleşmiş kodunu tek Installer'da toplar.

## Release PR kontrol listesi
1. Üretim dalındaki commit ve GitHub Releases'in en son `v2.x` sürümünü doğrula.
2. Açık dört iş akışı PR'ından dahil edilmemiş bağımlılık var mı kontrol et; gerekenleri önce birleştir.
3. Sonra şu dosyaların sürüm etiketlerini **aynı sürüme** ayarla:
   - `main.py` → `VERSION`
   - `banner_studio/studio_server.py` → `SUITE_VERSION`
   - `ALFACOPYCENTER_Suite.iss` → `SuiteVersion`, `VersionInfoVersion`, `OutputBaseFilename`
   - `ALFA_BUILD_SUITE_WINDOWS.ps1` → Setup dosyası
   - `.github/workflows/alfacopycenter-suite.yml` → başlık, `SUITE_TAG`, `SUITE_EXE`, release notes ve artifact
   - `README.md`, `CHANGELOG.md`, `surum_gecmisi.py`
   - `docs/ALFACOPYCENTER_SUITE_V<versiyon_birleşik>_RELEASE.md`
4. `python tools/check_release_consistency.py` ile sürümlerin uyumunu ve notların varlığını doğrula.
5. `integration/release-...` PR'ı aç; PR kalite kapısını kontrol et.
6. Merge sonrası manifesti değiştiren push, `alfacopycenter-suite.yml` üzerinden Windows Setup, EXE smoke testleri, SHA-256 ve kararlı GitHub Release aşamalarını çalıştırır.
7. Release assets'de `ALFACOPYCENTER_Suite_Setup_Vx_y_z.exe`, `SHA256SUMS.txt`, `RELEASE_NOTES.txt` varlığını doğrula. CI sırf derlemede başladı diye yayımlandı deme.

## Risk azaltma
- Üretim dalında sıradan birim PR'ı, README düzeltmesi veya test eklemesi **yeni Setup başlatmamalı**.
- Workflow `workflow_dispatch` ile gerekirse manuel tetiklenebilir; tekrar aynı tag'in yayımlanması/üstüne yazılması beklenmemeli.
- User data klasörleri, Firebase Rules, canlı siparişler ve cihaz yetkileri korunur.
- Bu model yeni uygulama sürümünün operatör onaylı yüklenmesi ilkesini değiştirmez.
