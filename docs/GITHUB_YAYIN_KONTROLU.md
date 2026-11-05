# GitHub Yayın / 404 Kontrolü — ALFA ERP

Güncelleme: 5 Kasım 2026.

## Tespit

- Depo: `alarslan12/alfa-erp`, herkese açık ve erişilebilir.
- Ana dal: `main` (eski V6.2.2 kodu). Aktif Firebase geliştirme dalı: `firebase-rtdb-final`, ana daldan 58 commit ilerideydi.
- V6.4.1 Windows Actions #42029816134: iki EXE derlendi ve SHA-256 doğrulandı; **yalnız Release yayınlama adımı başarısız**.
- Paket arşivi: artifact #13415766720. GitHub Actions arşivleri giriş gerektirir, tarih aşımıyla silinir (burada 7 gün). Dolayısıyla doğrudan `/suites/.../artifacts/...` URL'si herkeste çalışmaz; 404 verebilir.
- GitHub Release oluşturma: hedef commit mevcut `main` dalında olmayan üç `.github/workflows/` dosyasını içeriyor. Bu yüzden otomatik `GITHUB_TOKEN` hesabı için workflow-yazma ayrı yetkisi gerekiyor; GitHub bu durumda 403/404 döndürebilir.
- GitHub genel hizmet durumu: inceleme anında aktif kesinti bulunmadı.

## Giderilen sorunlar

1. Önizleme derlemesi bundan sonra **sadece kurulum dosyalarını ve SHA-256 kontrolünü** oluşturur. Başarılı bir build, Release yayınlama yetkisi yok diye kırmızıya düşmez.
2. Önizleme build token'ı `contents: read` ile sınırlandırıldı. Her derleme sonunda güvenli indirme yönergesi iş özeti içinde görünür.
3. `publish-641-built-release.yml` sürekli `push` ile tetiklenmez, **yalnız elle** başlatılır ve ayrı izinli release token'ı ister. Eski Actions artifact'ını yeniden derlemeden kullanır.
4. Hiçbir Firebase verisi veya cihaz yetkisi değiştirilmedi; `main` dalı korunuyor.

## V6.4.1 kurulumlarını GitHub'dan açmak

GitHub'a kendi hesabınla giriş yap. `https://github.com/alarslan12/alfa-erp/actions/runs/42029816134` sayfasına gel. Sayfa altındaki **Artifacts** alanından `ALFA_ERP_Firebase_RTDB_V6_4_1_PREVIEW` dosyasını indir. Artifact 12 Kasım 2026 tarihinde sona eriyor.

## Kalıcı GitHub Release için iki yol

**Tercih edilen:** Yeni Firebase kodu iki Windows bilgisayarında doğrulanınca geliştirme dalını kontrollü şekilde `main` ile birleştir; ardından `main` üzerindeki uygun sürüm iş akışından (veya GitHub web arayüzünden) nihai Release yayımla. Böylece yeni `.github/workflows` dosyaları artık ana dala göre sürpriz fark olmaz.

**Geliştirme dalında kalıcı önizleme gerekiyorsa:** Depo sahibi *Settings → Secrets and variables → Actions → New repository secret* üzerinden `ALFA_RELEASE_TOKEN` adında, yalnız bu depo için geçerli, kısa süreli fine-grained token tanımlayabilir. Yalnız `Contents: write` ve `Workflows: write` izinleri verilmeli. Sonra Actions → **Publish prebuilt ALFA ERP 6.4.1 RC2** → Run workflow yoluyla manuel yayımlama yapılabilir. **Token'ı asla sohbet mesajına, koda veya loglara yapıştırma.**

Sadece *Settings → Actions → General → Workflow permissions* ayarını genişletmek, ana daldan farklı iş akışı dosyaları için ek Workflows iznini tek başına sağlamayabilir. Gereksiz izin genişletme yerine yukarıdaki iki yöntemden birini kullan.

Kaynaklar:
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts
- https://docs.github.com/en/rest/releases/releases
- https://www.githubstatus.com/
