# Jump CaptionをGitHub経由でWebアプリ化する手順

## 重要な前提

GitHub Pagesだけでは、Jump Caption本体は動きません。

Jump Captionは次をサーバー側で使うためです。

- Python / FastAPI
- FFmpeg / ffprobe
- faster-whisper
- 動画アップロードとローカル処理

そのため、実用構成は次です。

```text
GitHubリポジトリ
↓
Render / Fly.io / Google Cloud Run など
↓
DockerでJump Captionを起動
↓
ブラウザからWebアプリとして使う
```

このリポジトリには、GitHub連携デプロイ用に次を追加しています。

- `Dockerfile`
- `.dockerignore`
- `render.yaml`
- `.github/workflows/ci.yml`

## まずGitHubに上げる

```bash
git add .
git commit -m "Prepare GitHub web deployment"
git branch -M main
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

すでにremoteがある場合は、`git remote add origin ...` は不要です。

## Renderで公開する場合

1. GitHubにこのリポジトリをpushする
2. RenderでNew Web Serviceを作る
3. GitHubリポジトリを選ぶ
4. EnvironmentはDockerを選ぶ
5. `render.yaml` を使う場合はBlueprintとして作成する
6. デプロイ完了後、発行されたURLを開く

Render側ではDockerfileによりFFmpegも入ります。

## ローカルでDocker確認する

```bash
docker build -t jump-caption .
docker run --rm -p 8000:8000 jump-caption
```

ブラウザで開きます。

```text
http://127.0.0.1:8000
```

## Web公開版の注意

現状はMVPなので、公開範囲は限定してください。

- アップロード動画はサーバー側の `uploads/` に置かれる
- 出力ファイルはサーバー側の `outputs/` に置かれる
- Renderなどの無料/小型環境では、処理が遅い、またはメモリ不足になる可能性がある
- Whisperモデル初回ダウンロードに時間がかかる
- サーバー再起動や再デプロイで保存ファイルが消える環境がある
- 誰でもアクセスできるURLにすると、他人が動画をアップロードできる

## 最初に試す設定

Web公開版では、まず短い動画で試してください。

- 30秒から1分程度
- Whisperモデルは `tiny`
- 日本語動画なら言語は `日本語`

## 今後必要になる改善

本格的に人に使ってもらうなら、次が必要です。

- ログインまたは合言葉認証
- アップロード容量制限
- 処理完了後の自動削除
- 永続ストレージ
- 長時間処理のジョブキュー化
- 処理中プログレス表示
- Whisperモデルの事前ダウンロード
- エラー時の分かりやすい画面表示
