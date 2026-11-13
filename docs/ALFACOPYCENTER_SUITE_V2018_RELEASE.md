# ALFACOPYCENTER Suite v2.0.18

**Katalog ve Siparişler:** Sayısal kitap kodu sıralaması; sipariş
detayında hazırlanma/kolilenme bekleyenler için aynı genişlikte bölünmüş
filtre; sekmelerde taşma düzeltmesi ve sekmeleri ayrı pencereye ayırıp
geri ekleme; kitap adı/sayfa alanı kompakt, iki satırlı başlıklar korunur,
SB/RNK butonları büyütülür, aradaki beyaz çizgi kaldırılır.

**Sipariş bildirimi:** Personel sistem tepsisi bildiricisi Windows
Zamanlanmış Görev ile oturum açılışında çalışır. ERP kapansa bile sesli
ve görsel uyarı alabilir. Yeni ilk sipariş #1 ve Firebase değişiklik
sinyalinde tekrar kontrol/dedup düzeltildi. Windows yerel kadın/erkek
konuşma sesleri ve isteğe bağlı ElevenLabs ses A/B desteklenir.
ElevenLabs API anahtarı Windows DPAPI ile şifrelenir; müşteri bilgileri
servise iletilmez. Windows oturumu açık olmalıdır.

**Diğer:** Dolap uzun kodu son dört haneli ayrı blokla biçimlenir.
Yatay ilk PDF sayfası 270° döndürülerek dikey kapağa oturtulur,
manuel kapaklar korunur. Tek Suite Personel/Yönetici/Banner/Print
ve ortak Güncelleme Merkezi korunur.

**Doğrulama sınırları:** CI'daki offline Qt/Firebase testleri gerçek
çoklu monitör sürükle-bırak, Windows Task Scheduler başlangıcı,
fiziksel ses donanımı veya ElevenLabs hesabını doğrulamaz.
