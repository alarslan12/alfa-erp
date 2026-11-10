# ALFACOPYCENTER Suite — Banner Studio & Kargonomi geliştirme dalı

Kaynak: `v2.0.1` birleşik kurulum etiketi. **Ana dal değiştirilmedi, yeni Setup.exe derlenmedi.**

## Banner Studio
- Kapak Yerleşimi altındaki TTS'ye sabit üç düğme kaldırıldı.
- Excel kataloğundan dinamik gelen tüm gruplar açılır/kaydırılabilir listeden seçiliyor; tek tıkla o grubun kapakları ekleniyor (30 sınırı korunuyor).
- Bağımsız `subtitle` metin alanı ve `show_subtitle` anahtarı eklendi. Gösterilmediğinde eski kitap sayısı etiketi korunur.
- Marka sekmesindeki logo yükleme/konumlandırma kaldırıldı; kayıtlı eski logolar afişte artık çizilmiyor.
- Alt marka bloğunda mağaza adı, hesap adı, yeni nötr marka mesajı ve kısa spot ayrı satırlarda tutuluyor.
- Önceki proje JSON dosyaları açılabilir; eski logo ayarları yalnızca eski kayıtlarla geriye dönük veri uyumu için ayar modelinde kaldı.

## Kargonomi
- ERP üst çubuğunda **Kargonomi** düğmesi ve ayrı yönetim penceresi.
- Resmi `https://app.kargonomi.com.tr/api/v1` API; Bearer kimlik doğrulaması.
- Gönderi listeleme, sipariş seçerek taslak oluşturma, gönderi detayı, fiyat karşılaştırma, firma onayı ve barkod PDF alma.
- Kullanıcı, ERP siparişinden gelen bilgileri kontrol ederek eksikleri tamamlar. ERP'deki `kod` alanı kargo kodu veya adres olabildiğinden, alıcı adresine **otomatik taşınmaz**.
- Depo/şehir/ilçe için Kargonomi panelindeki sayısal ID'ler kullanılır.
- Token git deposuna ve yerel ayar JSON'una yazılmaz; çevre değişkeni `KARGONOMI_API_TOKEN` veya penceredeki oturumluk şifreli giriş kullanılabilir.
- Gönderi oluşturma ve firma onayı kullanıcıya ayrıca sorulur. İstekler arka plan iş parçacığında 18 saniyelik ağ zaman aşımıyla çalışır.
- **Sınır:** Bu ilk entegrasyon sürümü, Kargonomi gönderi ID'sini ERP/Firebase siparişine kalıcı şekilde eşleştirmez; durum webhook'u ve otomatik kargo ücreti muhasebeleştirmesi de henüz bağlı değildir. Canlı tokenla gerçek API çağrısı yapılmadı.

## Üretim öncesi
1. Kargonomi hesabından kişisel API token ve depo ID temin edin.
2. Test/küçük hacimli gönderide il/ilçe ID, gönderi oluşturma, fiyat ve barkod yanıtlarını doğrulayın.
3. Birleştirilmiş setup, bu dal üzerinden Windows'ta yeniden derlenmelidir. Eski v2.0.1 EXE dosyası kendiliğinden güncellenmez.
4. Uçtan uca Windows GUI testi ve canlı Kargonomi işlemi **yapılmadı**.

Resmi referans: https://www.kargonomi.com.tr/help/api-dokumantasyonu/kargonomi-api/
