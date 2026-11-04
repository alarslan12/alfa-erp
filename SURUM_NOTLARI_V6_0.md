# ALFA ERP V6.0 Beta — Performans ve Görsel Envanter

## Değişenler
- Hazırlama, kolileme ve sipariş durumu işlemleri artık GUI thread içinde HTTP beklemez.
- Değişiklikler önce yerel diske kaydedilir, dayanıklı `alfa_outbox.json` kuyruğuna eklenir ve arka planda ~2 saniyede bir gönderilir.
- Hazırlama/kolileme hareketleri benzersiz işlem kimliği ile Supabase'e delta olarak aktarılır; başarısız ağ çağrıları otomatik yeniden denenir.
- Diğer bilgisayarlar 1,8 sn'de bir sadece küçük değişiklik kontrolü (`pulse`) sorgular; değişim varsa tam görüntüyü alır.
- Windows arka plan bildiricisi 2,1 sn'de bir değişiklik kontrolü yapar.
- Envanter ana sekmesi görsel ve farklı boyutlu yatay kartlar, filtreleme, kategori/etiket arama, ürün oluşturma, görsel yükleme, satış, stok sayısı ve satış analitiği içerir.
- Ürün oluşturma/düzenleme yöneticinin Supabase hesabıyla kimlik doğrulamasını gerektirir. Çalışanlar ürünleri görebilir ve cihaz anahtarı üzerinden satış kaydı girebilir.
- Envanter verileri, görseller ve satışlar aynı Supabase projesinde saklanır; cihazlar arasında yenilenir.
- Önceki kitap kataloğu, sipariş ekranının düzeni, analitik parolası ve yönetici/personal ayrımı korunur.

## Önemli sınırlar
- Bu kaynak sürüm Windows üzerinde test edilmedi. Kullanıcının tercihi doğrultusunda testler çalıştırılmadı.
- İyimser yerel değişiklikler buluta onay gelene kadar ekranda görünür. Ağ kesilirse yerel kuyrukta kalır; 'Bulut bağlı/işlem sırada' durumunu izleyin.
- Aynı siparişin iki cihazda çakışan durum değişiklikleri sunucuda reddedilebilir; yerel kuyruk korunur ve kullanıcıya bekleme/çatışma bilgisi gösterilir. Sayısal hazırlama/kolileme hareketlerinde toplamalı birleştirme uygulanır.
- Ürün satış geliri ile maliyet arasındaki fark, baskı/operasyon/komisyon giderlerini içermez; 'tahmini brüt fark' olarak gösterilir.
- Windows için doğrudan EXE bu Linux çalışma ortamında derlenemedi. Personel paketi, yönetici Windows bilgisayarında `URET_SETUP_EXE_WINDOWS.bat` ile tek dosyalı Inno Setup kurulumuna dönüştürülebilir. Çalışan PC'ye Python kurulmaz.
- Tek kullanımlık bilet yalnızca bir yeni bilgisayar içindir. Mevcut eşleştirilmiş bilgisayarlarda DPAPI cihaz anahtarı korunur.

## Güncelleme talimatı
1. Uygulamayı ve bildirim ajanını kapatın. `%LOCALAPPDATA%\AlfaERP` klasörünü yedekleyin.
2. Yeni yönetici sürümünü farklı klasöre çıkarın. Önce Windows'ta `KUR_WINDOWS.bat`, sonra `BASLAT_WINDOWS.bat` çalıştırın.
3. Personel sisteminde mümkünse yönetici PC'de `URET_SETUP_EXE_WINDOWS.bat` kullanıp çıkacak `output\ALFA_ERP_Personel_Setup_V6_0.exe` dosyasını yükleyin.
4. Yönetici laptopunda ürün eklemek için önce üstteki **Yönetim** düğmesinden admin girişini yapıp **Envanter** ana sekmesine dönün.
5. Müşteri mobil web kataloğu önceki sürümdeki gibi çalışmayı sürdürür; yeni ürün envanteri şu anda personel/owner masaüstü modülüdür.

## Sürüm
V6.0 Beta — 2026-11-04
