# ALFA ERP V6.1.1 — Kaynak dosyası uyumluluğu

- Önceki V6.1 kontrolünde emekliye ayrılmış `ekran_bulut.py` dosyası zorunlu tutulmuştu.
- Dosya listesi mevcut mimariye göre düzeltildi. `ekran_bulut.py` gerekmez.
- Yönetici ZIP: `ALFA_ERP_DESKTOP_QT` klasörü altındaki `BASLAT_WINDOWS.bat` ile çalışır.
- Veri dizini ve Supabase bağlantısı değiştirilmedi; mevcut işlemler etkilenmez.
- Windows `Setup.exe` GitHub Actions Windows runner üzerinde derlenebilir.
- Bu pakette test çalıştırılmadı ve EXE derlenmedi.
