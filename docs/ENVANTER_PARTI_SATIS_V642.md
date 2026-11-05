# ALFA ERP 6.4.2 — Envanter alış partisi, satış geçmişi ve son kabul

## Ne değişti?

Ürün ana kartı yalnızca kimlik/etiket/kategori/görsel gibi ürün
özelliklerini saklar. Stok miktarı ve maliyet ürün kartı düzenlenerek değiştirilmez.

Envanter → **Stok ve Envanter** → **Alım partisi ekle**:

1. Genel ürün kataloğundan ürünü seç.
2. Yeni alınan adet ve **o alımın birim maliyetini** gir.
3. Kaydet. Firebase alışın tarih/saatini otomatik UTC olarak saklar.
4. Aynı ürüne yeni fiyatla tekrar alım yaptığında **önceki partiyi değiştirmez**.

Ürün kartında kalan parti adetleri ve her birinin birim alış maliyeti,
**Partiler** penceresinde tüm alımlar (tükenenler dahil) görünür.

**Satış** düğmesinde hangi alış partisini sattığını seç, satılan adedi
ve o satışın **birim satış fiyatını** gir. Tek satış bir partiden yapılır;
iki partiden satış yapılacaksa iki ayrı hareket kaydet.

Satış fiyatı ürünün ana kartına zorunlu fiyat olarak yazılmaz.
Bir önceki satış fiyatı yeni satış penceresinde yalnız kolaylık için
ön değer olarak gösterilir; her satışta değiştirilebilir.

Firebase stok azaltımı + satış geçmişi, tek ürün üzerinde
**ETag koşullu tek işlem** olarak yapılır. Ağdan gelen eski
stok snapshot'ları üzerine yazılmaz; aynı partiden çakışan satışlar
yeniden miktar kontrolünden geçer. Beklenmeyen hatada veriyi
sahte biçimde başarıyla yazılmış göstermemek gerekir.

## Analitik ve kayıt

Envanter → **Satış analitiği**:

- Son 30 günün ciro grafiği
- 7/30/90/365 gün veya tüm zamanlar için satış geçmişi
- Satış adedi, ciro, satılan stokun alış maliyeti, **brüt fark ve oran**
- Çok satan ürünler, güncel stok sermayesi
- Satış tarihi, ürün, alım tarihi/parti, adet, alış fiyatı,
  satış fiyatı, ciro ve brüt fark satırları

Ekran en yeni **250 hareketi** görüntüler. Veri Firebase üzerinde
tam olarak korunur. Bu ekran ayrı polling/indirme yapmaz;
masaüstünün mevcut envanter snapshot'ını kullanır.

## Eski ürünler

Geçmişte yalnız bir toplam stok ve tek maliyet olarak girilmiş ürünler
kaybolmaz. İlk yeni alım/satış sırasında **Eski stok** adlı sanal parti
oluşturulur. Bu stokların gerçek alış tarihi bilinmediğinden ekran
bir ürünün oluşturulma tarihini alış tarihiymiş gibi göstermez.

Önceki satış geçmişi aynen tutulur. Geçmişte kaydedilmiş tek maliyet
alanıyla hesaplanan satışlar, o tarihte kaydedildiği maliyeti gösterir.

## Son üretim kontrolü

- [ ] Stok alımı sırasında artık \`QSpinBox already deleted\` hatası yok
- [ ] Aynı ürünün iki farklı maliyetli alımı **iki ayrı parti** olarak görünüyor
- [ ] Alış tarihi/saat ve kalan adetler doğru
- [ ] Bir partiden satış yapınca sadece o partinin kalan adedi azalıyor
- [ ] Satış fiyatı, Satış düğmesine basınca ayrı soruluyor
- [ ] Satış geçmişi ve kâr/maliyet doğru
- [ ] Yönetici ve Personel cihazında envanter tutarlı
- [ ] Kitap kataloğu ve Sipariş Havuzu değişmedi

Veritabanını yeniden sıfırlama. Üretim verileri korunur.
Bu sürümün Windows derlemesi kaynak sözdizimini kontrol eder,
otomatik uygulama işlev testlerini koşmaz. Kullanıcı son kabulü
yapılmadan kararlı sürüm etiketi kullanılmamalıdır.
