SET PYT_PATH=C:\Python27
SET OUT_DIR=d:\Temp
SET PKG_NAME=rail_radar_diagnost

SET LOG_PATH=%OUT_DIR%\%PKG_NAME%_create_exe.log
SET PKG_OUT_DIR=%OUT_DIR%\%PKG_NAME%

rmdir /S /Q %PKG_OUT_DIR%
rm %LOG_PATH%

pushd ..\src
%PYT_PATH%\python.exe %PYT_PATH%\scripts\cxfreeze diagnost.py --target-dir %PKG_OUT_DIR% > %LOG_PATH%
popd
