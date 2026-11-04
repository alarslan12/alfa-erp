@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0ALFA_TEMIZ_KURULUM.ps1"
echo.
if errorlevel 1 echo Clean local setup failed. Check the message above; no cloud changes were made.
pause
