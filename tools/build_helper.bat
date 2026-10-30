@echo off
rem Builds dist\NHL94 Helper.exe: the helper, converter and viewer in one file for people without Python.
rem Needs Python with PyInstaller (python -m pip install pyinstaller). Run from anywhere.
rem "build_helper.bat nobroadcast" builds dist\nobroadcast\ instead: no live broadcast module, and the viewer's Help
rem without its "Watching live" section (between the viewer's broadcast markers).
cd /d "%~dp0.."
set ROOTDIR=%CD%
if not exist rink_gens.js python tools\embed_rink.py
if not exist rink_snes.js python tools\embed_rink.py
set VIEWER=%ROOTDIR%\viewer.html
set DIST=%ROOTDIR%\dist
set BROADCAST=--hidden-import live_broadcast
if /i "%~1"=="nobroadcast" (
  if not exist "%ROOTDIR%\build\nobroadcast" mkdir "%ROOTDIR%\build\nobroadcast"
  python -c "import re,sys; t=open(sys.argv[1],encoding='utf-8').read(); u=re.sub(r'<!-- broadcast.*?<!-- /broadcast -->\n?','',t,flags=re.S); assert u!=t; open(sys.argv[2],'w',encoding='utf-8',newline='').write(u)" "%ROOTDIR%\viewer.html" "%ROOTDIR%\build\nobroadcast\viewer.html"
  if errorlevel 1 exit /b 1
  set VIEWER=%ROOTDIR%\build\nobroadcast\viewer.html
  set DIST=%ROOTDIR%\dist\nobroadcast
  set BROADCAST=--exclude-module live_broadcast
)
python -m PyInstaller --noconfirm --clean --onefile --console --name "NHL94 Helper" ^
  --paths "%ROOTDIR%\tools" ^
  --hidden-import nhl94_helper --hidden-import nhl94_memory --hidden-import export_match ^
  --hidden-import extract_sprites --hidden-import share_game --hidden-import png_read --hidden-import season --hidden-import romnames --hidden-import xg --hidden-import xg_snes --hidden-import deserve %BROADCAST% ^
  --exclude-module boto3 --exclude-module botocore ^
  --hidden-import systems --hidden-import systems.common --hidden-import systems.process ^
  --hidden-import systems.genesis --hidden-import systems.snes ^
  --add-data "%VIEWER%;." --add-data "%ROOTDIR%\helper.html;." --add-data "%ROOTDIR%\season.html;." --add-data "%ROOTDIR%\rink_gens.js;." ^
  --add-data "%ROOTDIR%\rink_benches.js;." --add-data "%ROOTDIR%\rink_gens.png;." ^
  --add-data "%ROOTDIR%\rink_snes.js;." --add-data "%ROOTDIR%\rink_benches_snes.js;." --add-data "%ROOTDIR%\rink_snes.png;." ^
  --distpath "%DIST%" --workpath "%ROOTDIR%\build\pyinstaller" --specpath "%ROOTDIR%\build" ^
  "%ROOTDIR%\tools\helper_main.py"
if errorlevel 1 exit /b 1
rem The package for testers and league members: the .exe and its read-me, zipped.
copy /y "%ROOTDIR%\tools\tester_readme.txt" "%DIST%\Read me first.txt" >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path '%DIST%\NHL94 Helper.exe','%DIST%\Read me first.txt' -DestinationPath '%DIST%\NHL94 Helper.zip'"
