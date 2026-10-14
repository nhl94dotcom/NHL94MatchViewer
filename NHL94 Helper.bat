@echo off
rem Starts the NHL '94 Helper: records games played in RetroArch and lists them at http://localhost:9494/
cd /d "%~dp0"
python tools\nhl94_helper.py
if errorlevel 1 pause
