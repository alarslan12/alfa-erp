@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0kurulum_personel.ps1"
if errorlevel 1 (
 echo.
 echo Kurulum tamamlanamadi. Hata mesajini yoneticiye iletin.
 pause
 exit /b 1
)
echo.
echo ALFA ERP kuruldu; masaustu kisayolu hazir.
pause
