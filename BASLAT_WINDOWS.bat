@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Ilk once KUR_WINDOWS.bat dosyasini bir kez calistirin.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" KONTROL_DOSYA_UYUMU.py
if errorlevel 1 (
 echo.
 echo Eski ve yeni surum dosyalari karismis. Bos bir klasore tam proje cikariniz.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
 echo.
 echo Uygulama hata ile kapandi. Mesaji kopyalayip paylasin.
 pause
)
