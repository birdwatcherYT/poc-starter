"""TestClient + Testcontainers の PG で /documents の挙動を検証する。

pgvector を実際に使った保存と類似検索が動くことを確認する。embedding はダミー実装だが、同じ入力なら同じベクトルが返るので類似検索のテストは決定的に書ける。
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_db_env: None, clean_documents: None) -> Iterator[TestClient]:
    from api import app

    with TestClient(app) as c:
        yield c


def test_create_document_returns_saved_row(client: TestClient) -> None:
    """正常系: title / content が保存され、id と created_at 付きで返る。embedding はレスポンスに含めない（重いため）。"""
    res = client.post(
        "/documents",
        json={"title": "猫の生態", "content": "猫は夜行性の傾向がある。"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert isinstance(body["id"], int)
    assert body["title"] == "猫の生態"
    assert body["content"] == "猫は夜行性の傾向がある。"
    assert "embedding" not in body


def test_similar_search_returns_exact_match_first(client: TestClient) -> None:
    """同じ文字列を入れたドキュメントは距離 0 で先頭に返る（ダミー埋め込みは決定的なので確実）。"""
    client.post(
        "/documents",
        json={"title": "犬", "content": "犬は忠実な動物だ。"},
    )
    client.post(
        "/documents",
        json={"title": "猫", "content": "猫は気まぐれな動物だ。"},
    )

    # 「猫」ドキュメントと同じ title + content をクエリにすれば距離 0 になるはず。
    res = client.get("/documents/similar", params={"q": "猫\n猫は気まぐれな動物だ。"})
    assert res.status_code == 200
    body = res.json()
    assert body["items"][0]["title"] == "猫"
    assert body["items"][0]["distance"] == pytest.approx(0.0, abs=1e-6)


def test_similar_search_respects_limit(client: TestClient) -> None:
    for i in range(5):
        client.post(
            "/documents",
            json={"title": f"t{i}", "content": f"content {i}"},
        )

    res = client.get("/documents/similar", params={"q": "anything", "limit": 2})
    assert res.status_code == 200
    assert len(res.json()["items"]) == 2
