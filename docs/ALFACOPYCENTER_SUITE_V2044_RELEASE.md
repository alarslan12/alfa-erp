# ALFACOPYCENTER Suite v2.0.44 — Onaylanan Analitik mockup'ının uygulanması

**Amaç:** Kullanıcının onayladığı koyu lacivert gösterge paneli düzenini PySide6 uygulamasına taşımak; renkli dolu alan görünümü, gizlenen Y ekseni ve her yerde açılan bulut durum tooltip'ini onarmak.

## Normal Analitik çizgi grafikleri

- QPainter'ın önceki çizimden kalan aktif fırçası temizlenir. `QPainterPath` açık yolunun Qt tarafından kapatılarak renkli bir çokgene doldurulması engellenir: `Qt.BrushStyle.NoBrush`.
- Grafiğin altı şeffaftır (alan grafiği yok), sadece 2,4 px çizgi vardır. Az sayıda gün olduğunda küçük, kontrastlı nokta işaretleri kullanılır.
- Dikey Y ekseninde **sayısal ölçek etiketleri** geri gelir, yatay tarihler okunur. Noktanın tam sayısal değeri sadece fare üzerinde açılan tooltip ile gösterilir.
- Ana pencerenin `setToolTip(message)` çağrısı kaldırılır; bulut durumu yalnızca bağlantı rozeti üzerinde açıklama gösterir. Böylece grafik tooltip'i örtülmez.

## Platform gelir grafiği ve özetler

- Platforma göre gelir donut grafiği tüm satır yerine tek bir **kompakt istatistik kartı** halindedir, başlığı kartın içindedir.
- Yanındaki özet kart aynı grid satırında, şu **kayıtlı seçili dönem metrikleriyle** oluşturulur: İade/kargo sonrası net ciro, basılan sayfa, kitap adedi, SB/RNK kitap adedi.
- Küçük pencerelerde grafik kartı ve özet kartı dikey istiflenir; büyük pencerelerde iki sütun düzeni kullanılır.
- Mockup'ta örnek gösterilen önceki dönem büyüme yüzdeleri uygulamada hesaplanmamışsa **uydurulmaz**.
- Gelir donut'u iade düşülmüş satış cirosundan platform paylarını hesaplar. Kargo giderleri mevcut nihai ciro panelinde düşülür; donut dilimlerine negatif maliyet payları eklenmez.

## Geriye dönük uyumluluk

- Katalog ve Siparişler ekranları, Firebase güvenlik kuralları, müşteri/sipariş kayıtları, Analitik finans mantığı ve FlexFlow modeli değişmedi.
- Mevcut Suite `AppId` ve veri klasörleri korunur; yeniden kurulum mevcut kayıtları silmez.

Windows çıktı dosyası: `ALFACOPYCENTER_Suite_Setup_V2_0_44.exe`.
