@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" cihaz_eslestir.py
) else (
  python cihaz_eslestir.py
)
