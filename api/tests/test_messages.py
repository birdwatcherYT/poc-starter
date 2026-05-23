"""TestClient + Testcontainers の PG で /messages の挙動を検証する。"""

from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_db_env: None, clean_messages: None) -> Iterator[TestClient]:
    """DB 環境変数設定・テーブルクリア後に FastAPI アプリの TestClient を返す。"""
    from api import app

    with TestClient(app) as c:
        yield c


def test_create_message_saves_and_returns_row(client: TestClient) -> None:
    """正常系: POST した message / author が DB に保存され、id と created_at 付きで返る。"""
    res = client.post(
        "/messages",
        json={"message": "hello", "author": "tester"},
    )
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["id"], int)
    assert body["message"] == "hello"
    assert body["author"] == "tester"
    datetime.fromisoformat(body["created_at"])


def test_create_message_accepts_null_author(client: TestClient) -> None:
    """author は optional: 省略すれば null として保存される。"""
    res = client.post("/messages", json={"message": "no author"})
    assert res.status_code == 200
    assert res.json()["author"] is None


def test_create_message_rejects_empty_message(client: TestClient) -> None:
    """バリデーション: 空文字 message は Pydantic の min_length=1 で 422 になる。"""
    res = client.post("/messages", json={"message": ""})
    assert res.status_code == 422


def test_list_messages_returns_recent_first(client: TestClient) -> None:
    """GET /messages: 保存したメッセージが新しい順で返る（ORM 経由）。"""
    client.post("/messages", json={"message": "first", "author": "a"})
    client.post("/messages", json={"message": "second", "author": "b"})
    client.post("/messages", json={"message": "third", "author": "c"})

    res = client.get("/messages")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    messages = [item["message"] for item in body["items"]]
    assert messages == ["third", "second", "first"]


def test_list_messages_respects_limit(client: TestClient) -> None:
    """limit クエリで件数が制限される。"""
    for i in range(5):
        client.post("/messages", json={"message": f"m{i}"})

    res = client.get("/messages?limit=2")
    assert res.status_code == 200
    assert res.json()["total"] == 2
