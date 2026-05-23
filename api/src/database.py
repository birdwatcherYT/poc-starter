"""PostgreSQL アクセスのラッパー（SQLAlchemy 一本化）。

DB_HOST の値に応じて 2 通りの接続経路をサポートする:
- 通常のホスト名 / IP（ローカル docker-compose もしくは cloud-sql-proxy 経由）
- `/cloudsql/<conn_name>` のような Unix socket パス（Cloud Run から Cloud SQL への直接接続。psycopg は `/` 始まりの host を自動的に socket として扱う）

トランザクション挙動:
- `db.session()` は context 終了時に正常なら commit、例外なら rollback を自動で行う
- 生 SQL を叩きたいときは `session.execute(text("..."))` を使う
"""

from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .logger import get_logger

logger = get_logger(__name__)


def _build_sqlalchemy_url(
    host: str, port: int, dbname: str, user: str, password: str
) -> str:
    """接続情報から SQLAlchemy URL を組む。

    Unix socket (host が `/` で始まる) も Cloud SQL の Unix socket も
    `host=` クエリで渡せば psycopg ドライバが解釈する。
    """
    auth = quote_plus(user)
    if password:
        auth = f"{auth}:{quote_plus(password)}"
    if host.startswith("/"):
        return f"postgresql+psycopg://{auth}@/{dbname}?host={host}"
    return f"postgresql+psycopg://{auth}@{host}:{port}/{dbname}"


class Database:
    """SQLAlchemy Engine + sessionmaker のラッパー。

    通常はアプリ起動時に 1 度だけインスタンス化し、`app.state.db` 経由で各ルーター・サービスから使い回す。

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

    ORM クエリ（`schema.models.Message` などを使う）:
        from sqlalchemy import select
        from schema.models import Message

        with db.session() as s:
            rows = s.scalars(select(Message).limit(10)).all()
            for r in rows:
                print(r.id, r.message)

    ORM での insert（id / created_at は flush 後に DB から返って詰まる）:
        with db.session() as s:
            msg = Message(message="hi")
            s.add(msg)
            s.flush()
            print(msg.id)
        # ブロック終了で commit、例外なら rollback

    生 SQL を叩きたいとき:
        from sqlalchemy import text

        with db.session() as s:
            rows = s.execute(
                text("SELECT id, message FROM messages WHERE author = :a"),
                {"a": "alice"},
            ).mappings().all()
            for r in rows:
                print(r["id"], r["message"])
    """

    def __init__(
        self,
        host: str,
        port: int,
        dbname: str,
        user: str,
        password: str = "",
        pool_size: int = 10,
        max_overflow: int = 0,
        pool_recycle: int = 1800,
    ) -> None:
        # pool_pre_ping=True: 借りる時に SELECT 1 で死活確認（Cloud SQL のアイドル切断対策）
        # pool_recycle: 一定秒数経った接続は破棄して張り直す
        self._engine: Engine = create_engine(
            _build_sqlalchemy_url(host, port, dbname, user, password),
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=pool_recycle,
            future=True,
        )
        self._session_factory = sessionmaker(
            bind=self._engine, expire_on_commit=False, class_=Session
        )
        logger.info(
            "Database engine initialized",
            extra={
                "extra_fields": {
                    "host": host,
                    "dbname": dbname,
                    "pool_size": pool_size,
                    "max_overflow": max_overflow,
                }
            },
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        """SQLAlchemy の Session を借りる。

        正常終了時に commit、例外時は rollback、いずれにせよ close。
        """
        sess = self._session_factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    def close(self) -> None:
        """Engine を破棄してプール内のコネクションを全て閉じる。"""
        self._engine.dispose()
        logger.info("Database engine disposed")
