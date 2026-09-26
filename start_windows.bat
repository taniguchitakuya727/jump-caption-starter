@echo off
setlocal

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

if not exist "start_windows_core.bat" (
  echo start_windows_core.bat was not found.
  echo Please unzip the whole jump-caption-mvp folder again.
  echo.
  pause
  exit /b 1
)

call "%APP_DIR%start_windows_core.bat"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo This window is kept open so you can read messages above.
pause
exit /b %EXIT_CODE%
