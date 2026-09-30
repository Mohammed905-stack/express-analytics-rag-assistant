@echo off
cd /d "%~dp0"
py scripts\launch.py --setup-only
if errorlevel 1 pause
