# Next

## Sprint 0: Repository Bootstrap

### Goal

Mac上で開発を開始でき、将来Windowsでも同じコードを動かせる最小リポジトリを作る。

### Tasks

1. Gitリポジトリを初期化
2. Pythonプロジェクト構成を作成
3. FastAPIでローカルサーバーを起動
4. ブラウザでトップページを表示
5. FFmpegの存在確認APIを作る
6. 動画ファイルを選択できるUIを作る
7. READMEにMac / Windowsの開発手順を記載
8. 基本テストを追加
9. git statusがcleanになるまで整える

### Exit Criteria

- `python -m` または1つの起動スクリプトでサーバーが立ち上がる
- ブラウザで画面が開く
- FFmpegの検出結果が画面に表示される
- 動画ファイルを選択できる
- まだ動画加工はしない
- Macでテスト済み
- Windows対応を妨げるOS依存コードを避ける

## Sprint 1: Silence Detection and Jump Cut

### Goal

動画を読み込み、無音区間を検出し、ジャンプカット済みMP4を出力する。

### Requirements

- FFmpegを使用
- 無音判定しきい値を指定可能
- 最短無音時間を指定可能
- 前後の余白を指定可能
- 元ファイルは変更しない
- 出力名は `<original>_cut.mp4`
- 処理ログを画面に表示
- エラー時に原因が分かる表示を出す

### Exit Criteria

- 1本のMP4で処理成功
- 出力動画の音声・映像同期が保たれる
- 変更した設定が処理へ反映される
- 無音区間一覧をJSONとして保存できる

## Sprint 2: Local Subtitle Generation

### Goal

ジャンプカット済み動画からローカルAIで字幕を生成する。

### Requirements

- faster-whisperを使用
- 日本語を初期値にする
- CPUでも動作可能
- SRT / TXT を生成
- 認識確信度または怪しい区間情報を保持
- モデルは初期値として small または適切な軽量モデルを選定
- モデルの初回ダウンロードを案内する

## Sprint 3: Subtitle Editor

### Goal

動画を再生しながら字幕本文と時間を修正できる。

### Requirements

- 動画プレビュー
- 字幕一覧
- 字幕選択で該当位置へシーク
- 本文編集
- 開始・終了時刻編集
- 字幕の追加・削除
- 分割・結合
- 検索・置換
- Undo / Redo
- 自動保存
- SRT再出力

## Sprint 4: AI Subtitle Formatting

### Goal

AIまたは言語解析により、日本語字幕の可読性を高める。

### Evaluation Factors

- 意味の切れ目
- 助詞の位置
- 一画面の文字数
- 表示時間
- 改行位置
- 読み速度
- 発話タイミング
- 2行以内
- 意味の途中で切らない
- 助詞だけを次の字幕へ残さない

### Important

元の発話内容を勝手に要約・言い換えない。
字幕の区切りと改行を整えることが目的。
