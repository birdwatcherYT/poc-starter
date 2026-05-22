# database/

ローカル開発用 PostgreSQL イメージと、`golang-migrate` 形式のマイグレーション。

## 構成

```
database/
├── Dockerfile           # postgres:16 + pgvector（拡張を追加したい場合はここに apt-get で並べる）
├── migrate.Dockerfile   # Cloud Run Job 用 migrate コンテナ
├── migrations/          # {timestamp}_<name>.up.sql / .down.sql のペア（冪等に書く）
└── seed/grants.sql      # Cloud SQL の IAM ユーザー / アプリ SA への GRANT
```

## ローカル DB

```sh
make db-up                       # postgres 起動 + migration まで自動適用（ルートから）
make gen-migrate NAME=add_users  # 新規 migration の雛形作成
```

その他のターゲットは `make help`。

## Cloud SQL

### ローカルから proxy 経由（開発用）

別ターミナルで proxy を起動して、本シェルから流す（接続情報は terraform output から自動取得）:

```sh
make cloudsql-proxy        # 別ターミナル
make migrate-cloudsql      # 本シェル
make grant-cloudsql        # 初回のみ。terraform.tfvars と output から自動取得
```

### Cloud Run Job 経由（本番デプロイフロー）

terraform で作られる `migrate-job` を実行:

```sh
make run-migrate-job
```
