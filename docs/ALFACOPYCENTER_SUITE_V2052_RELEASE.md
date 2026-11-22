# ALFACOPYCENTER Suite v2.0.52 — Fason Sipariş ZIP Baskı Adedi ve Talimat Özeti

## ERP Personel / Yönetici
- Sipariş derleme ZIP dosyalarındaki her PDF'nin adı baskı adediyle başlar: `2 ADET - DOSYA_XXXXXXXXXXXX.pdf`. Bir adetlik dosyalarda da `1 ADET` yazılır.
- `BASKI_TALIMATI.txt` üç satırdan oluşur: **Sipariş Kodu**, **Toplam Sayfa Sayısı** ve **Toplam Kitap Sayısı**. Dosya bazlı tekrar eden baskı listesi kaldırılmıştır.
- Sayfa hesabı mevcut ERP `Database._book_page_count` hesabını takip eder: sipariş satırındaki tarihsel `sayfa_birim` / `sayfa` bilgisi, yoksa katalog sayfa değeri kullanılır. SB ve RNK baskılar adetleriyle toplanır.
- Tekli veya seçili kitaplar derlenirse sayfa ve kitap sayıları yalnız oluşturulan ZIP'in içeriğine aittir.
- Kaynak kitap PDF'leri yeniden kodlanmaz, anonimleştirilmez, ZIP'de tekrar sıkıştırılmaz veya sunucuya gönderilmez; orijinal baytlar korunur. İçerikler PDF içinde bulunan metadata ve filigranları hâlâ taşıyabilir.
- Siyah/Renkli klasörleri, rastgele dosya kimlikleri, `Sipariş N.zip` Masaüstüne otomatik kayıt, önceki ZIP'leri koruma ve eksik kaynakta işlem iptali korunur.

## Diğer Suite bileşenleri ve veriler
- Personel, Yönetici, Banner Studio, Print Surveillance ve yardımcı bileşenler tek Windows Suite Setup kurulumunda kalır. Mobil katalog ve diğer uygulamaların işlevsel dosyaları değiştirilmemiştir.
- Firebase Authentication/Realtime Database, Hosting/Rules, yerel kullanıcı geçmişi, siparişler, arşivler, ayarlar ve cihaz izinleri korunur.
- Windows CI, dört Suite bileşeninin EXE açılış kontrolleri ve SHA-256 doğrulaması release iş akışında yapılır. Gerçek yazıcıda fiziksel baskı testi yoktur.

Kaynak PR: https://github.com/alarslan12/alfa-erp/pull/27

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_52.exe`.
