# api/

FastAPI アプリ本体。リクエスト処理 / DB アクセス / ログ / 静的フロントを含む。

## 構成

```
api/
├── api.py             # FastAPI エントリポイント（lifespan で Database 初期化、TraceContext 仕込み）
├── src/
│   ├── database.py        # psycopg3 ConnectionPool ラッパー
│   ├── logger.py          # LOG_FORMAT=text|json で出力切替、構造化ログヘルパー
│   ├── trace_context.py   # W3C traceparent を ContextVar で伝播
│   └── example/           # 機能モジュールのサンプル（POST /example/echo）
│       ├── router.py          # FastAPI ルーター（HTTP 層）
│       ├── service.py         # ビジネスロジック / DB アクセス
│       └── schema.py          # Pydantic の Request / Response モデル
├── static/            # make run で配信される動作確認フォーム
├── tests/             # Testcontainers で PostgreSQL を立てる integration test
├── scripts/           # 動作確認 runner（example_runner.py）と OpenAPI 生成（generate_docs.py）
├── Dockerfile         # multi-stage build + gunicorn + uvicorn worker（Cloud Run 用）
└── cloudbuild.yaml    # gcloud builds submit の build 定義
```

## ローカル起動

```sh
make run    # uvicorn --reload で :8080 起動
make test   # Testcontainers で pytest
```

その他のターゲットは `make help`。

## scripts/

新しいエンドポイントを足したら `example_runner.py` をコピーして `*_runner.py` を作る運用。共通の `make_client()` / `call()` は `_runner_common.py` 参照。

```sh
uv run scripts/example_runner.py                                       # ローカル
BASE_URL=https://xxx.run.app uv run scripts/example_runner.py          # 本番（IAP 越し、gcloud token 自動付与）
```

curl で疎通確認（`var.iap_allowed_group` で許可した Google Group のメンバー限定）:

```sh
URL=$(terraform -chdir=../infra/terraform/env/dev output -raw service_uri)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$URL/health"
```

## デプロイ

初回 / 全体のセットアップ手順は [`../infra/README.md`](../infra/README.md) を参照。API のみを更新したいときは:

```sh
make build-deploy IMAGE_TAG=$(date +%s)
```

`IMAGE_TAG` を可変にしておくと履歴を遡れる（latest 固定だと辿れないので本番では時刻 / SHA 推奨）。
