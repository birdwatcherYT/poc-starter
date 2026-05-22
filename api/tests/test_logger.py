"""src/logger.py の振る舞いを担保する unit / integration test。

- `_to_payload`: 構造化ログ用に Pydantic モデルを JSON 安全な dict に変換する
- `log_request`: Cloud Run の trace ヘッダーが StructuredLogHandler の出力に載る
"""

import json
import logging
from datetime import UTC, datetime
from io import StringIO

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.example.schema import EchoRequest, EchoResponse
from src.logger import _to_payload, configure_logging, log_request
from src.trace_context import install


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (
            EchoRequest(message="hello", author="alice"),
            {"message": "hello", "author": "alice"},
        ),
        (
            EchoResponse(
                id=1,
                message="hello",
                author="alice",
                created_at=datetime(2026, 5, 22, 20, 22, 23, tzinfo=UTC),
            ),
            {
                "id": 1,
                "message": "hello",
                "author": "alice",
                "created_at": "2026-05-22T20:22:23Z",
            },
        ),
    ],
)
def test_to_payload_is_json_serializable_for_request_and_response(
    model: EchoRequest | EchoResponse,
    expected: dict[str, object],
) -> None:
    """log_request / log_response が body をログに載せる前に JSON 化できること。

    EchoRequest（文字列のみ）と EchoResponse（datetime 含む）の両方で、
    `json.dumps` 可能な dict になることを確認する。datetime は ISO 8601 文字列になる。
    """
    payload = _to_payload(model)

    json.dumps(payload)
    assert payload == expected


def test_log_request_emits_trace_from_cloud_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud Run の X-Cloud-Trace-Context が log_request の JSON ログに載ること。

    ミドルウェアで ContextVar に trace を入れ、StructuredLogHandler 経由で
    `logging.googleapis.com/trace` / `spanId` が出力される end-to-end を検証する。
    """
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

    stream = StringIO()
    configure_logging()
    logging.getLogger().handlers[0].stream = stream

    async def endpoint(request: Request) -> PlainTextResponse:
        log_request({"message": "hello"}, endpoint="/")
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", endpoint)])
    install(app)
    client = TestClient(app)
    client.get("/", headers={"X-Cloud-Trace-Context": "abc123/456;o=1"})

    request_log = next(
        line for line in stream.getvalue().splitlines() if "request received" in line
    )
    payload = json.loads(request_log)
    assert payload["logging.googleapis.com/trace"] == (
        "projects/test-project/traces/abc123"
    )
    assert payload["logging.googleapis.com/spanId"] == "456"
