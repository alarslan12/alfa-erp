# ALFACOPYCENTER Suite v2.0.2 · Banner Studio v3.4 + Kargonomi

Geliştirme dalı: `feature/banner-kargonomi-20261110` (v2.0.1 birleşik kurulumunu temel alır). Ana dal değiştirilmemiştir.

## Kurulum / bir defalık Kargonomi yetkilendirmesi

1. GitHub Actions > **ALFACOPYCENTER Suite v2.0.2 Windows candidate (build only)** başarılı işin **Artifacts** alanından `ALFACOPYCENTER_Suite_v2.0.2_Windows_Candidate` ZIP'ini indir.
2. Mevcut `%LOCALAPPDATA%\AlfaERP` verilerini yedekle. İndirilen ZIP'i açıp `ALFACOPYCENTER_Suite_Setup_V2_0_2.exe` dosyasını çalıştır. Kurulumda mevcut uygulamalar aynı AppId ile güncellenir; yönetici bileşeni seçildiyse onun kurulum parolası gerekebilir.
3. Kargonomi panelinden işletme hesabının **API Bearer Token** değerini ve **gönderici depo ID** bilgisini temin et. Üretimde API'ye yetkin ve kargo kredin olmalı.
4. ERP'yi aç; sağ üstte **Kargonomi** > API anahtarını ve depo ID'yi bir kez gir > **Bağlantıyı Windows kimlik kasasında sakla**. Anahtar kaynak koduna, herkese açık GitHub'a, Firebase'e veya düz metin ayar dosyasına yazılmaz. Farklı Windows kullanıcıları / PC'lerde bu adım ayrı yapılır.
5. Yeni sipariş için katalogdan kitapları seç, kargo kodu ve **satış fiyatı** gir, kayda bas. Açılan pencerede **ad soyad, cep telefonu, açık adres, il ve ilçe** doldur.
6. Gardrops kodu otomatik algılanıyorsa **net ciro = yukarı yuvarla(girilen fiyat × %90)** uygulanır. Örnek: 555 TL → 500 TL. Diğer platformların tutarı aynen kalır.
7. Sipariş aktifte tamamen hazırlandı ve kolilendiğinde **Tamamlandı** seç. Uygulama desiyi sorar. **Kargo tekliflerini getir** ile taslak açar, il/ilçe ID'lerini Kargonomi'den bulur ve teklifleri sunar. Otomatik en uygun teklif ön seçilidir; farklı firmayı da seçebilirsin.
8. **Yeni Barkod** düğmesine basıp ücret doğurabilecek gönderi/firma onayını kabul et. PDF **KargonomiBarcodes** klasörüne kaydedilip açıldıktan sonra ERP siparişi tamamlanır. PDF başarısızsa ERP'de otomatik tamamlanmaz.
9. Tamamlanan siparişin detayında **Yeni Barkod · PDF yeniden al** düğmesi vardır. ERP üst menüsündeki Kargonomi ekranından gönderi detayını, fiyatları, bakiyeyi görebilir ve iptal talebinde bulunabilirsin.

## İş kuralları ve güvenlik

- Tek bir ERP siparişinin Kargonomi gönderi ID'si saklanır; daha sonraki denemede aynı taslağa devam edilir. Ağda onaysız hata olursa gerçek gönderi var mı Kargonomi panelinden kontrol etmeden ikinci kez taslak oluşturma.
- Alıcı bilgileri ve gönderi kimliği, mevcut Firebase sipariş oluşturma/tamamlama senkronizasyon mesajlarıyla taşınır; eski bulut anlık görüntüleri yerel gönderi bilgilerini düşürmez.
- Her platform siparişine **ayrı Kargonomi etiketi** açmadan önce, satış platformunun zaten ücretli/aktif bir taşıma etiketi oluşturmadığını kontrol et. Çift kargo ödemesi doğabilir.
- İkinci cihazdan aynı siparişte eşzamanlı barkod oluşturulması konusunda sunucu tarafı dağıtık kilit henüz yoktur; gönderi kesimi tek yetkili cihazdan yapılmalıdır.
- Kargonomi gönderi güncellemeleri ERP içinde otomatik webhook ile izlenmez. Gönderi detayı Kargonomi penceresinden sorgulanır.
- **Canlı API tokenı olmadan gerçek gönderi, fiyat ve barkod uçtan uca doğrulanmamıştır.** Windows GUI testleri özellikle çalıştırılmamıştır; Actions iş akışı yalnızca kurulum paketi üretir.
- Kargonomi API resmi referansı: https://www.kargonomi.com.tr/help/api-dokumantasyonu/kargonomi-api/
