@echo off
setlocal
chcp 65001 >nul

echo.
echo ========================================
echo  FFmpeg installer for Jump Caption
echo ========================================
echo.

where winget >nul 2>nul
if errorlevel 1 (
  echo winget が見つかりません。
  echo Windows 10/11 の App Installer が有効な環境で使えます。
  echo.
  echo 手動で入れる場合:
  echo 1. https://www.gyan.dev/ffmpeg/builds/ をブラウザで開く
  echo 2. release builds の ffmpeg-release-essentials.zip をダウンロード
  echo 3. 展開した bin フォルダを PATH に追加
  echo.
  goto error
)

echo winget で FFmpeg をインストールします。
echo 途中で確認画面が出た場合は、内容を確認して続行してください。
echo.
winget install --id Gyan.FFmpeg -e
if errorlevel 1 goto error

echo.
echo FFmpeg のインストールが完了しました。
echo 新しく start_windows.bat を起動し直してください。
echo まだ見つからない場合は、Windowsを再起動してから試してください。
echo.
pause
exit /b 0

:error
echo.
echo FFmpeg のインストールを完了できませんでした。
echo 上のメッセージを確認してください。
pause
exit /b 1
