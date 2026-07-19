# Jump Caption

Jump Caption は、Mac / Windows の両方で動くローカルWebアプリとして開発する動画編集補助ツールです。

Sprint A では、FastAPI のローカルサーバー、動画ファイル選択UI、FFmpeg検出API、無音検出、ジャンプカット済みMP4出力、無音区間JSON保存、faster-whisper によるローカル字幕生成、ブラウザ上の字幕エディタ、Windows起動補助、ルールベースの日本語字幕整形を実装しています。

## Requirements

- Python 3.9 以上
- FFmpeg
- macOS または Windows

Windowsで開発者ではない人に試してもらう場合は、`README_WINDOWS.md` を添えて `start_windows.bat` をダブルクリックしてもらってください。PythonやFFmpegがない場合は日本語で案内し、揃っていれば自動起動します。

## Setup on macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

FFmpeg が未インストールの場合:

```bash
brew install ffmpeg
```

## Setup on Windows

簡単に試す場合は、コマンド入力ではなく `start_windows.bat` のダブルクリック起動を推奨します。
PythonとFFmpegを確認し、不足していれば日本語でインストール先を案内します。揃っている場合、初回は `.venv` の作成、Pythonパッケージのインストール、起動前チェックを行います。

コマンドで手動セットアップしたい場合:

```bat
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

FFmpeg は公式ビルド、winget、または Chocolatey などでインストールし、`ffmpeg.exe` が `PATH` から実行できる状態にしてください。

winget の例:

```bat
winget install Gyan.FFmpeg
```

Windows配布用フォルダを作る場合:

```bash
python tools/build_windows_dist.py
```

生成先:

```text
dist_windows/jump-caption-mvp
```

## Run

```bash
python -m app
```

ブラウザで次を開きます。

```text
http://127.0.0.1:8000
```

ホストやポートを変えたい場合は環境変数を使えます。

macOS:

```bash
JUMP_CAPTION_PORT=8080 python -m app
```

Windowsのコマンドプロンプト:

```bat
set JUMP_CAPTION_PORT=8080
.\.venv\Scripts\python.exe -m app
```

## Test

```bash
pytest
```

## Current Scope

- トップページを表示する
- 動画または音声ファイルを選択できる
- `/api/ffmpeg` で FFmpeg の利用可否、検出パス、バージョンを返す
- 画面に FFmpeg の検出結果を表示する
- 無音判定音量、最短無音時間、残す余白を指定できる
- 選択したファイルをアップロードし、FFmpegで無音区間を検出する
- `<original>_cut.mp4` と `<original>_silences.json` を `outputs/` に保存する
- 処理ログとエラー内容を画面に表示する
- ジャンプカット済みMP4から SRT / TXT を生成する
- 字幕セグメント、認識ログ、怪しい区間フラグを `<original>_subtitles.json` に保存する
- 動画を再生しながら字幕本文と開始・終了時刻を編集できる
- 字幕選択で動画を該当時間へシークできる
- 字幕の追加、削除、分割、結合、検索置換、Undo / Redo、自動保存ができる
- 編集後の SRT / TXT / 字幕メタデータJSONを再出力する
- `outputs/` に残っているカット済みMP4から字幕生成を再開できる
- `outputs/` に残っている字幕メタデータJSONから字幕エディタを直接開ける
- 字幕の長さ、改行、短すぎる字幕の結合、長すぎる字幕の分割をローカルで整形できる
- 字幕分割時は句読点、接続語、助詞、文字数バランスを見て自然な本文境界へ寄せる
- Whisper認識時に可能な範囲で単語タイムスタンプを取得し、字幕メタデータへ保存する
- 字幕整形は `app/services/subtitle_optimizer.py` のルールベース処理で行う
- 整形後に本文欠落、重複、時刻順、重なり、行数、文字数、表示時間を検証する

## Assumptions

- Sprint 2 では、ブラウザで選択したファイルをローカルFastAPIサーバーへアップロードして処理します。外部サービスには送信しません。
- FFmpeg はアプリに同梱せず、ユーザーの `PATH` から検出します。
- `ffprobe` も `PATH` から検出します。通常は FFmpeg と同時にインストールされます。
- Sprint 1 のジャンプカットは音声付きMP4を主対象にしています。音声トラックのない動画は後続で対応します。
- Whisperモデルは初回の字幕生成時にダウンロードされます。初期値は日本語、CPU、`small`、`int8`、word timestamps 有効です。
- faster-whisper の詳細な認識確信度はモデル出力に依存するため、Sprint 2 では `avg_logprob` と `no_speech_prob` を保存し、怪しい区間のフラグに使います。
- Sprint 3 の自動保存は、字幕編集後に短い待ち時間を置いてローカルの `outputs/` 内ファイルへ反映します。
- 途中再開の字幕エディタは、このアプリが生成した `<original>_subtitles.json` を対象にしています。
- Sprint 4 の字幕整形は外部AI APIを使わず、ローカルのルールベース処理として実装しています。本文の要約や言い換えはしません。
- 手動分割は現在の動画再生位置を時刻境界にし、本文側は近くの自然な文字境界へ寄せます。
- Windows対応を妨げないよう、OS固有のパス区切りやシェル前提の処理はアプリ本体に入れていません。

## Subtitle Optimizer Settings

- `minimum_duration`: 0.8 sec
- `maximum_duration`: 7.0 sec
- `minimum_gap`: 0.05 sec
- `preferred_chars_per_second`: 10 chars/sec
- `maximum_chars_per_second`: 15 chars/sec
- `max_chars_per_caption`: 36 chars
- `preferred_chars_per_line`: 18 chars
- `max_lines`: 2
