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

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=py -3"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PYTHON_CMD=python"
  ) else (
    echo Python が見つかりません。
    echo Python 3.10 または 3.11 を https://www.python.org/downloads/windows/ からインストールしてください。
    echo インストール時に "Add python.exe to PATH" を有効にしてください。
    goto error
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo 初回セットアップ: 仮想環境を作成しています...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto error
) else (
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
echo FFmpeg を確認しています...
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo.
  echo [注意] FFmpeg が見つかりません。
  echo ジャンプカットには FFmpeg と ffprobe が必要です。
  echo winget が使える場合:
  echo   winget install Gyan.FFmpeg
  echo.
  echo インストール後、このウィンドウを閉じて start_windows.bat を起動し直してください。
  echo.
) else (
  ffmpeg -version | findstr /B /C:"ffmpeg version"
)

where ffprobe >nul 2>nul
if errorlevel 1 (
  echo [注意] ffprobe が見つかりません。通常は FFmpeg と一緒にインストールされます。
)

echo.
echo ブラウザを開きます: %URL%
start "" "%URL%"
echo.
echo サーバーを起動しています。このウィンドウを閉じるとアプリも停止します。
echo.
".venv\Scripts\python.exe" -m app
goto end

:error
echo.
echo セットアップまたは起動に失敗しました。
echo 上のエラーメッセージを確認してください。
pause
exit /b 1

:end
echo.
echo Jump Caption を終了しました。
pause
