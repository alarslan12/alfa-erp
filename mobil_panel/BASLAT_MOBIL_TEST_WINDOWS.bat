@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
 "..\.venv\Scripts\python.exe" -m http.server 8080 --bind 127.0.0.1
) else (
 py -3.13 -m http.server 8080 --bind 127.0.0.1
)
pause
