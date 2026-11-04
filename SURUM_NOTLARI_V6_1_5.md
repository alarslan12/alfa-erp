# ALFA ERP V6.1.5 — Bulut Eşitleme ve Genel Ürün Kataloğu

## Kritik canlı bağlantı onarımı (Supabase'de yayımlandı)
- İlk eşitlemede 403 ve buna bağlı 500 hatası oluşturan `erp_authorized_sync` fonksiyonu, eski JWT ayarı yerine gerçek SQL `service_role` yetkisini kontrol ediyor.
- Sunucu: Yetkili servis için 200 yanıtı, anonim erişim reddi doğrulandı.
- Mevcut cihaz eşleştirme anahtarları, siparişler, stok miktarları ve denetim kayıtları korunmuştur.
- Sunucu düzeltmesi mevcut 6.1.4 istemcilerine de uygulanır; yeni kurulum bu düzeltmenin şartı değildir.

## Katalog ve Envanter artık ayrı akış
- Kitap sipariş ekranı korunur. Katalog üstünden Kitap Kataloğu / Genel Ürünler arasında geçiş yapılır.
- Genel Ürünler: bütün bilgisayarlarda ortak ürün kartları, arama, kategori, etiket, fiyat ve görsel.
- Yeni ürün kataloğa stok 0 ve `in_inventory=false` olarak kaydedilir.
- Envanter: "Katalogdan envantere ekle"; ürün seçme, yeni toplam adet, satış fiyatı, maliyet belirleme. Aranmış metin yanlış ürünün kaydına dönüşmesin diye listeden kesin seçim gereklidir.
- Mevcut stoklu ürünler `in_inventory=true` olarak korunur; başlangıçta envanterden kaybolmaz.
- Katalogdaki ürünler sipariş kitap satırlarıyla karıştırılmaz.
- Yeni ürünler veritabanında saklanır, envanter değişiklik sayacı sayesinde diğer bilgisayarlarda görünür.

## Geçmiş başarısız işlemler
- Eski çakışma arşivi "21 işlem onaylanmadı" gibi aktif kuyruk anlamı taşıyan ifadeler yerine geçmiş kayıt olarak belirtilir.
- Yönetici > Ayarlar > İşlem Günlüğü > Eski bulut hatalarını incele: hata ayrıntılarını açıp inceleme durumunu işaretleyebilir.
- İnceleme, sipariş verisini/işlem kayıtlarını silmez ve eski hareketleri yeniden göndermez.
- Bulut eşitlemesi tekrar hata verirse o güncel bağlantı hatası eski çakışmaların arasında gizlenmez.

## Testler
- Windows birim ve GUI testleri: genel katalog, stoktan ayrı ürün kartı, tema ve sipariş akışları.
- Supabase işlemi: yetkili servis, anonim reddi, stok seçimi, fiyat güncellemesi ve envanter revizyonu. Veri değişimleri ROLLBACK ile geri alındı.
- Windows paket açılış testleri: yönetici ve personel 303 kitap / 5 ekran.

## Kurulum
Uygulamaları ve arka plan bildirim servisini kapat. Yerel dosya klasörünü yedekle:
`%LOCALAPPDATA%\\AlfaERP`.
Ardından V6.1.5 Setup.exe kurulumunu V6.1.4 üzerine yap.
Gerçek iki bilgisayarda işlemlerin eşzamanlı görünmesi ayrıca kullanıcı cihazlarında doğrulanmalıdır.

Not: V6.1.4 öncesinden gelen ve daha önce reddedilmiş işlemler otomatik tekrar gönderilmez; hatalar korunur ve gerekirse güncel sipariş üzerinde kullanıcı tarafından tekrar uygulanır.
