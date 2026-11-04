# ALFA ERP v4.18 — Windows kurulumu

1. `ALFA_ERP_DESKTOP_QT` klasörünü çıkar.
2. Python 3.13 (64-bit) kurulu değilse python.org üzerinden kur.
3. `KUR_WINDOWS.bat` dosyasını aç. Bu işlem yalnızca sanal ortamı ve kütüphaneleri kurar; test çalıştırmaz.
4. `BASLAT_WINDOWS.bat` dosyasını aç.

Komut satırı alternatifi (CMD):

```bat
cd /d C:\ALFA_ERP_DESKTOP_QT
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Mevcut siparişler `%LOCALAPPDATA%\AlfaERP` altında tutulur. Tam proje ZIP'inde kullanıcı verileri yoktur. Eski proje klasörünü değiştirmeden önce yedekle.
