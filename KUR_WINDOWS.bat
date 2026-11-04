@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ALFA ERP Desktop - Kurulum
echo.
where py >nul 2>&1
if errorlevel 1 (
 echo Python Launcher bulunamadi. Python 3.13 x64 kurun.
 pause
 exit /b 1
)
py -3.13 --version >nul 2>&1
if errorlevel 1 (
 echo Python 3.13 bulunamadi. Python 3.13 x64 kurun.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 py -3.13 -m venv .venv
 if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Kurulum tamamlandi. BASLAT_WINDOWS.bat dosyasini acabilirsiniz.
pause
exit /b 0
:failed
echo Kurulum hata verdi. Yukaridaki mesaji paylasin.
pause
exit /b 1
