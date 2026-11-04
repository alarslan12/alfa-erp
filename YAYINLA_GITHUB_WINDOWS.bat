@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0YAYINLA_GITHUB_WINDOWS.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
    echo GitHub Windows yayinlama / derleme adiminda hata kodu: %EXIT_CODE%
    echo Hatayi gorebilmek icin bu pencereyi kapatmayin.
)
pause
exit /b %EXIT_CODE%
