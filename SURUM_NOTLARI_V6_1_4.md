# ALFA ERP V6.1.4 — Sipariş İlerlemesi ve Yönetici Teması

## Kritik sipariş akışı düzeltmesi
- Buluttan alınmış siparişlerde durum değişikliği ve hazırlama/kolileme tıklamaları tam sipariş yeniden yazma isteğine dönüşmüyor; ayrı küçük RPC hareketleri kuyruklanıyor.
- Arka arkaya tıklamalar yerel veri kuyruğunda güvenli sırayla tutuluyor; yeni hareketlerde hedef sayaç değerleri de gönderiliyor.
- Sunucuda eşzamanlı iki bilgisayar aynı kitabı işaretlediğinde hazırlama adedi gereksiz iki kez artmıyor; mevcut eski sürümler için additive geriye uyumluluk korunuyor.
- Reddedilen işlem artık yanlışlıkla “Bulut bağlı” olarak gizlenmiyor. Üst alanda uyarı ve hatanın nedeni gösteriliyor. Sorunlu kayıt kuyruk çakışma arşivinde korunuyor.
- Veriler ve eşleştirme anahtarları sıfırlanmaz. V6.1.3 için eski bulut API uç noktaları kaldırılmaz.

## Yönetici uygulaması
- Bilgisayarlar ve İşlem Günlüğü ekranı Koyu / Açık / Yüksek Kontrast temalarına uygun bağımsız renk paletleriyle düzenlendi.
- Tek işlem günlüğü: ikonlu olay kartları, okunabilir Türkçe olay adları, Tümü / Major / Minor filtreleri.
- Gürültülü düşük seviyeli veritabanı olayları, gösterimde gruplanıp ayıklanır; gerçek denetim kayıtları silinmez.
- Yeni progress/transition hareketlerinin kitap kodu ve hedef değişiklikleri (kişisel adres içermeyen) bulut işlem günlüğünde tutulur.

## Veritabanı
- Eski siparişler değiştirilmedi; geçici SQL regresyon işlemleri ROLLBACK ile geri alındı.
- Cihaz güvenliği ve audit yetkileri korunur.

## Testler
- Windows 2022 Python / Qt GUI testleri
- Buluttan alınmış siparişte Havuz → Aktif → Hazırlama/Kolileme → Havuz işlem kuyruğu
- Yönetici üç tema, cihaz tablosu, Major/Minor günlüğü
- Gerçek PyInstaller EXE açılış testi ve Setup.exe derleme doğrulaması

## Kurulum
Eski ERP ve bildirim hizmetini kapatıp %LOCALAPPDATA%\\AlfaERP klasörünü yedekleyin.
Mevcut V6.1.3 kurulumlarının üzerine V6.1.4 yönetici veya personel kurulum dosyasını çalıştırın.
Cihaz eşleştirmesi ve bekleyen işlemler korunmalıdır.

Sınırlama: Yapılan değişiklikler otomatik testleri geçse de iki ayrı gerçek bilgisayarda aynı sipariş üzerinde uzun süreli ağ yükü testi henüz tamamlanmamıştır. Ağ/sunucu çakışmalarında gerçek iş kuralı ihlalleri yine reddedilebilir.
