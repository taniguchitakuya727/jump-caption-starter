# Jump Caption Windows版 動作確認ガイド

このフォルダは、Windows PCで Jump Caption MVP を試すためのものです。exeやインストーラーではなく、Pythonで起動する確認版です。

## まず必要なもの

- Windows 10 / 11
- インターネット接続

`start_windows.bat` が Python と FFmpeg の有無を確認します。入っていない場合は、日本語の案内を表示して止まります。

Python 3.9以上で動く想定ですが、友人PCでの確認は Python 3.10 / 3.11 をおすすめします。Python 3.12以降は一部の音声認識パッケージの対応状況で詰まる可能性があります。

Pythonパッケージは `start_windows.bat` が自動で入れます。主な依存関係は次です。

- FastAPI
- Uvicorn
- python-multipart
- faster-whisper
- faster-whisper が使う CTranslate2 / Hugging Face Hub 関連パッケージ

## 初回起動

1. このフォルダをスペースや日本語を含まない短い場所へ置きます。
   例: `C:\JumpCaption`
2. `start_windows.bat` をダブルクリックします。
3. PythonまたはFFmpegが入っていない場合は、日本語の案内が表示されます。
4. PythonとFFmpegが入っていれば、初回だけ `.venv` 作成とPythonパッケージのインストールが走ります。
5. 起動前チェックでPython、FFmpeg、ffprobe、保存フォルダの状態を表示します。
6. ブラウザで `http://127.0.0.1:8000` が開きます。

起動中は黒いコマンド画面を閉じないでください。閉じるとアプリも停止します。

## 2回目以降

`start_windows.bat` をダブルクリックします。すでに `.venv` があれば、そのまま依存確認後に起動します。

## FFmpegの入れ方

FFmpegが入っていない状態で `start_windows.bat` を起動すると、日本語の案内が出ます。
画面の案内に従って `Y` を入力すると、同梱の `install_ffmpeg_windows.bat` で自動インストールを試します。

コマンドプロンプトで手動実行する場合は次です。

```bat
winget install Gyan.FFmpeg
```

インストール後、Windowsを再起動するか、新しく `start_windows.bat` を起動し直してください。
確認したい場合は、コマンドプロンプトで次を実行します。

```bat
ffmpeg -version
ffprobe -version
```

`ffmpeg` と `ffprobe` の両方が使える必要があります。

`start_windows.bat` はFFmpegまたはffprobeが見つからない場合、アプリを起動せずに案内を表示します。インストール後、もう一度 `start_windows.bat` をダブルクリックしてください。

## Whisperモデルについて

字幕生成を初めて実行すると、faster-whisper がWhisperモデルをダウンロードします。初期値は `small` です。軽く試す場合は画面で `tiny` または `base` を選んでください。

モデルは通常、Windowsユーザーのキャッシュ配下に保存されます。

```text
C:\Users\<ユーザー名>\.cache\huggingface\hub
```

保存場所は Hugging Face Hub の設定や環境変数により変わる場合があります。

## 出力ファイル

処理結果はこのフォルダ内の `outputs` に保存されます。

- `<original>_cut.mp4`
- `<original>_silences.json`
- `<original>_cut.srt`
- `<original>_cut.txt`
- `<original>_cut_subtitles.json`

アップロードされた元ファイルの作業コピーは `uploads` に入ります。

## Windowsでの注意

- まずは `C:\JumpCaption` のような短い英数字パスに置いてください。
- 日本語ファイル名やスペース入りパスでも動くように実装していますが、初回確認では短い英数字パスの方が切り分けしやすいです。
- アプリ本体はPythonの `pathlib` と `subprocess` のリスト引数でパスを渡しているため、バックスラッシュやスペース入りパスに対応しやすい作りです。
- Windowsの長いパス制限を避けるため、深いフォルダや長い動画ファイル名は初回確認では避けてください。
- 長い動画は処理に時間がかかります。
- 初回のPythonパッケージインストールとWhisperモデルダウンロードには時間がかかります。
- FFmpegがないとジャンプカットはできません。
- 出力先と一時的なアップロード先は、このフォルダ内の `outputs` と `uploads` です。

## 配布用フォルダを作る場合

開発PC側で次を実行すると、友人に渡しやすい最小フォルダを作れます。

```bat
python tools\build_windows_dist.py
```

生成されるフォルダ:

```text
dist_windows\jump-caption-mvp
```

このフォルダには、アプリ本体、`start_windows.bat`、`install_ffmpeg_windows.bat`、`README_WINDOWS.md`、設定ファイル、空の `outputs` / `uploads` が入ります。Python本体、FFmpeg、Whisperモデル、仮想環境、動画ファイルは含みません。

## 困ったとき

`start_windows.bat` の黒い画面に出ているエラーを確認してください。画面はすぐ閉じないようにしてあります。

よくある原因:

- Pythonが入っていない
- Pythonインストール時にPATHへ追加していない
- FFmpegが入っていない
- インターネット接続がない
- セキュリティソフトがPythonやFFmpegの実行を止めている
