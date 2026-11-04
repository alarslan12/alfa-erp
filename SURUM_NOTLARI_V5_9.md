# ALFA ERP V5.9 — Sipariş numarası ve ana Envanter sekmesi

- Supabase numaratöründeki `order number not authorized` hatası sunucuda düzeltildi. Yetkili cihazdan gelen yeni sipariş, kullanıcı `auth.uid()` bilgisi taşımadığı için reddedilmeyecek. Bu düzeltme mevcut masaüstü sürümlerinde de geçerlidir.
- `Envanter`, artık masaüstündeki **dördüncü ana sekmedir**; yönetim menüsündeki envanter yer tutucusu kaldırıldı.
- Envanter henüz yalnızca hazırlık ekranıdır: mevcut katalog kitap sayısı ve gelecekteki malzeme stok takibi alanları gösterilir; sahte stok miktarı yaratılmaz.
- Katalog, Siparişler, Analitik ve yönetim yetkileri aynen korunur. Analitik personel sürümünde önceki parolayla korunmaya devam eder.
- Personel için Windows Setup.exe oluşturucu dosya adları V5.9'a taşındı; personel bilgisayarında Python gerekmez (Setup.exe Windows'ta yönetici tarafından üretilir).
- Siparişler sunucu tarafında #1'den başlamaya devam eder; eski siparişler otomatik geri aktarılmaz.

Bu bir kaynak güncellemesidir. Kullanıcının önceki tercihine göre uygulama/Windows testleri çalıştırılmadı.
