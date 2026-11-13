# ALFACOPYCENTER Suite v2.0.14 — Yönetici kurulum koruması

- ALFA ERP Suite Setup'ta **Yönetici** bileşeni seçilince yerel kurulum şifresi istenir.
- Hatalı şifre ile Yönetici bileşeni kurulamaz; kurulum başlamadan kontrol tekrar yapılır.
- Sessiz kurulum parametreleri şifre kontrolünü atlayamaz.
- Personel, Banner Studio ve Print Center tek başına kurulurken şifre sorulmaz.
- Yerel şifre Firebase owner yetkisi değildir: Yönetici UID Cloud Shell üzerinden ayrıca doğrulanır.
- GitHub'da yalnız rastgele tuzlanmış SHA-256 doğrulama özeti tutulur; açık şifre kaynak kodda yoktur.
- Dört bileşenli Suite ve ortak Güncelleme Merkezi korunur.
- Mevcut Firebase oturumları, sipariş kuyruğu, afiş arşivi ve yazdırma geçmişi silinmez.

Not: İstemcinin kurulum şifresi tek başına güçlü bir sistem yetkilendirmesi değildir;
gerçek yönetim erişimini Firebase Auth + RTDB Security Rules belirler.
