# ERP Personel / Yönetici — Çalışma durumu

**Sohbet:** ERP Personel / Yönetici. **Repo:** `alarslan12/alfa-erp`; üretim `firebase-rtdb-final`.

**Son doğrulanmış kararlı Suite:** v2.0.47 (20.11.2026). Yeni görevlerde GitHub Release, üretim SHA ve açık PR'ları yeniden kontrol et.

**Kod sahipliği:** `main.py`, `ekran_katalog.py`, `ekran_siparis.py`, `ekran_analitik.py`, `ekran_verimlilik.py`, `flexflow*.py`, ERP/Firebase istemcisi, analitik/muhasebe ve ilgili testler.

**Korunacaklar:** Onaylanan Katalog/Siparişler arayüzü, ortak Havuz, personel/owner rolleri, Firebase Auth/RTDB, offline işlem kuyruğu, iade/kargo/ciro hesabı, FlexFlow hareketli gün/takvim filtresi ve günlük değerlendirme.

## Son iş: İki vardiya arasında üretim yükü dağıtımı
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
