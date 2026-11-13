# ALFACOPYCENTER Suite v2.0.26 — TUSDATA Konu PDF eşleştirme ve boş sayfa filtresi

v2.0.25 üzerine hedefli bir onarım; çalışan PDF ve JPEG kapak önbelleği, manuel kapaklar, katalog verileri ve Firebase siparişleri değiştirilmez.

## Kapak eşleştirmesi
Excel'de TUSDATA Konu kitapları 365–389 kodları arasındadır; sayfa bilgileri doludur. PDF klasöründeki örn. `Dahiliye 1 - TUSDATA Konu.pdf`, `TUSDATA Konu Dahiliye 1. Cilt.pdf` ve `TUSDATA Konu Dahiliye Cilt I.pdf` aynı katalog kitabına eşleşebilir. Kitap adı eşleştirmesinde yayınevi/seri, ders ve cilt numarası birlikte doğrulanır. Sadece sıralama ve `Cilt` ibaresi esnektir; numaralar farklıysa yanlış eşleşme yapılmaz.

Eşleşmeyen gerçek PDF adları, katalogda PDF olmayan kitap sayısından ayrı sayılır. Ayrıntılı tarama raporu: `%LOCALAPPDATA%\AlfaERP\alfa_pdf_eslestirme_raporu.json`. Ayarlar → Kitap PDF klasörü → Tara ve kapakları güncelle işlemini kullan.

## Sayfa bilgisi boş kitaplar
Sayfa sayısı 0 veya boş olan kitaplar Katalog'da **varsayılan olarak gizlenir**. Bu tercih önceki sürümde açık ise ilk geçişte bir kez kapatılır. Ayarlar → Görünüm bölümündeki `Sayfa sayısı olmayan kitapları katalogda göster` kutusu işaretlenirse tekrar görüntülenebilir. Filtre yalnızca Katalog kartlarını etkiler; Excel, Firebase, geçmiş siparişler veya stok kayıtları silinmez. Başlangıç anında Personel ve Yönetici ekranlarında aynı filtre çalışır.

## Güvenlik
Manuel kapaklar önceliklidir, eski JPEG'ler korunur; PDF önbellek sürümü değiştirilmez. PDF'ler internete yüklenmez. Gerçek PDF dosya adları görülmeden tüm kapakların eşleşeceği garanti edilmez. Kurulumdan önce `%LOCALAPPDATA%\AlfaERP` klasörünü yedekleyin.
