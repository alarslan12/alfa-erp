# ALFACOPYCENTER Suite v2.0.11 · Banner Studio v3.12

## Kapak görünmeme düzeltmesi
- Excel'deki kod ile yüklenen kapağın dosya kodu aynıysa, başlık birebir yazılmamış olsa bile görsel artık reddedilmez. Cerrahi / Radyoloji gibi kısaltılmış, farklı yayıncı adı içeren başlıklar yeniden görünür.
- Kodlar tam olarak eşleştirilir; `14` ve `140` karıştırılmaz.
- Yeni Excel yüklendiğinde yüklenmiş kapakların yanı sıra paket içindeki önceden mevcut kapaklar da tekrar değerlendirilir. Paket içi kapak için kitap kodu ve uyumlu başlık aranır.
- Kodu değişmiş eski görsel yalnızca kitap ismi *tam ve tekil* eşleşiyorsa geri bulunabilir; rastgele yakın adlı başka kapağa bağlanmaz.
- Harici kapak yükleme işlemi artık mevcut bütün kapakların birleşik indeksini korur; diğer kapakları kaybettirmez.
- 270 derece otomatik yatay kapak döndürme, önceki Excel filtreleri, arşiv ve ayarlar korunur.

**Önemli:** Bu kod, bilgisayarda var olan kapakları yeniden eşleştirir. Kaynak görsel gerçekten silindiyse geri getiremez; o görseli yeniden yüklemek gerekir. Kapak arşivine ve geçmiş kayıtlara dokunulmaz.

Kullanıcı tercihi uyarınca otomatik testler çalıştırılmadı. Windows kurulum sonucu GitHub Actions üzerinden doğrulanmalıdır.
