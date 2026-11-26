# ALFACOPYCENTER Suite v2.1.0 — ERP Yönetici / Personel yenilemesi

> Sürüm adayı: Bu dosyanın oluşturulması Windows Setup yayımlandığı anlamına gelmez. PR #36, merkezi release kalite kapıları, gerçek ses dosyaları ve yayın asset'leri ayrı doğrulanır.

## ERP özellikleri
- Hata Merkezi: arama, durum filtresi, çoklu seçim, toplu inceleme ve silme, incelenmiş kayıtları temizleme, hata kodu/aşaması ve açıklamalı detaylar. Yerel arşivlenmiş bulut çakışmaları bu merkezdedir. Yeni raporlar yalnız izinli işlem türü ve teknik kod taşır; sipariş içeriği göndermez.
- Bağlı bilgisayarlar: UID, kayıt tarihi, varsa son bağlantı, mevcut cihaz göstergesi, cihaz adı arama/düzenleme. Pasif diğer cihazların silinmesi ETag korumalıdır. Owner doğrulaması zorunlu; aktif cihazları toplu temizleme yoktur. Mevcut owner cihazı personel onayıyla ezilmez.
- İşlem günlüğü: tarih ve saat, 120 saniyelik aynı sipariş/cihaz/aktivite grupları, aktivite/arama filtreleri, okunabilir temaya uygun vurgular. Sistem sağlığı sayfası kaldırıldı.
- Uygulama Ayarları: PDF klasörü sol, Excel katalog sağ, görünüm/kontrast aynı sekmede. Bildirimler/Güncelleme ayrı sekme; üst sağda cihaz kalkanı ve ayarlar.
- Derleme yalnız Yönetici (Personel derleme modülü hariç); ZIP içindeki sipariş notu korunur. Geçmiş checkout note recovery çıkarıldı; yeni mobil sipariş notları korunur.
- Bulut çakışması bildirimi 14 saniye; arşivler silinmez. Sayaç/revision ETag yarışları geçici hata olarak kuyrukta kalır.

## Yerel ses sistemi
ElevenLabs API, key/voice ayarları ve ağ sentezi kaldırıldı. Dört yerel sabit Türkçe anons için paketleme ve oynatma yolu hazırdır. **Canva Ozan WAV dosyaları bu adayda mevcut değildir.** Bkz. assets/notifications/README.md. Dosya yoksa yüklü Türkçe Windows sesi, o da yoksa yerel uyarı tonu kullanılır. Gerçek Canva çıktısı olmadan Ozan sesi olarak tanıtılmaz.

## Yetki, kapsam ve yayın durumu
- Repo Firebase Rules yalnız aktif owner'a rapor silme hakkı tanır; pasif cihaz silme koşulu daraltılmıştır. **Canlı Firebase Rules veya Hosting değiştirilmemiştir.** Canlı 403/owner üyeliği ayrıca doğrulanmalıdır.
- Kaynak ERP entegrasyon PR #36; diğer Suite bileşenlerine işlevsel değişiklik yok. Canlı Firebase siparişleri, kullanıcı arşivleri, cihaz kimlikleri ve geçmiş korunur.
- Dalların envanteri ve hedefli statik inceleme yapıldı. Elle GitHub test ya da Windows build başlatılmadı; PR'ın otomatik kalite kontrolü ayrı tutulur.
- Hedef ortak kurulum adı: `ALFACOPYCENTER_Suite_Setup_V2_1_0.exe`. Bu sürüm yalnız merkezi release PR birleştirilip gerçek Windows Release asset'i ve SHA-256 doğrulanınca yayımlanmış sayılır.
