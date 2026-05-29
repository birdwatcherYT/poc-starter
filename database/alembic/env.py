"""Alembic 環境設定。

接続情報の解決順:
1. 環境変数 `DB_URL` があればそれを使う（Cloud Run Job など URL 一本で渡す経路）
2. なければ `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` から組む
   （ローカル開発・cloud-sql-proxy 経由）

`postgres://` で始まる URL は SQLAlchemy 用に `postgresql+psycopg://` に正規化する。
パスワードは `DB_URL` に含めないユースケース（Cloud Run Job が `PGPASSWORD` で
渡す形）も想定し、libpq の環境変数解決にそのまま委ねる。
"""

import os
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

import schema.models  # noqa: F401  schema.models の __init__.py が全モデルを Base.metadata に登録するために import する
from alembic import context
from schema.base import Base

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

target_metadata = Base.metadata

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers=False: fileConfig はデフォルトで「既存の全 logger を disabled にする」ため、テストで Python プロセス内から alembic を呼ぶと src.logger などが死ぬ。明示的に無効化する。
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _build_url() -> str:
    raw = os.environ.get("DB_URL")
    if raw:
        # SQLAlchemy は postgres:// を受け付けないので postgresql+psycopg:// に揃える。
        if raw.startswith("postgres://"):
            raw = "postgresql+psycopg://" + raw[len("postgres://") :]
        elif raw.startswith("postgresql://"):
            raw = "postgresql+psycopg://" + raw[len("postgresql://") :]
        return raw

    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "poc")
    user = os.environ.get("DB_USER", "app_user")
    password = os.environ.get("DB_PASSWORD", "")

    # /cloudsql/... の Unix socket 接続は host をクエリで渡す。
    if host.startswith("/"):
        auth = quote_plus(user)
        if password:
            auth = f"{auth}:{quote_plus(password)}"
        return f"postgresql+psycopg://{auth}@/{name}?host={host}"

    auth = quote_plus(user)
    if password:
        auth = f"{auth}:{quote_plus(password)}"
    return f"postgresql+psycopg://{auth}@{host}:{port}/{name}"


# sqlalchemy.url を alembic.ini 経由で渡さない。quote_plus 後の % が ConfigParser の
# 補間構文と衝突するため（cloudsql-migrate 等で Secret Manager のパスワード使用時）。


def run_migrations_offline() -> None:
    context.configure(
        url=_build_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_build_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
