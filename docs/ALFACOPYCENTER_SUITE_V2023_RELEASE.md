# ALFACOPYCENTER Suite v2.0.23 — Kapak ve sayfa verisi kurtarma

v2.0.20–v2.0.22 PDF taramasındaki boş/uyuşmayan manifest, önceki otomatik JPEG kapakları gizleyebiliyordu. Gerçek tarama kaynağı olan eski kodlu JPEG'ler kurtarma durumunda yeniden görünür. Yeni tarama hiç eşleşme bulmazsa mevcut manifest korunur.

Bulutun sayfa sayısı 0 veya boş olsa bile aynı kod+kitap adına sahip önceden bilinen sayfa sayısı yerelde korunur. Koruma kaydı: %LOCALAPPDATA%\AlfaERP\alfa_katalog_sayfa_kurtarma.json. Firebase'e kendiliğinden yazılmaz.

Personel/Yönetici Excel seçiminde dolu ve boş sayfa sayıları ayrı görülür. 478 kayıtlı KİTAPLAR Excel'inde 329 sayfa sayısı dolu, 149 boş. Boş değerleri tahmin etmeyin. Eksik veri için doğru Excel'in Yönetici üzerinden, yedek alınarak ve doğrulanarak buluta içe aktarılması gerekir.

Güncellemeden önce %LOCALAPPDATA%\AlfaERP ve kaynak Excel/PDF klasörlerini yedekleyin. Kurulum sonrası Ayarlar → Kitap PDF klasörü ile gerçek eşleşmeleri kontrol edin.

Sipariş, arşiv, manuel kapak, Banner Studio, Print Center ve Firebase yetkileri korunur.
