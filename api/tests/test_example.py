"""TestClient + Testcontainers の PG で /example/echo の挙動を検証する。"""

from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_db_env: None, clean_example_messages: None) -> Iterator[TestClient]:
    from api import app

    with TestClient(app) as c:
        yield c


def test_echo_saves_and_returns_row(client: TestClient) -> None:
    """正常系: POST した message / author が DB に保存され、id と created_at 付きで返る。"""
    res = client.post(
        "/example/echo",
        json={"message": "hello", "author": "tester"},
    )
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["id"], int)
    assert body["message"] == "hello"
    assert body["author"] == "tester"
    datetime.fromisoformat(body["created_at"])


def test_echo_accepts_null_author(client: TestClient) -> None:
    """author は optional: 省略すれば null として保存される。"""
    res = client.post("/example/echo", json={"message": "no author"})
    assert res.status_code == 200
    assert res.json()["author"] is None


def test_echo_rejects_empty_message(client: TestClient) -> None:
    """バリデーション: 空文字 message は Pydantic の min_length=1 で 422 になる。"""
    res = client.post("/example/echo", json={"message": ""})
    assert res.status_code == 422
