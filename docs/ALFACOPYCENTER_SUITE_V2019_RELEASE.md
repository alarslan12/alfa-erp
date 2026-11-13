# ALFACOPYCENTER Suite v2.0.19 — Analitik ve muhasebe düzeni

Personel, Yönetici, Banner Studio ve Print Center aynı Suite ve
Güncelleme Merkezi içinde kalır. Firebase ve mevcut veriler korunur.

## Analitik
- Ciro ve Tahsilat Durumu: Toplam Ciro, Kargo Sonrası Ciro, Ödenen
  Ciro, Ödenmeyen Ciro için ayrı, açıklamalı dört geniş kart.
- Ödenen/ödenmeyen: hesaplanan dönem içindeki "Ödendi" işaretli
  tamamlanma günlerine ait tutarlar; banka hesabı hareketi değildir.
- Ortalamalar/Birim Verimlilik ayrı grup: ort. sipariş, sayfa başına
  ciro, kitap/sipariş, sayfa/sipariş, kitap başı ortalama sayfa.
- Kargo Giderleri, Sipariş/İş Günü, Kitap/Sayfa ve Baskı türleri
  kendi bölümlerinde. Responsive 4/2/1 finans kart dizilimi.
- Kargo sonrası ciro formülü ve bunun net kâr olmadığı açıkça anlatılır.

## Telafi ve kargo
- Yeni ve düzenlenen Telafi siparişlerinde gelir 0 TL'ye zorlanır,
  fiyat alanı gizlenir. Telafi siparişi kargo gideri tamamlanırken sorulur.
- Açık adres siparişleri normal satış cirosunu korur, kargoları
  tamamlanırken ayrıca sorulur. Giderler analitikte ayrı ve toplamda
  yalnız bir kez düşülür.
- Geçmişte yanlış tutar girilmiş telafi kayıtları Analitik/HTML
  raporlarında satış cirosu olarak sayılmaz; arşiv kayıtları silinmez.

## Diğer
- PDF'de yatay ilk sayfalar +90° döndürülür (eski 270/-90 ters
  yönünden farklı); otomatik kapak önbelleği tazelenir.
- Kitaplara Genel Bakış açılır listesi ortak kurumsal menü temasını
  kullanır, Qt beyaz alt paneli kaldırılmış olur.

Saha doğrulaması: Gerçek Windows font ölçekleri ve mevcut PDF
dosyalarının fiziksel yönü kullanıcı bilgisayarında kontrol edilmelidir.
