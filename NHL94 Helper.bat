@echo off
rem Starts the NHL '94 Helper: records games played in RetroArch and lists them at http://localhost:9494/
rem Games are kept in Documents\NHL94 Viewer, the same folder NHL94 Helper.exe uses, with the latest pages copied there.
cd /d "%~dp0"
set "NHL94_HOME=%USERPROFILE%\Documents\NHL94 Viewer"
if not exist "%NHL94_HOME%" mkdir "%NHL94_HOME%"
copy /y viewer.html "%NHL94_HOME%\" >nul
copy /y season.html "%NHL94_HOME%\" >nul
copy /y helper.html "%NHL94_HOME%\" >nul
for %%f in (rink_*.js rink_*.png) do copy /y "%%f" "%NHL94_HOME%\" >nul
python tools\nhl94_helper.py
if errorlevel 1 pause
