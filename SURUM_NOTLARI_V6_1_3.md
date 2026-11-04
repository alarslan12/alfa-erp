# ALFA ERP V6.1.3 — Performans ve Senkronizasyon

Bu sürümün amacı, kullanıcı deneyimini koruyarak Supabase CPU kullanımına ve gereksiz veri trafiğine neden olan sorguları azaltmaktır.

## Değişiklikler
- Tek istekte cihaz yetkisi doğrulama, değişiklik numarası kontrolü ve gerektiğinde sadece değişen veri gruplarını indirme.
- Hazırlama / kolileme sırasında değişmeyen kitap kataloğu ve ürün envanteri yeniden indirilmez.
- Hareketli kullanımda yaklaşık 2 saniye, boşta yaklaşık 5,5-6,5 saniyelik adaptif kontrol.
- Yaklaşık 0,85 saniyelik güvenli arka plan işlem toplulaştırması.
- Windows bildirim servisi artık tam siparişleri değil, yeni sipariş numaralarını sorgular.
- Muhasebe güncellemeleri değişiklik sayacını yükselterek diğer cihazlara yansır.
- Üç sorgu yolu için veritabanı indeksleri; cihaz çevrimiçi zamanının 4 dakika aralıkla güncellenmesi.
- Eski bulut API yöntemleri geriye uyumlu tutulmuştur.
- Sipariş, ürün, finans, cihaz eşleştirmesi ve yerel bekleyen işlemler silinmemiştir.

## Testler ve Yayın
Windows çevrimdışı sipariş/kuyruk, Qt GUI, yeni senkronizasyon protokolü ve EXE açılış testleri. Bulut yetkilendirmesi tanınmayan, geçici yetkili ve iptal edilmiş cihazlar için veri saklamadan SQL transaction testleriyle denetlenmiştir.

Normal kaynak güncellemeleri yalnızca Windows testlerini tetikler. Setup.exe derleme ve kalıcı GitHub Release yayını, açık release işaretiyle yapılır.

Yeni optimizasyonların masaüstü bilgisayarlarda geçerli olması için V6.1.3 kurulumu gereklidir; eski sürümlerin bulut bağlantıları bir anda kesilmez.

Not: WebSocket yerine birkaç saniyelik adaptif kontrol kullanılır. Gerçek CPU değişimi ancak güncellenmiş istemcilerle ölçülebilir. İş kurallarından kaynaklı gerçek 409 çakışmaları sıfırlanmış değildir.
