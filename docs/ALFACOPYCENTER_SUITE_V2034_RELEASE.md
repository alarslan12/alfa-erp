# ALFACOPYCENTER Suite v2.0.34 — Aktif sipariş üretim özeti (ön izleme)

- Aktif siparişlerin üst kısmında altı kompakt, tema uyumlu gösterge: aktif sipariş sayısı, toplam kitap/SB/RNK, kalan kitap, basılacak kitap/sayfa, kolilemeye hazır kitap, toplam ciro/sayfa.
- Kalan kitap = toplam - kolilenen; basılacak kitap = toplam - hazır; kolilemeye hazır = hazır - kolilenen.
- Kalan sayfa sayısı sipariş satırındaki gerçek nüsha ve sayfa bilgisiyle hesaplanır. Eksik sayfa bilgisi varsa belirtilir.
- Üretim toplamları filtrelerden bağımsız tüm aktif siparişleri kapsar. Filtrelenmiş sipariş sayısı ayrı gösterilir. İşlem ve seçim düğmeleri ayrı bir satırda kalır. Dar ekranda göstergeler iki satıra yerleşir.
- Mevcut sipariş hazırlama/kolileme, not sistemi, katalog, Firebase kuralları ve canlı veriler değiştirilmez. v2.0.33 özellikleri korunur; v2.0.30 kararlı kanalda kalır.
