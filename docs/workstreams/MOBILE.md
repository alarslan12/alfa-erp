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
