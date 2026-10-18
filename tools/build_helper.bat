@echo off
rem Builds dist\NHL94 Helper.exe: the helper, converter and viewer in one file for people without Python.
rem Needs Python with PyInstaller (python -m pip install pyinstaller). Run from anywhere.
cd /d "%~dp0.."
set ROOTDIR=%CD%
if not exist rink_gens.js python tools\embed_rink.py
if not exist rink_snes.js python tools\embed_rink.py
python -m PyInstaller --noconfirm --clean --onefile --console --name "NHL94 Helper" ^
  --paths "%ROOTDIR%\tools" ^
  --hidden-import nhl94_helper --hidden-import nhl94_memory --hidden-import export_match ^
  --hidden-import extract_sprites --hidden-import share_game --hidden-import png_read --hidden-import season --hidden-import romnames --hidden-import xg --hidden-import xg_snes ^
  --hidden-import systems --hidden-import systems.common --hidden-import systems.process ^
  --hidden-import systems.genesis --hidden-import systems.snes ^
  --add-data "%ROOTDIR%\viewer.html;." --add-data "%ROOTDIR%\helper.html;." --add-data "%ROOTDIR%\season.html;." --add-data "%ROOTDIR%\rink_gens.js;." ^
  --add-data "%ROOTDIR%\rink_benches.js;." --add-data "%ROOTDIR%\rink_gens.png;." ^
  --add-data "%ROOTDIR%\rink_snes.js;." --add-data "%ROOTDIR%\rink_benches_snes.js;." --add-data "%ROOTDIR%\rink_snes.png;." ^
  --distpath "%ROOTDIR%\dist" --workpath "%ROOTDIR%\build\pyinstaller" --specpath "%ROOTDIR%\build" ^
  "%ROOTDIR%\tools\helper_main.py"
if errorlevel 1 exit /b 1
rem The package for testers and league members: the .exe and its read-me, zipped.
copy /y "%ROOTDIR%\tools\tester_readme.txt" "%ROOTDIR%\dist\Read me first.txt" >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path '%ROOTDIR%\dist\NHL94 Helper.exe','%ROOTDIR%\dist\Read me first.txt' -DestinationPath '%ROOTDIR%\dist\NHL94 Helper.zip'"
