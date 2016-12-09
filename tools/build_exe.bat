SET PYT_PATH=C:\Python27
SET OUT_DIR=..\.build

SET PKG_NAME=rail_radar_diagnost

%PYT_PATH%\Scripts\pyinstaller.exe --windowed --distpath %OUT_DIR%\dist --workpath %OUT_DIR%\build -y --clean --icon=..\src\favicon.ico ..\src\diagnost.py
