"""Offline embedded ALFACOPYCENTER Suite release history.

This is shipped inside every ERP EXE so notes are available without GitHub
or Firebase connectivity. Exact historical release pages remain accessible at
https://github.com/alarslan12/alfa-erp/releases.
"""

_RELEASES = [
    ("2.0.21", "PDF kapak görünürlüğü ve eşleşme güncellemesi", [
        "Küçük ama geçerli JPEG kapaklar katalogdan gizlenmez.",
        "Tam PDF dosya adı eşleştirmesi güvenli kapak/baskı eklerini destekler.",
        "Otomatik PDF kapak önbelleği v5'e yükseltildi; yeniden tarama gerekir.",
        "Yatay PDF kapakları -90 derece döner; manuel kapaklar korunur.",
        "Önceki Excel, Analitik PIN, hata ve cihaz temizliği revizyonları korunur.",
    ]),
    ("2.0.21", "PDF kapak taraması ve kitap eşleşmesi onarımı", [
        "Yatay ilk PDF sayfaları -90 derece döndürülür ve ters yönlü önbellek yenilenir.",
        "PRETUS 3 kitabının 402 kodu ile PDF'nin tam adı eşleşebilir.",
        "PDF adındaki seri sayıları yanlış kitap kodu olarak kullanılmaz.",
        "Belirsiz veya yinelenen PDF kaynakları raporlanır, yanlış görsel atanmaz.",
        "Eski otomatik kapaklar diskte korunur; doğrulanmamışsa katalogda kullanılmaz.",
        "Firebase Excel kitap katalog revizyonunda yerel PDF kapakları yeniden taranır.",
        "Ayarlar ekranında eksik kapak örnekleri ve yerel JSON tanı raporu bulunur.",
    ]),

    ("2.0.19", "Analitik ciro odağı ve telafi muhasebesi", [
        "Toplam, kargo sonrası, ödenen ve ödenmeyen ciro dört belirgin açıklamalı kartta toplandı.",
        "Ortalama sipariş, sayfa başı ciro ve kitap başı ortalamalar ayrı verimlilik grubuna taşındı.",
        "Telafi siparişi oluşturma ve düzenlemede ciro otomatik 0 TL; kargo gideri tamamlanırken sorulur.",
        "Eski telafi siparişindeki hatalı ciro Analitik ve HTML muhasebe toplamlarına dahil edilmez.",
        "Telafi/açık adres kargo giderleri ayrı gösterilip kargo sonrası tutardan tek kez düşülür.",
        "Yatay ilk PDF kapaklar ters yön yerine +90° döndürülür; eski otomatik kapak önbelleği yenilenir.",
        "Genel Bakış filtreleri beyaz boşluksuz kurumsal açılır liste stilini kullanır.",
    ]),
    ("2.0.18", "Sipariş görünümü, bildirim ajanı ve yatay kapaklar", [
        "Sipariş detayları ve genel bakış kitapları sayısal kitap koduna göre sıralar.",
        "Hazırlanmayanlar ve kolilenmeyenler aynı pillbox'ta ayrı filtrelenebilir.",
        "Sipariş sekmeleri kaydırılabilir, dışarı sürüklenerek ayrı pencereye alınabilir ve geri eklenebilir.",
        "Katalog başlık bandı iki satırı koruyarak kısaldı; SB/RNK sayaçları büyüdü ve aradaki çizgi kaldırıldı.",
        "Dolap uzun kodunun son dört hanesi ayrı gruba dönüştürüldü.",
        "Windows Zamanlanmış Görev ile ERP'den bağımsız Firebase sipariş bildirimi ve doğal ses seçenekleri.",
        "Yatay PDF ilk sayfası 270 derece döndürülerek kapaklara oturtulur.",
    ]),
    ("2.0.17", "Firebase kitap kodları, 0 sayfa ve Excel kurtarma", [
        "Buluttaki eski kod kaymaları Excel'deki kodlara göre, sunucu doğrulamalı olarak düzeltilir.",
        "Katalogun eski kopyası otomatik saklanır ve tam yazma doğrulanmadan revizyon artışı yapılmaz.",
        "Yeni siparişlerde kitap adı ve sayfa anlık görüntüsü Firebase'e doğru gönderilir.",
        "Eski 0 sayfa kaydı katalogda doğru sayfa biliniyorsa ekranda düzeltilir.",
        "Mobil katalog önbelleği ve sipariş sayfa toplamları katalog değişiminde güncellenir.",
        "Cloud Shell üzerinden salt-okunur fark kontrolü ve kontrollü kurtarma eklendi.",
    ]),
    ("2.0.16", "Analitik PIN açılış güvenliği", [
        "Personel ve Yönetici PIN kontrolü artık GUI iş parçacığına yönlendirilen Qt slotları ile sonuçlanır.",
        "İş parçacığı bitişinde pencereyi doğrudan sonlandırma/iş parçacığı bekleme yarışı giderildi.",
        "Analitik raporun yeniden çizimi ve boyut değişimi sırasında iç içe render korunur.",
        "Personel PIN sonrası Analitik ekranı için Windows regresyon testi eklendi.",
    ]),
    ("2.0.15", "Geçmiş notlar, Personel Excel ve temizlik araçları", [
        "Personel ve Yönetici güncelleme ekranları önceki Suite revizyonlarını çevrimdışı gösterir.",
        "Personel, yetkilendirilmiş Firebase cihazından Excel kitap kataloğu aktarabilir.",
        "Yönetici, eski pasif cihazları ve hata raporlarını onayla temizleyebilir.",
        "Mevcut siparişler, katalog kartlarının düzeni ve Suite bileşenleri korunur.",
    ]),
    ("2.0.14", "Yönetici kurulum koruması ve Cloud Shell", [
        "Yönetici bileşeni için yerel kurulum şifresi; Personel, Banner ve Print şifresiz.",
        "Firebase owner yetkisi yerel şifreden bağımsızdır ve Cloud Shell'de onaylanır.",
        "Tek Suite kurulumu, önceden seçilen bileşenler ve kullanıcı verileri korunur.",
    ]),
    ("2.0.13", "Firebase ile dört bileşenli Suite bütünleşmesi", [
        "Personel ve Yönetici Firebase RTDB, canlı SSE ve çevrimdışı kuyruk kullanır.",
        "Banner Studio ve Print Center aynı Suite Setup'a geri eklendi.",
        "Ortak Güncelleme Merkezi, SHA-256 kontrolü ve v2 Suite yayın kanalı.",
        "Gardrops satışına girilen ciroyu %100 koruyan düzeltme.",
        "Eski bulut bağımlılıkları, yinelenen kurulumlar ve geçiş araçları temizlendi.",
    ]),
    ("2.0.12", "Banner Studio özel fiyat etiketi", [
        "Kitap kapağındaki fiyat farkı yazısının punto ayarı düzeltildi.",
        "Gerektiğinde iki satırlı etiket ve taşma önleyici yerleşim kullanılır.",
    ]),
    ("2.0.11", "Banner Studio kapak eşleştirme", [
        "Kapak dosyasının kitap kodu eşleşiyorsa farklı başlık nedeniyle reddedilmesi düzeltildi.",
        "Cerrahi/Radyoloji gibi kısaltılmış isimler ve kapak arşivi korunur.",
    ]),
    ("2.0.10", "Banner Studio döndürme, alt grup ve setler", [
        "Yatay kapaklar 270° çevrilerek orantısı korunur.",
        "YDUS, DUSDATA 1+2, ÇTS/TTS gruplarında doğru Excel etiketlerine göre arama.",
        "Arşivdeki tasarım açıldığında kodlar güncel katalogla eşleştirilir.",
    ]),
    ("2.0.9", "Banner Studio Excel veri yenileme", [
        "Kitap adı ve kodu varsa sayfa sayısı boş olan satırlar da kabul edilir.",
        "Yeni Excel eskisinin yerine geçer; tasarım ve kapak arşivi silinmez.",
    ]),
    ("2.0.8", "Banner Studio Excel şablonu doğrulama", [
        "Boş yer tutucular ve mükerrer kitap kodları için veri kontrolleri.",
        "Hatalı içe aktarma mevcut afiş arşivini değiştirmez.",
    ]),
    ("1.1.2", "Firebase ilk iyileştirmeler", [
        "Çevrimdışı yeniden açılış için doğrulanmış çalışma alanı işareti.",
        "Başlangıç kontrolleri, hızlı bağlantı kurtarma ve korunan işlem kuyruğu.",
    ]),
    ("1.1.1", "Güncelleme Merkezi güvenilirliği", [
        "Güncelleme sırasında gerçek ERP penceresinin güvenli kapanışı.",
        "Bekleyen işlemlerle güncellemeyi durdurma ve yeniden başlatma düzeltmeleri.",
    ]),
    ("1.1.0", "Envanter, eşitleme ve duyurular", [
        "Yönetici satış iptali: stok partilerine güvenli geri alma ve satış arşivi.",
        "Siparişlerde çakışma kurtarma, Hata Bildir, Duyurular ve günlük sürüm kontrolü.",
    ]),
    ("1.0.0", "Firebase ERP ilk birleşik Windows sürümü", [
        "Personel/Yönetici seçimi, Firebase RTDB ortak sipariş havuzu, hata merkezi.",
        "SHA-256 doğrulamalı GitHub güncellemesi ve owner cihaz yetkisi.",
    ]),
]


def release_history_markdown(installed=None):
    """Full offline version log; retains previous v1/v2 releases."""
    lines=["# ALFACOPYCENTER Suite · Sürüm geçmişi",
           "Kurulu sürüm: **v"+str(installed or "bilinmiyor")+"**",
           ""]
    for number,title,items in _RELEASES:
        lines.extend(("## v"+number+" — "+title,""))
        lines.extend("- "+item for item in items)
        lines.append("")
    lines.append("Daha eski ve ayrıntılı sürüm kayıtları: "
                 "https://github.com/alarslan12/alfa-erp/releases")
    return "\n".join(lines)
