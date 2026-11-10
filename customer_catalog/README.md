# alfacopycenter | Müşteri kitap kataloğu (önizleme)

## Güncel durum
- **303 kitap / 48 grup** mevcut `katalog.json` verisinden alındı.
- Mobil ve masaüstünde aynı responsive HTML katalog; kitap kodları, grup araması, toplu seçim, sepette gruplama ve WhatsApp / Telegram liste paylaşımı çalışacak şekilde hazırlandı.
- Müşteri giriş kapısı ad, soyad, e-posta, telefon ve onay ister. **Bu önizleme bunları Firebase'e yazmaz; kimlik veya bot doğrulaması yapmaz.** Müşteri bilgileri yalnızca kendi tarayıcı oturumunda tutulur ve kullanıcı paylaşım düğmesine bastığında seçtiği mesajlaşma uygulamasına aktarılır.
- Fiyatlar **henüz sağlanmadığı için boş**. Müşteriye kesin toplam uydurulmaz.
- Kapak görselleri **henüz gönderilmediği** için her kitap bir yer tutucu kullanır.
- **Firebase Hosting'e yayımlanmadı; canlı web adresi henüz yok.** Mevcut ERP ve mevcut mobil panel değiştirilmedi.

## Fiyat kuralları

Fiyatlar `pricing.json` içinde yönetilir. Örnek şema (sadece format göstermek için, rakamlar gerçek satış fiyatı değildir):

```json
{
  "units": {"71": 150, "72": 150, "79": 135},
  "segments": {
    "DUSAK Konu - Klinik Kitaplar": 950,
    "DUSAK Konu - Temel Kitaplar": 600
  },
  "sets": [
    {
      "id": "dusak-konu-set",
      "name": "DUSAK Konu Tam Set",
      "codes": ["71", "72", "73", "74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "84"],
      "price": 1420
    }
  ]
}
```

- **Tekli kitap:** Kitap kodu üzerinden `units[code]`.
- **Alt grup:** Grubun bütün kitapları tek adet seçiliyse `segments[grup]` uygulanır. Yalnız 5/8 kitap seçilse bile sepette birlikte görünür, ama tam grup indirimi uygulanmaz.
- **Tüm set:** `sets[].codes` içindeki bütün kitaplar seçilmişse set fiyatı uygulanır. Bu kayıt alt gruplardan önce fiyatlanır; aynı kitap iki kez fiyatlandırılmaz. İlave adetler normal tekli kitap fiyatıyla fiyatlandırılır.
- **Eksik fiyat:** Müşterinin seçtiği kitaplardan herhangi birinin fiyatı yoksa yanlış/genel toplam yerine **Fiyat bekleniyor** gösterilir.
- **Arama:** `tts klinik`, `tts temel` ve `tts set` gibi doğal ifade aramaları, kitap adlarını ve grup adlarını filtreler. Toplu seçimde ekranda sayfalanmış olanlar değil **tüm filtre sonucu** eklenir.

## Canlı Firebase bağlantısı

`config.json` içindeki `catalog_url` ve `pricing_url`, yalnızca halka açık ve **özel bilgileri içermeyen** JSON döndüren HTTPS adresleri olabilir. Önerilen üretim mimarisi:

1. Firebase Hosting'de `customer_catalog` dağıtılır.
2. Cloud Function veya kontrollü salt-okunur Firebase düğümü, yalnızca açık katalog, kapak bağlantıları ve yayınlanabilir satış fiyatlarını döndürür.
3. Müşteri kimlik bilgilerinin Firebase'e yazılması isteniyorsa **App Check / bot doğrulaması**, doğrulama sonrası kimlik, hız sınırı ve KVKK aydınlatması bulunan **ayrı sunucu uç noktası** yapılır. Açık RTDB yazma izni kesinlikle verilmez.
4. Kapak klasörü Firebase Storage veya CDN'ye yüklenir; `cover_url` değerleri kitap koduyla eşleştirilir. Storage kuralları sadece ilgili katalog kapaklarına anonim okuma izni verebilir.
5. GitHub'a asla özel anahtar, servis hesabı veya kişisel müşteri verisi gönderilmez.

## Gerekli gerçek veriler

- Güncel kitap kapakları (kodlara göre dosyalar / ZIP)
- **Her kitabın tekli satış fiyatı**
- **Her klinik ve temel grubun tam grup fiyatı**
- **Tüm set tanımları (kitap kodları) ve tam set fiyatı**
- Paylaşım için tercih edilen işletme WhatsApp numarası / Telegram hesabı (şimdilik müşterinin kendi paylaşım seçicisi kullanılır)

Bu sürüm bir ön yüz / başlangıç dosyasıdır. Henüz canlı Firebase entegrasyonunu, mesaj iletim sunucusunu veya doğrulanmış müşteri kaydını içermemektedir.
