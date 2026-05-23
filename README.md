# poc-starter

PoC を本番運用に乗せる前提の FastAPI + PostgreSQL スターター。機能追加に集中できるよう、横断的な面倒ごとは最初から済ませてある。

## 整備済み

### ローカル開発

- ローカル PostgreSQL 環境（pgvector 付き）
- docker compose 環境

### アプリケーション

- FastAPI + SQLAlchemy + Pydantic
- 動作確認用 Web UI（FastAPI + html + js）
- 機能追加の雛形（router / service / schema + runner）
- 構造化ログ / トレース（text / Cloud Logging 互換 JSON、W3C traceparent）
- Cloud Run 向け Dockerfile（multi-stage + gunicorn）

### データベース

- SQLAlchemy スキーマ定義
- Alembic migration 対応（autogenerate / 差分チェック）
- Cloud SQL 対応（proxy / Cloud Run Job）
- Cloud SQL Studio の IAM ログイン

### 品質・CI

- ruff / pre-commit
- pytest + Testcontainers
- GitHub Actions CI（lint / test / terraform / migrate-check）

### ドキュメント

- OpenAPI 仕様 / Redocly UI の自動生成
- GitHub Pages 公開対応

### インフラ（GCP）

- Terraform（Cloud Run / Cloud SQL / Artifact Registry / Cloud Build SA / migrate Job）
- IAP / Google Group によるアクセス制御
- Cloud Build デプロイ対応

## 開発

最初にやること
```sh
brew install pre-commit cloud-sql-proxy uv terraform
pre-commit install
cp api/.env.example api/.env
make api   # postgres を起動して migration 適用 → api をローカル起動
```

ブラウザで http://localhost:8080 を開くと `POST /messages` と `POST /documents` / `GET /documents/similar` を試せる。Request / Response スキーマのサンプルとして `api/src/messages/schema.py` と `api/src/documents/schema.py` を参照。

わからないことは help で
```sh
make help               # ルート（開発フロー全般）
make -C api help        # api コンポーネント
make -C database help   # マイグレーション / Cloud SQL 操作
make -C infra help      # Terraform
```

## 構成

各コンポーネントは独立した `Makefile` を持ち、ルート `Makefile` は橋渡しに徹する。

```
.
├── Makefile             # ルート横断の開発フロー（api / test / fmt / build-deploy など）
├── README.md
├── docker-compose.yml
├── api/                 # FastAPI アプリ本体（README.md 参照）
├── database/            # PostgreSQL Dockerfile + SQLAlchemy スキーマ + Alembic マイグレーション
├── docs/                # make -C api docs の出力先（GitHub Pages のソース）
│   ├── openapi.json
│   └── index.html
└── infra/               # Terraform で GCP リソースを管理
```

## API ドキュメント

`make -C api docs` で `docs/openapi.json` と `docs/index.html` を生成する（main マージ時は `.github/workflows/docs-generate.yml` が自動コミット）。

GitHub Pages として公開するには:

1. リポジトリの **Settings → Pages**
2. **Source: Deploy from a branch** を選択
3. **Branch: main**, **Folder: /docs** を指定
4. 数分後 `https://<owner>.github.io/<repo>/` で Redocly UI が見られる

## 本番デプロイ

GCP（Cloud Run + IAP + Cloud SQL + Cloud Build）にデプロイする手順は [`infra/README.md`](infra/README.md) を参照。
