SET PYT_PATH=C:\Python27
SET OUT_DIR=..\.build

SET PKG_NAME=rail_radar_diagnost
SET LOG_PATH=%OUT_DIR%\%PKG_NAME%_build.log

%PYT_PATH%\Scripts\pyinstaller.exe --distpath %OUT_DIR%\dist --workpath %OUT_DIR%\build -y --clean ..\src\diagnost.py
