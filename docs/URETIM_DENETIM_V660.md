# ALFA ERP V6.6.0 — Üretim Denetimi ve Nihai Geçiş

## Uygulanan geliştirmeler

| Alan | Yapılan değişiklik | Ek sorgu |
|---|---|---|
| Hata derleyici | Python/Qt exception ve önceki native çökme kayıtlarını **mesaj/lokaller olmadan** derler; şifre veya sipariş içeriği gönderilmez | Yalnız olay olunca 1 yazma |
| Kritik eşitleme | Reddedilmiş iş, art arda 4 başarısız bulut denemesi ve kalıcı hata tiplerini ayrı sınıflandırır | Aynı tür için 5 dakikalık tekrarlama sınırı |
| Personel hatası | Yerel dosya kuyruğu (azami 30), gönderim başarısızsa silmez; yeni hata/yeniden bağlantı/başlangıçta yeniden dener | Arka planda yeni hata polling'i yok |
| Yönetici Hata Merkezi | Yetkili Yönetici cihazı Firebase SSE ile yeni kayıtları alır; son 70 rapor / son 150 onay | Sürekli HTTP sorgusu yok; 1 canlı SSE bağlantısı |
| Güncelleme Merkezi | GitHub kalıcı kararlı sürüm, SHA-256 kontrolü, indirme, kullanıcı onayı, kapanış sonrası sessiz kurulum | Günde en fazla 1 release API kontrolü |
| Operasyon | Buluta gönderilmeyi bekleyen sipariş varsa güncelleme başlamaz | Ek Firebase sorgusu yok |
| GitHub temizliği | V6.2–V6.5 için 6 eski iş akışı Firebase dalından kaldırıldı | Eski main dalı korunur |
| Masaüstü | Artık kullanılmayan Supabase eşleştirme zamanlayıcısı kaldırıldı | 60 saniyelik işe yaramaz zamanlayıcı kalktı |

## İşletim ve gizlilik

- Rapor örneği: `ExceptionType`, sürüm, cihaz adı, zaman, **sadece Python modül adı + fonksiyon + satır numarası**, hash/fingerprint.
- **DİKKAT:** Kişisel bilgi içerebilen `str(exception)`, müşteri adresleri, kargo kodları, PDF içerikleri, ağ isteği gövdeleri veya Firebase ID token hiçbir hata raporunda gönderilmez.
- Hata tekrarları aynı fingerprint ile 5 dakika sınırlanır; ağ kopunca yerel kuyruk saklanır.
- Yönetici ekranı yalnız owner rolü ile okunabilir. Personel sadece **kendi UID'siyle** rapor ekleyebilir; önceki raporları okuyamaz veya değiştiremez.
- SSE, oturum boyunca tek bağlantı açık tutar. Normal Firebase bağlantı kotasından **bir bağlantı** kullanır; sıfır maliyetli değildir.
- Yönetici kapalıyken ani Windows bildirimi gönderilmez: rapor bulutta saklanır, Yönetici açılınca gösterilir. Bulut fonksiyonu, e-posta ve ek ücretli servis **gerektirmez**.

## Yayın için kalan güvenli adımlar

1. [ ] Windows Yönetici ve Personel 6.6.0 kurulumları başarıyla derlendi; SHA256SUMS.txt kontrol edildi.
2. [ ] Cloud Shell'de `python3 tools/firebase_error_rules_cutover.py` ile **canlı Rules yedeği** alındı.
3. [ ] Yedek güvenli yerdeyse `python3 tools/firebase_error_rules_cutover.py --apply` ile sadece `error_reports` / `error_acks` izinleri yayımlandı.
4. [ ] Gerçek Windows cihazında hata akışı, Hata Merkezi, manuel SHA doğrulanmış güncelleme ve sipariş kuyruğu kontrol edildi.
5. [ ] GitHub'da kalıcı `v6.6.0` Release, iki EXE ve SHA256SUMS.txt **aynı sürüm etiketinde** yayımlandı. **Kişisel Drive linkleri otomatik güncelleme için kullanılmaz.**
6. [ ] GitHub'ın manuel release iş akışını kullanacaksan, iş akışını önce varsayılan dala taşı ve yalnız bu repoya yetkili `ALFA_RELEASE_TOKEN` secret'ını owner hesabıyla ayarla. Alternatif olarak GitHub Releases UI'da el ile yayımla.

## Veritabanı temizliği yaklaşımı

- Canlı siparişler, envanter satış geçmişi ve audit kaydı **silinmedi**: bunlar işletme delili.
- `error_reports` ve `error_acks` başlangıçta boştur. Yeni raporlar yalnız hata olduğunda eklenecek, tablo görünümünde son 70 kayıt gösterilecek.
- Eski operasyon verilerini ancak ayrıca yedek alıp işletme saklama gerekliliklerine uygun karar verdikten sonra arşivle/sil. Denetim izi olmadan otomatik DB purge yapılmadı.
- Eski `main` / Supabase dönemi ayrı tutulur. Şu anda kullanılan `alfa_cihaz.py` DPAPI kimlik koruma modülüne, 'eski' görünse bile dokunulmadı; silinmesi cihaz yetkilerini bozabilir.
- Mevcut Python uygulamasının çalışma dizini ve GitHub kaynak dosyaları doğrudan 1:1 EXE içine eklenmez; PyInstaller yalnızca bağımlılıkları ve açıkça tanımlanan varlıkları paketler. Salt belge/migrasyon dosyalarını silmek Firebase indirme kotasını azaltmaz.

## Doğrulanabilir kaynaklar

- `firebase/database.rules.json`: mevcut Rules yanında yeni erişim koruması.
- `alfa_hatalar.py`, `hata_merkezi_ui.py`: rapor üretimi / owner görünümü.
- `alfa_guncelleme.py`, `guncelleme_arayuzu.py`: güncelleme mekanizması.
- `.github/workflows/firebase-rtdb-preview.yml`: iki Windows installer + hash.
- `.github/workflows/alfa-stable-release.yml`: yetkili manuel kalıcı sürüm yayını.

**Not:** GitHub Actions sadece kaynak söz dizimini kontrol eder ve paketler. Kullanıcının önceki tercihine göre otomatik işlev testleri çalıştırılmaz. Gerçek cihazda fonksiyonel kabulü yapmadan üretim doğrulaması tamamlandı denmemelidir.
