@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0ALFA_BUILD_WINDOWS.ps1" yonetici
if errorlevel 1 (
 echo.
 echo Setup derlemesi tamamlanamadi. Yukaridaki hatayi inceleyin.
 pause
 exit /b 1
)
echo.
echo Setup dosyasi output klasorunde hazir.
pause
