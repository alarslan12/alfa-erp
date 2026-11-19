# ALFACOPYCENTER Suite — Ortak koordinasyon merkezi

Dört geliştirme sohbeti aynı GitHub reposunu kullanır; doğrudan birbirlerine mesaj göndermez. **Bu dosya rehberdir, anlık kayıt kaynağı değildir.** Gerçek güncel durum: [üretim dalı](https://github.com/alarslan12/alfa-erp/tree/firebase-rtdb-final), [açık PR'lar](https://github.com/alarslan12/alfa-erp/pulls), [Actions](https://github.com/alarslan12/alfa-erp/actions), [Releases](https://github.com/alarslan12/alfa-erp/releases).

## Başlangıç kaydı · 20.11.2026
- Repo: `alarslan12/alfa-erp`; aktif üretim: **`firebase-rtdb-final`** (`main` eski olabilir).
- Son doğrulanan kararlı Suite: **v2.0.46**. Her görev başında yeni sürüm olup olmadığını kontrol et.
- Firebase: `alfa-erp-8700c`. Windows: Personel, Yönetici, Banner Studio Pro ve Print Surveillance, **tek Suite Setup**.
- Kullanıcı dosyaları ve canlı sipariş veritabanı sürüm değişikliğinde asla sıfırlanmaz.
- Birim kodu PR ile birleştirilebilir; **Suite sürümü yalnız ayrı merkezi release PR'ıyla yükseltilir.**

## İş akışları

| Sohbet | Kendi durum kaydı | Çalışma dalları |
|---|---|---|
| ERP Personel / Yönetici | [ERP.md](workstreams/ERP.md) | `feature/erp-*`, `fix/erp-*` |
| Banner Studio Pro | [BANNER.md](workstreams/BANNER.md) | `feature/banner-*`, `fix/banner-*` |
| Mobil katalog / takip | [MOBILE.md](workstreams/MOBILE.md) | `feature/mobile-*`, `fix/mobile-*` |
| Print Surveillance | [PRINT.md](workstreams/PRINT.md) | `feature/print-*`, `fix/print-*` |

### Zorunlu akış
1. Her sohbet işe başlarken canlı repo/PR/Release ile **kendi** iş akışı dosyasını kontrol eder.
2. Yalnız kendi feature dalına kod ve **kendi** `docs/workstreams/*.md` durum kaydını yazar.
3. PR üzerinde kapsam ve Windows regresyon testleri çalışır; başarısız PR birleştirilmez.
4. Onaylı özellikler üretim dalına girer, ancak **her küçük değişiklik Setup üretmez**.
5. Paket çıkarılacağı zaman `integration/release-*` dalı tüm Suite sürüm dosyalarını birlikte yükseltir; ortak Windows build, tek Installer ve Release üretir.

`WORKSTREAM_STATUS.md` dosyası her PR'da değiştirilmez; bu, dört sohbetin aynı dosyada merge conflict oluşturmasını engeller. [Tam protokol](WORKSTREAM_PROTOCOL.md) · [Merkezi yayın](RELEASE_COORDINATION.md).
