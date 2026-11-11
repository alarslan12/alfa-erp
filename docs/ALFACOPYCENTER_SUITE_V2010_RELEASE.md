# ALFACOPYCENTER Suite v2.0.10 · Banner Studio v3.11

## Kapakların yönü ve yerleşimi
- Afiş motoru kaynak görselin EXIF yönünü düzeltir. Hâlâ yataysa **270 derece döndürür** ve kapak çerçevesine **kırpmadan, orantısını bozmadan** sığdırır.
- Katalog küçük önizlemeleri ve harici kapak küçük önizlemeleri de aynı kuralla dikey gösterilir.
- Yüklenmiş orijinal JPG/PNG dosyalarına dokunulmaz; geçmiş tasarım arşivi silinmez.

## Alt grup / set seçim doğruluğu
- Katalog araması grup ve kitap adını gelişigüzel birleştirerek bulanık arama yapmaz.
- Kullanıcı **YDUS** veya **DUSDATA 1+2** gibi mevcut Excel grup ismine uyan ifade yazarsa yalnızca uygun grup etiketli kitaplar gösterilir. Bir başka gruptaki kitap isminin içinde bu sözcüklerin geçmesi o kitabı gruba sokmaz.
- **1+2**, **1 + 2** yazımları aynı set ifadesi olarak değerlendirilir. Kelimeler tam token düzeyinde eşleştirilir; ör. `1` ve `1+2` ayrı tanımlardır.
- Grup listesindeki seçime göre toplu ekleme yalnızca `book.group === selectedGroup` olan Excel satırlarına uygulanır.
- Her katalog kartının altında **Excel'deki grup adı** görünür; hatalı kaynak grup etiketleri kullanıcı tarafından denetlenebilir.
- Kayıtlı arşiv tasarımı / proje düzenlemeye açılınca aktif seçimin kitap kodları ve grup etiketleri **güncel Excel ile** yeniden eşleştirilir. Arşivdeki kaynak kayıt değişmez.
- Güncel Excel'in kendi grup etiketi hatalıysa program bunu otomatik olarak doğru bir başka kategoriye tahminle taşımaz; Excel içindeki grup adı düzeltilmelidir.

## Korunanlar
- ERP Katalog ve Siparişler bölümleri, Firebase ve veri tabanı değiştirilmedi.
- Excel geçerli kitapları (adı ve kodu olanlar; sayfa sayısı zorunlu değil), arşiv ve markalama ayarları korunur.
- Otomatik testler kullanıcı tercihiyle çalıştırılmadı; Windows derleme sonucu GitHub Actions'ta izlenir.
