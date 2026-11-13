# ALFACOPYCENTER Suite v2.0.17 — Firebase katalog ve sayfa düzeltmesi

- Excel kitap kodları doğrudan ISBN/dahili kitap anahtarı olarak eşleştirilir; liste sırası kullanılmaz.
- TIPDEMY 346/508/509/510 yanlış eşleştirmeleri güncel Excel dosyasından düzeltilebilir.
- Yükleme öncesi mevcut Firebase kitapları ve mobil katalog yerel JSON yedeğine kaydedilir.
- Aktarım sonrasında aktif kitaplar ve mobil katalog sunucudan geri okunarak tek tek doğrulanır; bu doğrulama olmadan katalog revizyonu yükseltilmez.
- Masaüstünden girilen yeni siparişlerin kitap isimleri ve gerçek sayfa sayıları Firebase anlık görüntülerinde saklanır.
- Önceki sürümlerde 0 sayfalı yazılmış siparişlerde, bilinen doğru katalog sayfa sayısı gösterilir; sıfır değerli eski kayıtların silinmesi veya siparişlerin yeniden yazılması gerekmez.
- Başarılı katalog aktarımı sonrasında Personel, Yönetici, sipariş toplamları ve mobil sipariş eşleştirme önbelleği yenilenir.
- Cloud Shell için yalnızca okuyan önizleme ve açık kullanıcı onayıyla veri düzelten kurtarma aracı eklendi.
- v2.0.16 Analitik PIN/Qt iş parçacığı düzeltmeleri, dört bileşenli Suite, Güncelleme Merkezi ve Yönetici kurulum şifresi korunur.
- Mevcut sipariş, çevrimdışı kuyruk, cihaz kimliği, kapak arşivi ve yazdırma geçmişi silinmez.

**Önemli:** GitHub sürümünü yüklemek, canlı Firebase kitaplarını kendiliğinden güncellemez. Önce doğru Excel'i Yönetici uygulamasından Firebase'e yeniden yükleyin. İzin hatası olursa proje yöneticisi Cloud Shell kurtarma aracını kullanabilir.

**Geçmiş sipariş notu:** Daha önce kodu yanlış görünen siparişleri yazdırmadan önce gerçek müşteri siparişindeki kitap adını kontrol edin. Doğru kod haritası geçmişteki yanlış isimle yapılmış fiziksel seçimi otomatik açıklamaz.
