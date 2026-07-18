# Jump Caption

## 目的

Mac / Windows の両方で使える、無料・ローカル処理中心の動画編集補助ツールを作る。

ユーザーは動画を読み込み、無音部分を自動ジャンプカットし、AIで字幕を生成し、ブラウザ上で誤字脱字やタイムコードを手動修正したうえで、編集済み動画と字幕ファイルを書き出せる。

## 対象ユーザー

- YouTube のトーク動画を作る人
- セミナー・講義動画を編集する人
- CapCut などへ正確な字幕を持ち込みたい人
- Mac / Windows の一般ユーザー

## 基本方針

- ローカルWebアプリとして実装する
- 動画・音声は原則として外部へ送信しない
- API課金なしで動く構成を優先する
- AIに任せる領域と、通常プログラムで安定処理する領域を分ける
- 字幕装飾や高度な映像編集は CapCut 等に任せる
- 本ツールはジャンプカット、字幕生成、字幕校正に集中する

## 初期技術構成

- Backend: Python + FastAPI
- Frontend: HTML / CSS / JavaScript
- Video processing: FFmpeg
- Silence analysis / jump cut: FFmpeg ベース
- Speech recognition: faster-whisper
- Subtitle formats: SRT / VTT / TXT
- Project persistence: JSON
- Packaging:
  - Windows: PyInstaller 等
  - macOS: app bundle 化を後段で検討

## AIを使う領域

### 初期MVP

1. 音声認識とタイムコード生成
2. 認識確信度の低い字幕や怪しい箇所の強調

### 後続の重要機能

AIを用いて字幕を以下の観点から総合的に整形する。

- 意味の切れ目
- 助詞の位置
- 一画面の文字数
- 表示時間
- 読みやすい改行位置
- 発話タイミングとの一致
- 短時間に文字を詰め込みすぎないこと
- 意味の途中で字幕を切らないこと
- 助詞だけを次の字幕へ残さないこと

単純な固定文字数分割ではなく、日本語の自然さ、発話区間、字幕の可読性を合わせて最適化する。

## AIを使わない領域

- 動画の読み込み
- 音声抽出
- 無音区間の検出
- 動画区間の切り出しと結合
- SRT / VTT / TXT の読み書き
- 字幕本文の手動編集
- 字幕の開始・終了時刻の手動編集
- MP4の書き出し
- プロジェクトの保存と再読込

## 入力形式

初期対応候補:

- MP4
- MOV
- MKV
- AVI
- M4V
- MP3
- M4A
- WAV

## 出力

- ジャンプカット済み MP4
- 修正済み SRT
- VTT
- TXT
- 再編集用 JSON

## UIの基本像

- 動画ファイルの選択またはドラッグ＆ドロップ
- 無音判定音量
- 削除対象とする無音の最短時間
- 発話の前後に残す余白
- 処理開始
- 動画プレビュー
- 字幕一覧
- 字幕クリックで該当時間へ移動
- 字幕本文の直接編集
- 開始時刻・終了時刻の修正
- 検索・置換
- SRT / TXT / MP4 書き出し

## 初期値候補

- silence threshold: -35 dB
- minimum silence duration: 0.5 sec
- retained margin: 0.15 sec

これらはユーザーが変更できるようにする。
