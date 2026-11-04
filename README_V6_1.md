# ALFA ERP V6.1 — stabil senkronizasyon ve sade yönetici

- Yönetici, **YONETICI_WINDOWS.bat** ile başlar. Supabase admin e-posta/şifresi doğrulanır, normal ERP ekranı açılır. Ek yönetim penceresi kaldırıldı.
- Ayarlar: Görünüm, PDF klasörü, Excel kataloğu, Bilgisayarlar, tek İşlem Günlüğü.
- Personel: Herhangi bir hesap giriş ekranı bulunmaz. Analitik, önceki sürümdeki yerel şifre kontrolüyle korunur.
- Sipariş hazırlama/kolileme ve durum ilerletme işlemleri yerel kuyrukta kalıcı biçimde tutulur, arka planda sırayla ve idempotent olarak gönderilir.
- HTTP 409 bir internet kesintisi değildir; işlem ayrı çakışma dosyasına kaydedilir, diğer işlemlerin önünü kesmez.
- V6.0 eski kuyruğunu korumak için mevcut %%LOCALAPPDATA%%\AlfaERP klasörünü SİLMEYİN. Önce tam yedek alın.
- Yeni kurulumu eski sürümün üzerine rastgele dosya kopyalamak yerine yeni klasöre çıkarın.
- Yeni personel cihazı için Yönetici → Ayarlar → Bilgisayarlar → Personel kurulum paketi hazırla.
- **KUR_WINDOWS.bat** yalnızca geliştirme ortamında gerekir. Personel için build sürecinde PyInstaller Python'u exe içine paketler; personel bilgisayarına Python kurulmaz.
- **URET_SETUP_EXE_WINDOWS.bat** Windows bilgisayarında PyInstaller + Inno Setup ile gerçek Setup.exe derler. Vercel bir Windows derleme altyapısı değildir.

DİKKAT: Bu teslimde Windows EXE'nin derlemesi ve uygulama testleri yapılmadı. Bulut verileri sıfırlanmadı.
