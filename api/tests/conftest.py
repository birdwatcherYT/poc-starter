"""テスト全体で共有する fixture。

- Testcontainers で PostgreSQL（pgvector 入り）を起動
- golang-migrate を docker run して `database/migrations` を適用
- `Database` インスタンスとアプリ用 env をテストに提供

ローカルでも GitHub Actions でも追加設定なしに動くよう、Docker ソケットを自動検出する。
"""

import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from testcontainers.core.image import DockerImage
from testcontainers.postgres import PostgresContainer

from src.database import Database

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATABASE_DIR = _REPO_ROOT / "database"
_MIGRATIONS_DIR = _DATABASE_DIR / "migrations"


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


def _run_migrations(
    container: PostgresContainer,
) -> None:
    """golang-migrate コンテナで migrations/ を適用する。

    Testcontainers の PG コンテナが居るネットワークに migrate コンテナを join
    させ、コンテナ間で直接通信する。`--network host` は macOS / Linux で挙動が
    違うので使わない。これでローカル（macOS / Rancher / Docker Desktop）と
    GitHub Actions（Linux）の両方で同じく動く。
    """
    pg_id = container.get_wrapped_container().id
    pg_inspect = container.get_docker_client().client.api.inspect_container(pg_id)
    pg_networks = pg_inspect["NetworkSettings"]["Networks"]
    # Testcontainers は通常 "bridge" に置く。複数あれば最初を使う。
    network_name, network_info = next(iter(pg_networks.items()))
    # bridge は DNS 解決しないので IP アドレスを直接渡す（user-defined network なら
    # コンテナ名で名前解決できるが、ここでは bridge デフォルト前提で両対応する）
    pg_ip = network_info["IPAddress"]

    db_url = (
        f"postgres://{container.username}:{container.password}"
        f"@{pg_ip}:5432/{container.dbname}?sslmode=disable"
    )
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        network_name,
        "-v",
        f"{_MIGRATIONS_DIR}:/migrations",
        "migrate/migrate:v4.17.0",
        "-path=/migrations",
        f"-database={db_url}",
        "up",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"migrate に失敗しました (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


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
        min_size=1,
        max_size=3,
    )
    try:
        yield instance
    finally:
        instance.close()


@pytest.fixture
def clean_example_messages(db: Database) -> None:
    """各テストの前に example_messages テーブルをクリアする。"""
    db.execute("DELETE FROM example_messages")


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
