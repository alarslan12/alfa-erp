# ALFA ERP Firebase Web App kaydı

**Firebase Project ID:** `alfa-erp-8700c`

Kullanıcının bildirdiği durum: Firestore oluşturuldu, **Anonymous** ve
**Google** Authentication sağlayıcıları açıldı. Bu adımlar konsoldan bağımsız
olarak henüz doğrulanmadı.

## Sıradaki gerekli tek adım: Web app yapılandırması

1. Firebase Console → **Project settings** → **General** → **Your apps**.
2. Web simgesi **</> / Add app** → takma ad: `ALFA ERP Katalog`.
3. Firebase Hosting'i şimdilik işaretleme; daha sonra ayrıca karar verilebilir.
4. **Register app** → **SDK setup and configuration / Config** seç.
5. Görünen `firebaseConfig` nesnesindeki **apiKey, authDomain, projectId,
   appId, messagingSenderId** bilgilerini al. `storageBucket` alanı varsa
   onu da al.
6. **Özel anahtar, Admin SDK JSON, service-account credential, erişim tokeni
   veya kişisel parola gönderme.** Bunlar istemci yapılandırması değildir.

Firebase Web API key tek başına veri yetkisi sağlamaz; Firestore güvenlik
kuralları ve Firebase Auth gerekli erişim sınırlarını uygular.

## Örnek istemci yapılandırması (gerçek değerler bekleniyor)

```js
const firebaseConfig = {
  apiKey: "FIREBASE_WEB_API_KEY",
  authDomain: "alfa-erp-8700c.firebaseapp.com",
  projectId: "alfa-erp-8700c",
  storageBucket: "FROM_FIREBASE_CONSOLE",
  messagingSenderId: "FROM_FIREBASE_CONSOLE",
  appId: "FROM_FIREBASE_CONSOLE"
};
```

**Buradaki örnek doğrudan çalışmaz.** Konsoldaki gerçek istemci tanımlayıcıları
alındıktan sonra mobil katalog kodunun ayrı Firebase geliştirme dalı üzerinde
uyarlanması gerekecek. Firestore Rules yayınlanmadı; ticari veriler henüz
aktarılmadı. Canlı Supabase ve V6.2.2 kurulumları değişmedi.
