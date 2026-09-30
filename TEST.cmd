@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run START.cmd once to install the project environment first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pytest -q
pause
