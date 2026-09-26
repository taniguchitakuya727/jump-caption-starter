@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

set "PORT=8000"
if not "%JUMP_CAPTION_PORT%"=="" set "PORT=%JUMP_CAPTION_PORT%"
set "URL=http://127.0.0.1:%PORT%"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"

echo.
echo ========================================
echo  Jump Caption for Windows
echo ========================================
echo.

echo Checking Python...
set "PYTHON_CMD="
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.11 --version >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
  ) else (
    py -3.10 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.10"
  )
)

if "!PYTHON_CMD!"=="" (
  where python >nul 2>nul
  if not errorlevel 1 (
    for /f "tokens=2" %%V in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%V"
    echo !PYTHON_VERSION! | findstr /R "^3\.1[01]\." >nul
    if not errorlevel 1 set "PYTHON_CMD=python"
  )
)

if "!PYTHON_CMD!"=="" goto unsupported_python

!PYTHON_CMD! --version
if errorlevel 1 goto missing_python

echo.
echo Checking FFmpeg...
where ffmpeg >nul 2>nul
if errorlevel 1 goto missing_ffmpeg

where ffprobe >nul 2>nul
if errorlevel 1 goto missing_ffprobe

ffmpeg -version | findstr /B /C:"ffmpeg version"
echo FFmpeg and ffprobe were found.

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo First setup: creating virtual environment...
  !PYTHON_CMD! -m venv .venv
  if errorlevel 1 goto error
) else (
  echo.
  echo Using existing virtual environment.
)

set "VENV_VERSION="
for /f "tokens=2" %%V in ('".venv\Scripts\python.exe" --version 2^>^&1') do set "VENV_VERSION=%%V"
echo Virtual environment Python: !VENV_VERSION!
echo !VENV_VERSION! | findstr /R "^3\.1[01]\." >nul
if errorlevel 1 goto invalid_venv

echo Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error

echo Installing required Python packages...
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto error

echo.
echo Readiness check:
".venv\Scripts\python.exe" tools\check_windows_readiness.py
if errorlevel 1 goto error

echo.
echo Opening browser: %URL%
start "" "%URL%"
echo.
echo Server is starting. Keep this window open while using Jump Caption.
echo Server log: %APP_DIR%logs\windows_server.log
echo.
".venv\Scripts\python.exe" tools\run_windows_server.py
goto end

:missing_python
echo.
echo [Required] Python was not found.
echo Jump Caption needs Python 3.10 or 3.11.
echo.
echo Install Python for Windows from:
echo https://www.python.org/downloads/windows/
echo.
echo IMPORTANT: Check "Add python.exe to PATH" during installation.
echo After installing Python, run start_windows.bat again.
echo.
start "" "https://www.python.org/downloads/windows/"
goto error

:unsupported_python
echo.
echo [Required] Python 3.10 or 3.11 was not found.
echo Python 3.13 is not supported for this test package.
echo.
echo Install Python 3.11 for Windows from:
echo https://www.python.org/downloads/windows/
echo.
echo IMPORTANT: Check "Add python.exe to PATH" during installation.
echo After installing Python 3.11, run start_windows.bat again.
echo.
start "" "https://www.python.org/downloads/windows/"
goto error

:invalid_venv
echo.
echo [Required] Existing .venv uses unsupported Python.
echo Jump Caption needs a .venv made with Python 3.10 or 3.11.
echo.
echo Delete this folder, then run start_windows.bat again:
echo %APP_DIR%.venv
echo.
echo If Python 3.11 is not installed yet, install it first from:
echo https://www.python.org/downloads/windows/
echo.
goto error

:missing_ffmpeg
echo.
echo [Required] FFmpeg was not found.
echo Jump Caption needs ffmpeg and ffprobe for jump cuts.
echo.
echo To try automatic installation, type Y and press Enter.
echo To install manually, just press Enter. The FFmpeg page will open.
echo.
set /p INSTALL_CHOICE=Install FFmpeg automatically? [Y/Enter]: 
if /I "%INSTALL_CHOICE%"=="Y" goto run_ffmpeg_installer
goto open_ffmpeg_page

:missing_ffprobe
echo.
echo [Required] ffprobe was not found.
echo ffprobe is usually installed together with FFmpeg.
echo.
echo Reinstall FFmpeg or add FFmpeg's bin folder to PATH.
echo This page will open:
echo https://www.gyan.dev/ffmpeg/builds/
echo.
start "" "https://www.gyan.dev/ffmpeg/builds/"
goto error

:run_ffmpeg_installer
if exist "install_ffmpeg_windows.bat" (
  call "install_ffmpeg_windows.bat"
) else (
  echo install_ffmpeg_windows.bat was not found.
)
echo.
echo After installing FFmpeg, run start_windows.bat again.
goto error

:open_ffmpeg_page
echo.
echo Install FFmpeg from:
echo https://www.gyan.dev/ffmpeg/builds/
echo.
echo Download ffmpeg-release-essentials.zip from release builds.
echo Then add the extracted bin folder to PATH.
echo.
start "" "https://www.gyan.dev/ffmpeg/builds/"
goto error

:error
echo.
echo Setup or startup failed.
echo Please read the messages above.
exit /b 1

:end
echo.
echo Jump Caption stopped.
exit /b 0
