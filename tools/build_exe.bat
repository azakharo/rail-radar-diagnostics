SET PYT_PATH=C:\Python27
SET OUT_DIR=..\.build

SET PKG_NAME=rail_radar_diagnost

rmdir /S /Q %OUT_DIR%\build
rmdir /S /Q %OUT_DIR%\dist

%PYT_PATH%\Scripts\pyinstaller.exe --onefile --windowed --name srpps_test --distpath %OUT_DIR%\dist --workpath %OUT_DIR%\build -y --clean --icon=..\src\favicon.ico ..\src\diagnost.py
