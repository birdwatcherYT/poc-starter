# api/

FastAPI アプリ本体。リクエスト処理 / DB アクセス / ログ / 静的フロントを含む。

## 構成

```
api/
├── api.py             # FastAPI エントリポイント
├── src/
│   ├── database.py        # SQLAlchemy Engine + Session ラッパー
│   ├── logger.py          # LOG_FORMAT=text|json 切替、構造化ログ
│   ├── trace_context.py   # W3C traceparent を ContextVar で伝播
│   ├── messages/          # 機能 = 1 フォルダのサンプル（POST /messages, GET /messages）
│   │   ├── router.py          # FastAPI ルーター（HTTP 層）
│   │   ├── service.py         # ビジネスロジック / DB アクセス
│   │   └── schema.py          # Pydantic の Request / Response モデル
│   └── documents/         # pgvector + ベクトル検索のサンプル（POST /documents, GET /documents/similar）
├── static/            # make run で配信される動作確認 UI（messages / documents）
├── tests/             # Testcontainers で PostgreSQL を立てる integration test
├── scripts/           # 動作確認 runner と OpenAPI 生成
├── Dockerfile         # multi-stage build + gunicorn（Cloud Run 用）
└── cloudbuild.yaml
```

新しい機能を足すときは `src/<feature>/` に `router.py` / `service.py` / `schema.py` の 3 点セットを置き、`api.py` で `include_router(..., prefix="/<feature>")` する。動作確認用に `scripts/<feature>_runner.py` も足す。

## 基本操作

事前に DB を起動しておく（`make -C database db-up`）。

```sh
make run                                    # uvicorn --reload で :8080 起動
make test                                   # Testcontainers で pytest
make fmt                                    # ruff format + check --fix
make build-deploy IMAGE_TAG=$(date +%s)     # Cloud Build → Cloud Run へデプロイ
```

`IMAGE_TAG` は可変にしておくと履歴を遡れる（latest 固定だと辿れないので本番では時刻 / SHA 推奨）。その他のターゲットは `make help`。

## scripts/

新しいエンドポイントを足したら既存の `*_runner.py` をコピーして作る運用。共通ヘルパは `_runner_common.py`。

```sh
uv run scripts/messages_runner.py                               # ローカル
BASE_URL=https://xxx.run.app uv run scripts/messages_runner.py  # 本番（gcloud identity token 自動付与）
```

本番へのアクセス可否は infra 側の設定に依存。詳細は [`../infra/README.md`](../infra/README.md)。
