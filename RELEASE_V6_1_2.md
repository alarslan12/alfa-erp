# ALFA ERP 6.1.2 – Windows release hazırlığı

- **Düzeltilmiş V6.1.1 kod tabanı** kaynak olarak alınmıştır; Katalog ve Siparişler görünümü değiştirilmemiştir.
- Windows kaynak sözleşmesi ve 38+ Python dosyası sözdizimi kontrolleri.
- Çevrimdışı sipariş döngüsü, yeniden başlatma sonrası kuyruk, 409 çakışmasının ağ kopması sayılmaması, karantinaya alma regresyon testleri.
- Windows `QT_QPA_PLATFORM=offscreen` uygulama ve 5 ana ekran açılış smoke testi; PyInstaller ile derlenmiş iki EXE için `--self-test` modu.
- GitHub Actions `main` push'unda yalnızca test; sürüm etiketi veya manuel çağrıda gerçek 2 Setup.exe.
- Personel installer'ı genel yapılmıştır: ilk PC eşleştirmesi aynı dizindeki tek kullanımlık `kurulum_bilgisi.json` ile yapılır; yeni PC için EXE yeniden derlenmez.
- Yönetici > Bilgisayarlar bölümünde hazır Setup.exe + tek kullanımlık kodu tek ZIP olarak çıkarma.

**Dikkat:** Private GitHub deposuna yüklenmeden GitHub Actions koşamaz; Windows testleri ve derlemeler gerçekleşmiş sayılmaz. CI testleri gerçek Supabase veya Windows bildirim teslimini sınamaz. 6.1.2 bir release candidate paketidir.
