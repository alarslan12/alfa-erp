# ALFA ERP V6.2.1 — Kurulum ve Uygulama İkonları

Bu sürüm Windows'a Python kurmayı gerektirmeyen iki ayrı yerel kurulum paketi içerir.

## Yeni
- **ALFA ERP Personel:** Koyu lacivert zemin üzerinde beyaz geometrik A ve turkuaz vurgu.
- **ALFA ERP Yönetici:** Aynı marka dili, altın vurgu ve yönetici rozeti.
- Windows **Setup.exe**, kurulu **EXE**, **masaüstü kısayolu**, **pencere başlığı / görev çubuğu** ve **bildirim ajanı** için uygulama ikonları artık özel olarak üretilir.
- Simge dosyaları 16, 24, 32, 48, 64, 128, 256 piksel çok çözünürlüklü ICO biçimindedir. Ayrıca PNG önizlemeleri sürüm dosyalarına eklenir.
- İkonları üretmek için kullanılan Pillow yalnızca derleme ortamında kurulur, son kullanıcının bilgisayarında Python veya Pillow gerekmez.

## Devam eden özellikler
- Yönetici ve personel uygulamaları doğrudan açılır; yalnızca Analitik bölümü PIN korumalıdır.
- Buluta işlem yazmak için ilk cihaz yetkilendirmesi hâlâ gereklidir; uygulama bağlantı olmadan açılabilir.
- Katalog, Siparişler ve var olan Supabase siparişleri bu ikon güncellemesi sırasında değiştirilmedi.

## Kurulum
1. Windows kurulum dosyalarını GitHub'daki `v6.2.1` Releases sayfasından indirin.
2. Daha önceki yerel kayıt ve kuyrukları korumak için `%LOCALAPPDATA%\AlfaERP` klasörünü yedekleyin.
3. İlgili `ALFA_ERP_Yonetici_Setup_V6_2_1.exe` veya `ALFA_ERP_Personel_Setup_V6_2_1.exe` dosyasını çalıştırın.
4. Genel kurulum dosyasında sunucu erişimi için gerekirse bir defalık **Buluta bağla** işlemini tamamlayın; uygulamayı açmak için giriş yapmanız gerekmez.

Kaynak dosya simgeleri `tools/build_icons.py` tarafından kurulum derlemesi öncesinde otomatik oluşturulur.
