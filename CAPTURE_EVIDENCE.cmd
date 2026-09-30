@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe scripts\capture_evidence.py
pause
