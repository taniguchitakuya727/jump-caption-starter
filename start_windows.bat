@echo off
setlocal
chcp 65001 >nul

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

set "PORT=8000"
if not "%JUMP_CAPTION_PORT%"=="" set "PORT=%JUMP_CAPTION_PORT%"
set "URL=http://127.0.0.1:%PORT%"

echo.
echo ========================================
echo  Jump Caption for Windows
echo ========================================
echo.

echo Python を確認しています...
where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=py -3"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PYTHON_CMD=python"
  ) else (
    goto missing_python
  )
)

%PYTHON_CMD% --version
if errorlevel 1 goto missing_python

echo.
echo FFmpeg を確認しています...
where ffmpeg >nul 2>nul
if errorlevel 1 goto missing_ffmpeg

where ffprobe >nul 2>nul
if errorlevel 1 goto missing_ffprobe

ffmpeg -version | findstr /B /C:"ffmpeg version"
echo FFmpeg と ffprobe を確認しました。

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo 初回セットアップ: 仮想環境を作成しています...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto error
) else (
  echo.
  echo 既存の仮想環境を使います。
)

echo pip を更新しています...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error

echo 必要なPythonパッケージを確認しています...
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto error

echo.
echo Windows起動前チェック:
".venv\Scripts\python.exe" tools\check_windows_readiness.py
if errorlevel 1 goto error

echo.
echo ブラウザを開きます: %URL%
start "" "%URL%"
echo.
echo サーバーを起動しています。このウィンドウを閉じるとアプリも停止します。
echo.
".venv\Scripts\python.exe" -m app
goto end

:missing_python
echo.
echo [必要] Python が入っていません。
echo Jump Caption には Python 3.10 または 3.11 が必要です。
echo.
echo こちらからWindows版Pythonをインストールしてください:
echo https://www.python.org/downloads/windows/
echo.
echo インストール時は "Add python.exe to PATH" にチェックを入れてください。
echo インストール後、もう一度 start_windows.bat をダブルクリックしてください。
echo.
start "" "https://www.python.org/downloads/windows/"
goto error

:missing_ffmpeg
echo.
echo [必要] FFmpeg が入っていません。
echo Jump Caption のジャンプカットには FFmpeg と ffprobe が必要です。
echo.
echo この画面から自動インストールを試す場合は Y を入力して Enter を押してください。
echo 手動で入れる場合は Enter のみ押してください。インストールページを開きます。
echo.
set /p INSTALL_CHOICE=FFmpegを自動インストールしますか？ [Y/Enter]: 
if /I "%INSTALL_CHOICE%"=="Y" goto run_ffmpeg_installer
goto open_ffmpeg_page

:missing_ffprobe
echo.
echo [必要] ffprobe が見つかりません。
echo ffprobe は通常 FFmpeg と一緒に入ります。
echo.
echo FFmpeg を入れ直すか、FFmpeg の bin フォルダを PATH に追加してください。
echo こちらのページを開きます:
echo https://www.gyan.dev/ffmpeg/builds/
echo.
start "" "https://www.gyan.dev/ffmpeg/builds/"
goto error

:run_ffmpeg_installer
if exist "install_ffmpeg_windows.bat" (
  call "install_ffmpeg_windows.bat"
) else (
  echo install_ffmpeg_windows.bat が見つかりません。
)
echo.
echo インストール後、もう一度 start_windows.bat をダブルクリックしてください。
goto error

:open_ffmpeg_page
echo.
echo こちらから FFmpeg をインストールしてください:
echo https://www.gyan.dev/ffmpeg/builds/
echo.
echo release builds の ffmpeg-release-essentials.zip をダウンロードし、
echo 展開した bin フォルダを PATH に追加してください。
echo.
start "" "https://www.gyan.dev/ffmpeg/builds/"
goto error

:error
echo.
echo セットアップまたは起動に失敗しました。
echo 上のメッセージを確認してください。
pause
exit /b 1

:end
echo.
echo Jump Caption を終了しました。
pause
