@echo off
rem Builds dist\NHL94 Helper.exe: the helper, converter and viewer in one file for people without Python, and
rem dist\NHL94 Helper.zip, the package that goes to the public GitHub release.
rem Needs Python with PyInstaller (python -m pip install pyinstaller). Run from anywhere.
rem The public build can't broadcast to a website: live_s3 (the S3 upload) is left out, and the viewer's Help without
rem its "Watching live" section (between the viewer's broadcast markers). The local stream mode (--live-local, live
rem stats for OBS on this computer) stays. Broadcasting is only from Python (the user's own launcher).
cd /d "%~dp0.."
set ROOTDIR=%CD%
if not exist rink_gens.js python tools\embed_rink.py
if not exist rink_snes.js python tools\embed_rink.py
set DIST=%ROOTDIR%\dist
if not exist "%ROOTDIR%\build\public" mkdir "%ROOTDIR%\build\public"
python -c "import re,sys; t=open(sys.argv[1],encoding='utf-8').read(); u=re.sub(r'<!-- broadcast.*?<!-- /broadcast -->\n?','',t,flags=re.S); assert u!=t; open(sys.argv[2],'w',encoding='utf-8',newline='').write(u)" "%ROOTDIR%\viewer.html" "%ROOTDIR%\build\public\viewer.html"
if errorlevel 1 exit /b 1
set VIEWER=%ROOTDIR%\build\public\viewer.html
python -m PyInstaller --noconfirm --clean --onefile --console --name "NHL94 Helper" ^
  --paths "%ROOTDIR%\tools" ^
  --hidden-import nhl94_helper --hidden-import nhl94_memory --hidden-import export_match ^
  --hidden-import extract_sprites --hidden-import share_game --hidden-import png_read --hidden-import season --hidden-import romnames --hidden-import xg --hidden-import xg_snes --hidden-import deserve ^
  --hidden-import live_broadcast --hidden-import live_overlay ^
  --exclude-module live_s3 --exclude-module boto3 --exclude-module botocore ^
  --hidden-import systems --hidden-import systems.common --hidden-import systems.process ^
  --hidden-import systems.genesis --hidden-import systems.snes ^
  --add-data "%VIEWER%;." --add-data "%ROOTDIR%\helper.html;." --add-data "%ROOTDIR%\season.html;." --add-data "%ROOTDIR%\overlay.html;." --add-data "%ROOTDIR%\rink_gens.js;." ^
  --add-data "%ROOTDIR%\rink_benches.js;." --add-data "%ROOTDIR%\rink_gens.png;." ^
  --add-data "%ROOTDIR%\rink_snes.js;." --add-data "%ROOTDIR%\rink_benches_snes.js;." --add-data "%ROOTDIR%\rink_snes.png;." ^
  --distpath "%DIST%" --workpath "%ROOTDIR%\build\pyinstaller" --specpath "%ROOTDIR%\build" ^
  "%ROOTDIR%\tools\helper_main.py"
if errorlevel 1 exit /b 1
rem The package: the .exe, its read-me, and the stream mode's launcher and guide, zipped.
copy /y "%ROOTDIR%\tools\tester_readme.txt" "%DIST%\Read me first.txt" >nul
copy /y "%ROOTDIR%\tools\stream_launcher.bat" "%DIST%\NHL94 Helper - Stream.bat" >nul
copy /y "%ROOTDIR%\docs\STREAMING_GUIDE.md" "%DIST%\Streaming guide.txt" >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path '%DIST%\NHL94 Helper.exe','%DIST%\Read me first.txt','%DIST%\NHL94 Helper - Stream.bat','%DIST%\Streaming guide.txt' -DestinationPath '%DIST%\NHL94 Helper.zip'"
