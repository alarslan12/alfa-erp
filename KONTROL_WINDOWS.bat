@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Once KUR_WINDOWS.bat dosyasini calistirin.
 pause
 exit /b 1
)
set QT_QPA_PLATFORM=offscreen
".venv\Scripts\python.exe" -m compileall -q .
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m unittest discover -s tests -q
if errorlevel 1 goto failed
 echo.
 echo Kontroller tamamlandi.
 pause
 exit /b 0
:failed
 echo.
 echo Bir veya daha fazla kontrol basarisiz oldu. Hata ciktisini paylasin.
 pause
 exit /b 1
