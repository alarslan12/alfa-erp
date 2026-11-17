# ALFACOPYCENTER Suite v2.0.39 — Banner arşivi, iade sebebi ve masaüstü optimizasyonu

- Banner Studio Pro: Tasarım Arşivi içinde tasarım adı/tarih/kitap sayısı arama; filtreli toplu seçim ve sonuç sayacı; silme, yeniden adlandırma ve içe aktarmada kaydırma konumunu koruma. Görseller gecikmeli yüklenir.
- Yönetici: İade edilen sipariş için zorunlu 1–500 karakter sebep; sonradan düzenleme; Personel ve Yönetici kartlarının altında açıklama.
- İade sebebi mevcut Firebase iade işlemiyle owner-only, çakışma denetimli ve olay günlüğüyle saklanır. İade geri alındığında gerekçe aktif sipariş verisinden kaldırılır.
- Masaüstü: Firebase değişiklik bildirimleri 180 ms içinde birleştirilir; gizli sipariş/katalog ekranlarını gereksiz yeniden çizmeden açıldıklarında güncel gösterir.
- Analitik hesapları, mevcut veri saklama, çevrimdışı kuyruk ve Firebase güvenlik kuralları korunur.
- Suite Personel, Yönetici, Banner Studio Pro ve Print Center aynı tek Windows Setup içindedir.
