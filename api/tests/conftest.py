"""テスト全体で共有する fixture。

- Testcontainers で PostgreSQL（pgvector 入り）を起動
- Alembic で `database/alembic/versions/` を適用（Python プロセス内で実行、docker 不要）
- `Database` インスタンスとアプリ用 env をテストに提供

ローカルでも GitHub Actions でも追加設定なしに動くよう、Docker ソケットを自動検出する。
"""

import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from testcontainers.core.image import DockerImage
from testcontainers.postgres import PostgresContainer

from src.database import Database

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATABASE_DIR = _REPO_ROOT / "database"
_ALEMBIC_INI = _DATABASE_DIR / "alembic.ini"


def _setup_docker_host() -> None:
    """ローカル開発（Rancher Desktop / Docker Desktop / Colima）と GitHub Actions
    の両方で動くよう DOCKER_HOST を自動検出する。

    既に環境変数が設定されているがソケットが存在しない場合はクリアする。
    """
    docker_host = os.environ.get("DOCKER_HOST")
    if docker_host and docker_host.startswith("unix://"):
        sock = docker_host[len("unix://") :]
        if not os.path.exists(sock):
            del os.environ["DOCKER_HOST"]
            docker_host = None

    if docker_host:
        return

    home = os.path.expanduser("~")
    candidates = [
        f"{home}/.rd/docker.sock",  # Rancher Desktop
        f"{home}/.docker/run/docker.sock",  # Docker Desktop
        f"{home}/.colima/default/docker.sock",  # Colima
        "/var/run/docker.sock",  # Linux / GitHub Actions
    ]
    for sock in candidates:
        if os.path.exists(sock):
            os.environ["DOCKER_HOST"] = f"unix://{sock}"
            return


_setup_docker_host()

# Ryuk（Testcontainers のクリーンアップ用 sidecar）は docker.sock のマウントが必要。
# Rancher Desktop の rd 仮想化など、ホストの docker.sock をコンテナにバインドできない
# 環境では起動に失敗するので無効化する。テスト終了時に PG コンテナを `with` 文で
# 自前で閉じているので Ryuk なしでもリークしない。
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


def _run_migrations(container: PostgresContainer) -> None:
    """Alembic で migrations を適用する。

    Python プロセス内で `alembic upgrade head` 相当を呼ぶ。docker は不要。
    `env.py` は `DB_URL` を最優先で参照するので、ここでは testcontainer の
    接続情報から URL を組んで渡す。
    """
    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(5432))
    db_url = (
        f"postgresql+psycopg://{container.username}:{container.password}"
        f"@{host}:{port}/{container.dbname}"
    )

    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_DATABASE_DIR / "alembic"))
    # env.py がこの env を読む。
    prev = os.environ.get("DB_URL")
    os.environ["DB_URL"] = db_url
    try:
        command.upgrade(cfg, "head")
    finally:
        if prev is None:
            os.environ.pop("DB_URL", None)
        else:
            os.environ["DB_URL"] = prev


@pytest.fixture(scope="session")
def postgres_image() -> Iterator[str]:
    """`database/Dockerfile` をビルドしてテスト用 PostgreSQL イメージを用意する。

    本番と同じ Dockerfile を使うことで、apt で入れた拡張（pgvector など）が
    実環境とテストで同期する。Docker layer cache が効くので 2 回目以降は速い。
    """
    with DockerImage(
        path=str(_DATABASE_DIR),
        tag="poc-starter-postgres:test",
        clean_up=False,  # session スコープなので最後だけ消えれば十分
    ) as image:
        yield str(image)


@pytest.fixture(scope="session")
def postgres_container(postgres_image: str) -> Iterator[PostgresContainer]:
    """`database/Dockerfile` から作った PostgreSQL コンテナを 1 セッション分だけ起動する。"""
    with PostgresContainer(
        image=postgres_image,
        username="testuser",
        password="testpass",
        dbname="testdb",
    ) as container:
        # コンテナ起動直後はまだ accept していないことがある
        time.sleep(2)
        yield container


@pytest.fixture(scope="session")
def db(postgres_container: PostgresContainer) -> Iterator[Database]:
    """migrations 適用済みの Database インスタンスを返す。"""
    host = postgres_container.get_container_host_ip()
    port = int(postgres_container.get_exposed_port(5432))
    dbname = postgres_container.dbname
    user = postgres_container.username
    password = postgres_container.password

    _run_migrations(postgres_container)

    instance = Database(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        pool_size=3,
    )
    try:
        yield instance
    finally:
        instance.close()


@pytest.fixture
def clean_messages(db: Database) -> None:
    """各テストの前に messages テーブルをクリアする。"""
    with db.session() as s:
        s.execute(text("DELETE FROM messages"))


@pytest.fixture
def clean_documents(db: Database) -> None:
    """各テストの前に documents テーブルをクリアする。"""
    with db.session() as s:
        s.execute(text("DELETE FROM documents"))


@pytest.fixture
def app_db_env(
    postgres_container: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FastAPI の lifespan が期待する DB_* 環境変数をテスト用 PG に向ける。"""
    monkeypatch.setenv("DB_HOST", postgres_container.get_container_host_ip())
    monkeypatch.setenv("DB_PORT", str(postgres_container.get_exposed_port(5432)))
    monkeypatch.setenv("DB_NAME", postgres_container.dbname)
    monkeypatch.setenv("DB_USER", postgres_container.username)
    monkeypatch.setenv("DB_PASSWORD", postgres_container.password)
