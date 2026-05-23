# database/

DB スキーマ定義（SQLAlchemy）とマイグレーション（[Alembic](https://alembic.sqlalchemy.org/)）。ローカル開発用 PostgreSQL イメージもここに置く。独立した uv プロジェクト。

## 構成

```
database/
├── pyproject.toml       # alembic, sqlalchemy, psycopg[binary], pgvector
├── schema/models/       # SQLAlchemy モデル（autogenerate の入力）
├── alembic/versions/    # マイグレーション本体（autogenerate の出力をベース）
├── alembic.ini
├── Dockerfile           # postgres:16 + pgvector
├── migrate.Dockerfile   # Cloud Run Job 用 alembic コンテナ
├── Makefile
└── seed/grants.sql      # Cloud SQL の GRANT
```

api からは path 依存で参照され、ランタイムは `from schema.models import Message` のように使う。

コマンドの一覧は `make help`。

## スキーマ変更の考え方

DB のあるべき形は `schema/models/` と `alembic/versions/` の組み合わせで表現される。

- `schema/models/`: テーブル・カラム・型・nullable・主キー・FK・サーバーデフォルト・通常のインデックスなど SQLAlchemy で表現できるもの。Alembic の autogenerate で差分が拾われる
- `alembic/versions/`: モデルから `make gen-migrate` で自動生成された migration 本体。基本はこの自動生成をベースにする。ただし以下は autogenerate では検出されないので、`EMPTY=1` で雛形だけ作って手書きする:
  - `CREATE EXTENSION`（pgvector など）
  - ビュー・関数・トリガー
  - カラムの rename（autogenerate は drop + add に誤検出する）
  - データ移行（バックフィル）
  - CHECK 制約・部分インデックス・式インデックスなど複雑なもの

つまり DB の全体像を読むときは両方を見る必要がある。

## 推奨ワークフロー

モデルで完結する変更:

```sh
# schema/models/<feature>.py を編集
make gen-migrate NAME=add_tags_to_messages   # 差分から自動生成
# alembic/versions/<rev>_*.py を目視確認（特に rename は手直し）
make migrate-up
make migrate-check                                    # 差分 0 を確認
```

拡張・ビュー・データ移行など models で表せない変更:

```sh
make gen-migrate NAME=enable_pg_trgm EMPTY=1   # 空雛形
# alembic/versions/<rev>_*.py の upgrade()/downgrade() を手書き（op.execute(...) など）
make migrate-up
```

## 本番への適用

Cloud SQL 向けは `cloudsql-*` ターゲット（`make help` 参照）。

proxy 経由（開発者の手元）:

```sh
make cloudsql-proxy          # ターミナル A
make cloudsql-migrate        # ターミナル B: Alembic upgrade
make cloudsql-psql           # ターミナル B: psql 接続
make cloudsql-grant          # ターミナル B: seed/grants.sql
```

Cloud Run Job 経由（本番フロー、proxy 不要）:

```sh
make cloudsql-migrate-job
```

Cloud Run Job 側は `DB_URL` と `PGPASSWORD` を env で受け取り、`alembic/env.py` が `postgres://` を `postgresql+psycopg://` に正規化する。
