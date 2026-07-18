# Jump Caption

Jump Caption は、Mac / Windows の両方で動くローカルWebアプリとして開発する動画編集補助ツールです。

Sprint 0 では、FastAPI のローカルサーバー、トップページ、動画ファイル選択UI、FFmpeg検出APIだけを実装しています。動画加工、Whisper、字幕生成はまだ実装していません。

## Requirements

- Python 3.9 以上
- FFmpeg
- macOS または Windows

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

PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

FFmpeg は公式ビルド、winget、または Chocolatey などでインストールし、`ffmpeg.exe` が `PATH` から実行できる状態にしてください。

winget の例:

```powershell
winget install Gyan.FFmpeg
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

Windows PowerShell:

```powershell
$env:JUMP_CAPTION_PORT = "8080"
python -m app
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

## Assumptions

- Sprint 0 では選択した動画ファイルをアップロードせず、ブラウザ側でファイル名とサイズを表示するだけにしています。
- FFmpeg はアプリに同梱せず、ユーザーの `PATH` から検出します。
- Windows対応を妨げないよう、OS固有のパス区切りやシェル前提の処理はアプリ本体に入れていません。

