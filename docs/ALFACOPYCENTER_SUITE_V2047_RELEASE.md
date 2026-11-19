# ALFACOPYCENTER Suite v2.0.47 — Banner Studio tasarım arşivi güncellemesi

## Tasarım arşivinde tekrar kaydetme
- “Tasarım Arşivi → Düzenle” ile açılan tasarımların kayıt kimliği korunur.
- “Değişiklikleri Kaydet” mevcut tasarımın üzerine güncelleme yapar; arşivde ikinci banner oluşturmaz.
- “Farklı Kaydet” ile isteğe bağlı olarak ayrı bir arşiv kaydı oluşturulabilir.
- Aynı adla kayıt oluşacaksa mevcut tasarımın üzerine yazmak için kullanıcıdan onay alınır.
- PNG ve JPG afiş indirmelerinde düzenlenen tasarım mevcut arşiv kaydını günceller; kare kırpma önizlemesi orijinal arşiv görüntüsünü bozmaz.
- Otomatik çalışma taslağı düzenlenmekte olan tasarımın kimliğini korur; eski arşiv kayıtları silinmez.

## Türkiye saat dilimi
- Tasarım Arşivi zaman damgaları UTC saklanmaya devam eder. Kullanıcıya gösterilen saatler **Europe/Istanbul (UTC+3)** olarak Türkçe biçimde dönüştürülür.
- Eski kayıtların tarihlerini geriye dönük değiştirmeye, yerel arşivi taşımaya veya sıfırlamaya gerek yoktur.

## Dağıtım
- Bu düzeltmeler v2.0.46 GitHub kurulum yayınından sonra kaynak koda eklendiği için v2.0.47 Suite Setup ile ilk kez Windows kurulumuna girer.
- Dört uygulama tek Suite paketi altında kalır. ERP Personel, ERP Yönetici ve Print Surveillance işlevleri bu güncellemede değiştirilmez.
- Mevcut yerel Banner Studio arşivi/kapakları, Excel seçimi, Suite AppId ve Firebase verileri korunur.

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_47.exe`.
