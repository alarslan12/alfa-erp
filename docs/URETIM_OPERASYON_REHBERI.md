# ALFA ERP — Üretim Operasyon Rehberi

## Sistemin mimarisi

- Windows **Yönetici** ve **Personel** uygulamaları ortak Firebase Realtime Database alanına bağlanır.
- Mobil katalog Firebase Hosting üzerinden \`public_catalog\` okur; yeni sipariş talepleri \`checkout\` alanına yazılır. Yetkili Windows uygulaması isteği **mevcut Sipariş Havuzu** içine taşır.
- Uygulama kapalıyken bildirim servisi (Personel kurulumunda) kendi cihaz kimliğini kullanır. Windows'ta uygulamadan bağımsız çalışması ayrıca doğrulanmalıdır.
- Cihaz yetkileri Firebase Anonymous Authentication kimliği + \`members\` rolüyle korunur. Analitik PIN'i **yalnızca ekran kapısıdır**; gerçek güvenlik sınırı Firebase Rules ve cihaz rolüdür.
- GitHub: \`alarslan12/alfa-erp\`; geliştirme dalı \`firebase-rtdb-final\`. Kullanımdaki stabil Supabase 6.2.2 sürümünü üretim geçişi doğrulanana kadar sakla.

## Ücretsiz Spark planında dikkat edilecekler

| Servis | Resmî plan sınırı | Nereye bakmalı |
|---|---:|---|
| Firebase Realtime Database | 1 GB saklama | Firebase Console → Realtime Database → Usage |
| Firebase Realtime Database | Ayda 10 GB indirme | Aynı Usage ekranı |
| Firebase Realtime Database | 100 eşzamanlı bağlantı | Aynı Usage ekranı |
| Firebase Hosting | 10 GB saklama | Firebase Console → Hosting → Usage |
| Firebase Hosting | 360 MB/gün aktarım | Aynı Usage ekranı |
| GitHub Actions | Public repodaki standart runners ücretsiz | GitHub → Actions |
| GitHub Actions artifacts | Hesap planının depolama sınırına tabidir | GitHub → Settings → Billing & licensing |

**Önemli:** Firebase RTDB indirilen GB bilgisi yalnızca JSON boyutu değildir; ağ/protokol yükünü de kapsar. Yönetici uygulamasının yeni "Sistem sağlığı" ekranında gösterilen kitap, sipariş ve bekleyen işlem sayıları **kota tüketimi değildir**. Gerçek toplamlar resmî Firebase Usage üzerinden kontrol edilir.

**İzleme kuralı:** Haftada bir RTDB Storage, Downloads, Connections; Hosting data transfer; GitHub Actions son başarısız derlemeler. Sınırların %70'ine yaklaşırsa gereksiz verileri gözden geçir; %85'te operasyonel plan yap. Spark planında aşım kullanım kesintisine yol açabilir. Blaze'a geçilirse Google Cloud bütçe alarmları aç; bütçe alarmı kendi başına harcamaya kesin üst sınır koymaz.

Resmî bağlantılar:

- https://console.firebase.google.com/project/alfa-erp-8700c/database
- https://console.firebase.google.com/project/alfa-erp-8700c/hosting
- https://console.firebase.google.com/project/alfa-erp-8700c/usage
- https://github.com/alarslan12/alfa-erp/actions
- https://github.com/alarslan12/alfa-erp/releases
- https://firebase.google.com/pricing
- https://firebase.google.com/docs/database/usage/monitor-usage

## Düşük veri trafiği ilkeleri

1. Hazırlandı/kolilendi: tek siparişte art arda değişen tüm kitap satırları **tek koşullu Firebase yazmasıyla** güncellenir. Yeniden denemelerde \`op_id\` işlem geçmişi korunur.
2. İşlem günlüğü: güncellemenin kitap satırları, **tek audit grubu** içerisinde saklanır; ayrıntı gösterimi yerelde açılır, yeni ağ isteği oluşturmaz.
3. Yönetici işlem günlüğü yalnızca açılışta ve elle yenilendiğinde yüklenir; kısa süreli sekme değişimlerinde tekrar indirme yapılmaz.
4. Yönetici oturum işlemleri var olan \`Workstation\` örneğini paylaşır; her seferinde yeni cihaz oturumu açılmaz.
5. Sistem sağlığı ekranı kendiliğinden kota sorgusu yapmaz; mevcut uygulama senkronizasyon durumunu sunar.
6. Firebase veri indirme kotasını en çok artırabilecek etkenler: büyüyen \`orders/event_log\`, \`checkout\` taleplerinin uzun süre tutulması, çok sayıda açık tarayıcı/masaüstü bağlantısı. Gerçek ölçümleri takip ederek sonraki arşivleme politikasını planla.

## Üretime sıfır test verisiyle geçiş

**Bu adımı sadece yeni Yönetici/Personel sürümü aynı anda, iki bilgisayarda doğrulandıktan sonra uygula.**

- Her iki Windows uygulamasında **0 işlem sırada** olmalı.
- Uygulamaları kapat. Mobil sipariş gönderimini durdur.
- Google Cloud Shell projesi \`alfa-erp-8700c\` olarak seçilmiş olmalı.
- Kurulum deposundan yedek/ön kontrol (Firebase verisini **değiştirmez**):

\`\`\`bash
cd ~/alfa-erp
git pull --ff-only
python3 tools/rtdb_prepare_production.py
\`\`\`

- Oluşan \`~/alfa_erp_private_backups/*.json.gz\` dosyasını ayrı güvenli yere kopyala; GitHub'a yükleme.
- Doğrulanan yedek ve plan sonra, üretime geçişi özellikle istediğinde:

\`\`\`bash
python3 tools/rtdb_prepare_production.py --apply
\`\`\`

- Script terminalden \`ALFA-URETIM-VERISINI-SIFIRLA\` onayını almadan hiçbir şey silmez.
- Silinen deneysel veri: siparişler, mobil sepet istekleri, envanter, muhasebe, eski audit/arşiv, Analytics PIN ve eski cihaz istekleri.
- **Korunan:** 303 kitaplık katalog ve onaylı cihazlar (\`members\`). Firebase Authentication kullanıcıları silinmez.
- Eski epoch değiştiği için masaüstü uygulaması açılışta test kayıtlarını yerel arşive taşıyarak yeni boş veri alanını alır.
- Katalog ve personel yetkisi doğrulandıktan sonra Analitik PIN'i yeniden oluştur.

**Üretim geçişi Firebase'deki bütün test verilerini siler; test geçmişini tutmak istersen yedeği sakla. Doğrudan Google/Firebase konsolundan tek tek silme yapılmamalı.**

## Yayın kontrol listesi

- [ ] Mobil sipariş tek kopya, hem Yönetici hem Personel havuzunda görüldü.
- [ ] Hazırlandı/kolilendi toplu değişiklik diğer bilgisayarda tutarlı görüntülendi.
- [ ] Onaysız personel cihazı erişim sağlayamadı; onaylı cihaz başarılı bağlandı.
- [ ] Analitik PIN kilidi ve açılması çalıştı.
- [ ] İşlem günlüğü tek gruplu hareketleri gösterdi.
- [ ] Her uygulama kapatılıp açıldığında veri ve cihaz yetkisi korundu.
- [ ] Windows bildirim ve sesli uyarı; uygulama kapalıyken de kontrol edildi.
- [ ] Firebase Rules sürümü ve GitHub kodu eşleşti.
- [ ] Firebase özel yedeği alındı, yeni epoch'a güvenli geçildi.


## Mobil katalog için kalıcı yayın

Firebase Hosting'deki geçici önizleme linkleri **1 gün sonra sona erebilir**.
Üretim veritabanına güvenli geçiş ve iki uygulamada test tamamlandıktan sonra
aşağıdaki komutlar Cloud Shell'de kalıcı Hosting canlı kanalına yalnızca
HTML katalog dosyalarını yayımlar:

\`\`\`bash
cd ~/alfa-erp
git pull --ff-only
bash tools/firebase_mobile_production.sh
\`\`\`

Terminal onayı \`ALFA-MOBIL-YAYINLA\` yazılmadan canlı sitenin üzerine
yazılmaz. **Veritabanı, cihaz izinleri ve Firebase Security Rules değişmez.**
Canlı Hosting yayını projenin mevcut web sitesini değiştirebilir; sitede başka
içerik barındırılıyorsa önce ayrıca yedekle.



## Eski sistem ve Cloud Shell yedek güvenliği

- **Supabase eski V6.2.2:** Firebase'e geçiş tamamen doğrulanana kadar eski projeyi silme.
  Supabase Free: 500 MB veritabanı, aylık 5 GB egress; inaktif Free projeler
  yaklaşık 7 gün yetersiz etkinlikle duraklatılabilir. Aktif siparişlerle
  Firebase tarafı **eşzamanlı güncellenmez**. Üretim açıldıktan sonra ayrı
  CSV/SQL arşivi tutup eski projeyi bilinçli olarak sonlandır.
  https://supabase.com/docs/guides/platform/billing-on-supabase
- **Google Cloud Shell:** Ücretsiz 5 GB kalıcı HOME alanı vardır, ancak
  Cloud Shell'e 120 gün erişilmezse HOME temizlenebilir. Özel Firebase
  yedeğinin TEK kopyasını orada bırakma; yerel şifreli diske indir.
  https://docs.cloud.google.com/shell/docs/how-cloud-shell-works
- **Firebase Security Rules:** Uygulamadaki kimlik kontrolü çözülebilmiş
  olsa da kuralları değiştirmeden önce Rules kaynak dosyasını yedekle;
  \`audit\` erişimi owner-only kalır.
- **Kod/GitHub güvenliği:** Admin SDK anahtarı, servis hesabı JSON'u,
  Firebase veritabanı dökümü veya Cloud Shell \`*.json.gz\` yedeği kesinlikle
  halka açık GitHub deposuna yüklenmemeli. Firebase istemci apiKey'i
  güvenlik sınırı değil, RTDB Rules güvenlik sınırıdır.
- **Sürüm politikası:** Release Candidate (RC) canlı işletmede nihai sürüm
  sayılmaz. Üretim temizliği ve ikili cihaz kontrolü bittikten sonra tek
  stabil etiket ve iki Setup EXE yayımlanır. Eski installer paketlerini
  sürüm etiketi olmadan karıştırma.
