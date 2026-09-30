@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python from python.org first.
  pause
  exit /b 1
)
py scripts\launch.py
if errorlevel 1 pause
