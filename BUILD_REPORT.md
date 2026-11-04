# ALFA ERP V6.1.2 – test / dağıtım raporu

**Kaynak:** ALFA ERP V6.1.1 düzeltilmiş tam proje, yalnızca Windows derleme ve sürüm dağıtım iyileştirmeleriyle düzenlendi.

## Bu oturumda gerçekten çalıştırılan doğrulamalar

- `python KONTROL_DOSYA_UYUMU.py`: BAŞARILI (eski `ekran_bulut.py` zorunlu değil).
- `python -m unittest discover -s tests -v`: **14 testtan 12 BAŞARILI, 2 ATLAnDI**. 2 atlanan Windows PySide6 GUI testidir (buradaki ortam Windows değil).
- AST/Python sözdizimi ve kaynak sözleşmesi: BAŞARILI.
- Yerel sipariş oluşturma, hazırlama-kolileme ve tamamlamanın dosyada saklanması: BAŞARILI.
- Çevrimdışı işlemlerin kalıcı kuyruğa eklenmesi, durum/ilerleme sırası, yeniden açılışta korunması: BAŞARILI.
- 409 çakışmasının bağlantı kopması sayılmaması, kuyruktan izole edilmesi: BAŞARILI.
- Mevcut personel Setup.exe ile yeni bilgisayar kodu birleştiren ZIP oluşturucu: BAŞARILI.
- GitHub Actions YAML sözdizimi yerel ayrıştırıcıyla kontrol edildi.

## Henüz yapılamayan / bloke aşamalar

- `alarslan12` GitHub bağlantısı mevcut fakat **erişilebilir repo yok**. Hiçbir dosya GitHub'a yüklenmedi. GitHub Actions başlatılmadı.
- Burada Windows çalıştırıcısı, PySide6 veya Inno Setup yok; gerçek Windows Qt GUI, PyInstaller EXE ve Setup.exe testleri **henüz yapılmadı**.
- CI workflow, özel GitHub deposuna yüklendiğinde **Windows 2022** üzerinde hem uygulamanın kaynaktan GUI testlerini hem de derlenmiş iki EXE'nin `--self-test` açılışını yapacak.
- Üretimdeki Supabase bağlantısı, iki bilgisayarın karşılıklı gerçek ağ gecikmesi veya Windows bildirim servisi test edilmedi; bunlar için bağımsız test çalışma alanı ve gerçek Windows ortamı gerekir.

## Sonraki tek GitHub hazırlığı

`https://github.com/new?name=alfa-erp&private=true` üzerinden **Private** depo oluşturulmalı. O andan itibaren GitHub bağlantısının erişimiyle dosyalar yüklenip Windows test/derleme çalıştırılabilir. Hiçbir personel eşleştirme anahtarı kaynak deposunda veya CI sırrı olarak tutulmamalıdır.

## Sürüm dağıtımı ve yeniden derleme sıklığı

- `main` kod değişikliklerinde yalnızca Windows testleri çalışır; **EXE her commit'te yeniden üretilmez**.
- `v6.1.2` gibi sürüm etiketi veya manuel Actions çağrısı, 2 Windows Setup.exe üretir.
- Yayınlanmış sürüm etiketinde derleme başarılı olursa özel GitHub Release'e kaydedilir.
- Personel için tek genel EXE, yeni PC için ayrı tek kullanımlık kod dosyası; her PC için yeni EXE derleme ihtiyacı kalkar.
- Inno Setup AppId korunur: yeni EXE var olan kurulumu günceller, Windows kullanıcı verileri ise `%LOCALAPPDATA%\\AlfaERP` içinde kalır.
