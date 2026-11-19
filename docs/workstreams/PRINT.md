# ALFA Print Surveillance — Çalışma durumu

**Sohbet:** Print Surveillance. **Repo:** `alarslan12/alfa-erp`, üretim `firebase-rtdb-final`.

**Başlangıç referansı:** Suite v2.0.46 (20.11.2026); GitHub release'i yeniden doğrula.

**Sahiplik:** `alfa_print_*.py`, `alfa_print_standalone.py`, `ekran_yazdirma.py`, `ekran_baski_plani.py`, `tools/test_print_contract.py`, ilgili testler.

**Korunacaklar:** Windows spool izleme, IPP/SNMP, operatör fiziksel çıktı teyidi, SQLite `%LOCALAPPDATA%\AlfaERP\print_monitor`, user-session PrintAgent/PrintSupervisor, yazıcıya kontrolsüz komut ve spool reseti vermeme.

**Fiziksel üretim referansı:** 3×45 SB sayfa/dk, 2×15 RNK + 1×7,5 yavaş RNK sayfa/dk. Bunlar teorik kapasite; fiziksel yazdırma tamamlandı teyidi değildir.

**Aktif PR:** Başlangıçta yok; GitHub üzerinden tekrar kontrol et.

**Sıradaki iş / bağımlılık:** Kullanıcı talepleri. Ortak Suite sürüm dosyalarına dokunma.

Bu durum kaydını **yalnız Print sohbeti** kendi PR'larında yeniler.
