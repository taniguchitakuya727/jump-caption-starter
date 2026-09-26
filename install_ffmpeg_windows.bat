@echo off
setlocal

echo.
echo ========================================
echo  FFmpeg installer for Jump Caption
echo ========================================
echo.

where winget >nul 2>nul
if errorlevel 1 (
  echo winget was not found.
  echo Please install FFmpeg manually.
  echo.
  echo Manual install page:
  echo https://www.gyan.dev/ffmpeg/builds/
  echo.
  echo Download ffmpeg-release-essentials.zip from release builds.
  echo Then add the extracted bin folder to PATH.
  echo.
  start "" "https://www.gyan.dev/ffmpeg/builds/"
  goto error
)

echo Installing FFmpeg with winget...
echo If Windows asks for confirmation, approve it.
echo.
winget install --id Gyan.FFmpeg -e
if errorlevel 1 goto error

echo.
echo FFmpeg installation finished.
echo Run start_windows.bat again.
echo If FFmpeg is still not found, restart Windows and try again.
echo.
pause
exit /b 0

:error
echo.
echo FFmpeg installation did not finish.
echo Please read the messages above.
pause
exit /b 1
