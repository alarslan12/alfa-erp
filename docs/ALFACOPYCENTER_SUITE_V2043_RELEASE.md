# ALFACOPYCENTER Suite v2.0.43 — İnteraktif platform pasta grafiği

- **Normal Analitik → PLATFORMA GÖRE GELİR DAĞILIMI:** Gardrops, Dolap, WhatsApp, Elden ve diğer kayıtlı satış platformlarının gelir yüzdesini gösteren interaktif halka/pasta grafik eklendi.
- Her dilim gerçek sipariş gelirini temsil eder, **sipariş adedini değil**. Yüzdeler seçili tamamlanma dönemi için hesaplanır.
- Pasta grafiğinde dilimin üzerine gelindiğinde platform adı, toplam TL satış geliri ve yüzde görülür; grafiğin yanında aynı renklerle açıklama listesi bulunur. Çok sayıda küçük platform varsa kalanları “Diğer platformlar” diliminde toplanır.
- Pasta grafik **iadeler düşüldükten sonraki satış cirosunu** kullanır. Kayıtlı kargo gideri pasta yüzdesini bozmak için negatif dilim olarak çizilmez; kargo ve iadeler sonrası nihai tutar ayrı muhasebe kartında korunur.
- Çizgi grafikler saf çizgi grafiktir, altları renk/dolgu ile kapatılmaz. Sol tarafta statik sayısal eksen etiketleri ve tepe noktasında sürekli duran değerler kaldırılmıştır.
- Her çizgi veri noktasına fareyle gelindiğinde tarih, seri adı ve **o noktaya ait gerçek sayısal değer** görülebilir; nokta geçici olarak parlayarak öne çıkar.
- Önceki v2.0.42 performans/finans düzeltmeleri, Normal Analitik ile FlexFlow alt ayrımı, Katalog ve Siparişler, Firebase kuralları ve kullanıcı verileri korunur.

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_43.exe`.

Kullanıcı veri klasörleri ve canlı Firebase siparişleri silinmez veya sıfırlanmaz; birinci kurulumun üstüne aynı AppId ile yükseltilir.
