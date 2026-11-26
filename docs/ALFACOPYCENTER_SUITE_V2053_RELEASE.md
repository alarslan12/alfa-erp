# ALFACOPYCENTER Suite v2.0.53 — Mobil Sipariş Notları ve Güvenli Kurtarma

## ERP Personel / Yönetici
- Son kurulum v2.0.52, üretim dalına birleştirilmiş PR #30 checkout not aktarımını içermiyordu. Bu kurulumda yeni mobil checkout'un `order_note` alanı (maksimum 2000 karakter) doğrudan mevcut havuz siparişinin `order_note` alanına alınır; `siparis_uyari.make_notice(None, order)` ile okunmamış `initial_note` uyarısı oluşur.
- Issue #32 / PR #34: Daha önce notsuz aktarılmış mevcut siparişlerde **checkout kaynak talebinde hâlâ not varsa**, UUIDv5 sipariş anahtarı, müşteri isteği kimliği ve workspace doğrulanarak koşullu RTDB ETag yazması ile not ve yeni uyarı onarılır.
- Güvenli onarım yalnız silinmemiş, notu ve uyarı anahtarı **hiç bulunmayan** siparişe uygulanır. Mevcut / sonradan düzenlenen notlar, okunmuş veya okunmamış uyarılar, sipariş numarası, satırları, durumu, üretim/koli değerleri, finans ve geçmiş korunur. Kopya sipariş açılmaz. Aynı onarım tekrar çalışınca değişiklik yapılmaz.
- Kaynak checkout'ta `order_note` artık yoksa not **uydurulmaz ve geri getirilemez**. Canlı geçmiş kaynaklar bu sürüm sürecinde erişilerek incelenmedi; onarılan gerçek sipariş sayısı doğrulanmadı.
- PR #31: `Siparişi Derle` ile oluşan ZIP'in `BASKI_TALIMATI.txt` dosyası, önceki üç satırlık özetin sonuna sipariş notu varsa `Sipariş Notu:` başlığı ve çok satırlı not ekler.
- PR #33 mobil katalog kodu üretim dalında birleştirilmiştir. **Canlı Firebase Rules veya Hosting bu Windows sürümünde yayımlanmaz.**

## Tek Windows Suite kurulum
- Personel ve Yönetici, Banner Studio Pro, Print Surveillance ve yardımcı bileşenler **tek v2.0.53 Setup** içindedir. Uygulamaların iş verileri, %LOCALAPPDATA% arşivleri, Firebase siparişleri, Firebase Rules ve Hosting dağıtımı değiştirilmez.
- Eski bir workstation yeni checkout'u ilk görürse notsuz sipariş oluşturabilir. Bu yüzden eşitleme yapan tüm Personel/Yönetici PC'lerinin v2.0.53'e yükseltilmesi gerekir.
- CI Windows kapsam/regresyon, offline Firebase kontrat, EXE açılış testleri, ortak Setup ve SHA-256 doğrulamaları yayın işinde gerçekleştirilir. Gerçek Firebase yetki testi ve canlı iki-PC senaryosu CI içinde değildir.

## Bağlantılar
- Issue #32: https://github.com/alarslan12/alfa-erp/issues/32
- ERP onarım PR #34: https://github.com/alarslan12/alfa-erp/pull/34
- Mobil PR #33: https://github.com/alarslan12/alfa-erp/pull/33
- Not aktarımı PR #30: https://github.com/alarslan12/alfa-erp/pull/30
- ZIP talimat notu PR #31: https://github.com/alarslan12/alfa-erp/pull/31

Kurulum: `ALFACOPYCENTER_Suite_Setup_V2_0_53.exe`.
