# Codexへの最初の指示

このリポジトリの `PROJECT.md`、`DECISIONS.md`、`NEXT.md` を最初にすべて読んでください。

あなたは実装担当です。まず Sprint 0 のみを実装してください。Sprint 1以降には進まないでください。

## Sprint 0 の目的

Mac上で開発を開始でき、将来Windowsでも同じコードを動かせる最小のローカルWebアプリを作ること。

## 実装要件

- Python + FastAPI
- 可能な限りOS非依存
- ブラウザでトップページを表示
- 動画ファイルを選択できる
- FFmpegが利用可能か確認できる
- FFmpegの検出結果を画面に表示
- 動画加工、Whisper、字幕生成はまだ実装しない
- READMEにMac / Windowsの開発環境構築手順を書く
- 最低限のテストを追加
- 適切な `.gitignore` を追加
- 既存の設計文書を勝手に書き換えない
- 不明点は合理的な仮定を置き、READMEまたは実装メモへ明記する
- 実装後にテストを実行する
- 最後に変更ファイル、実行方法、テスト結果、未解決事項を報告する

## 推奨構成

以下は推奨であり、必要に応じて改善してよい。

```text
jump-caption/
├── app/
│   ├── main.py
│   ├── services/
│   │   └── ffmpeg.py
│   ├── static/
│   │   ├── app.js
│   │   └── style.css
│   └── templates/
│       └── index.html
├── tests/
├── PROJECT.md
├── DECISIONS.md
├── NEXT.md
├── README.md
├── pyproject.toml
└── .gitignore
```

## 完了条件

- 1つの明確なコマンドで起動できる
- ブラウザで画面が表示される
- FFmpegの検出結果が確認できる
- 動画ファイルを選択できる
- テストが通る
- git statusが確認できる状態まで整理されている
