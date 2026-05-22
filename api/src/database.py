"""PostgreSQL コネクションプールのラッパー（psycopg3）。

DB_HOST の値に応じて 3 通りの接続経路をサポートする:
- localhost（ローカル docker-compose もしくは cloud-sql-proxy 経由）
- /cloudsql/<conn_name>（Cloud Run から Cloud SQL への Unix socket。psycopg がスラッシュ始まりを自動的に socket として扱う）

トランザクション挙動について:
- `pool.connection()` は context 終了時に正常なら commit、例外なら rollback を自動で行う（psycopg3 公式ドキュメント保証）。
- よって `execute()` / `fetch()` で明示的な commit / rollback は不要。
- 複数文を 1 トランザクションにまとめたい場合は `with db.transaction() as conn:` を使う。
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .logger import get_logger

logger = get_logger(__name__)


class Database:
    """PostgreSQL の接続プールと簡易クエリヘルパーをまとめたクラス。

    通常はアプリ起動時に 1 度だけインスタンス化し、`app.state.db` 経由で各ルーター / サービスから使い回す。

    使い方:

    初期化（lifespan で 1 度だけ）:
        db = Database(
            host=os.environ["DB_HOST"],
            port=int(os.environ["DB_PORT"]),
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
        )
        app.state.db = db
        ...
        db.close()  # shutdown 時

    単発の SELECT（dict のリストが返る）:
        rows = db.fetch(
            "SELECT id, name FROM users WHERE active = %(active)s",
            {"active": True},
        )
        for row in rows:
            print(row["id"], row["name"])

    単発の INSERT / UPDATE / DELETE（影響行数を返す）:
        n = db.execute(
            "UPDATE users SET last_login = NOW() WHERE id = %(id)s",
            {"id": user_id},
        )
        assert n == 1

    複数文を 1 トランザクションにまとめる（途中で例外が出れば全体 rollback）:
        with db.transaction() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO pairs ... ")
            cur.execute("INSERT INTO matchings ... ")
            cur.execute("UPDATE users SET ... ")

    生のコネクションを使いたいとき（cursor を細かく制御する場合など）:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("...")
                conn.commit()  # 通常は不要（ブロック終了で自動 commit）
    """

    def __init__(
        self,
        host: str,
        port: int,
        dbname: str,
        user: str,
        password: str = "",
        min_size: int = 1,
        max_size: int = 10,
        connect_timeout: int = 10,
        max_lifetime: int = 1800,
    ) -> None:
        conninfo = psycopg.conninfo.make_conninfo(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=connect_timeout,
        )
        self._pool = ConnectionPool(
            conninfo=conninfo,
            min_size=min_size,
            max_size=max_size,
            max_lifetime=max_lifetime,
            check=ConnectionPool.check_connection,
            open=True,
        )
        logger.info(
            "Database connection pool initialized",
            extra={
                "extra_fields": {
                    "host": host,
                    "dbname": dbname,
                    "min_size": min_size,
                    "max_size": max_size,
                }
            },
        )

    @contextmanager
    def get_connection(self) -> Iterator[psycopg.Connection]:
        """プールから接続を借りる。ブロック終了時に正常なら commit、例外なら rollback。"""
        with self._pool.connection() as conn:
            yield conn

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Connection]:
        """複数文を 1 トランザクションにまとめる。途中で例外が出れば全体が rollback される。"""
        with self._pool.connection() as conn, conn.transaction():
            yield conn

    def execute(self, sql: str, params: tuple | dict | None = None) -> int:
        """SQL を実行して影響行数を返す（INSERT / UPDATE / DELETE 想定）。"""
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def fetch(
        self, sql: str, params: tuple | dict | None = None
    ) -> list[dict[str, Any]]:
        """SELECT を実行して dict のリストを返す。"""
        with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            cur.execute(sql, params)
            return cur.fetchall()

    def close(self) -> None:
        """接続プールを閉じる。lifespan の shutdown で呼ぶ想定。"""
        self._pool.close()
        logger.info("Database connection pool closed")
