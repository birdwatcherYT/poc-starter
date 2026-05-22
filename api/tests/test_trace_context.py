"""src/trace_context.py の振る舞いを担保する test。

TraceContextMiddleware が HTTP ヘッダーから trace_id / span_id を読み取り、
リクエスト処理中だけ ContextVar に載せることを検証する。
"""

import re

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.trace_context import get_span_id, get_trace_id, install

_TRACE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@pytest.mark.parametrize(
    ("headers", "expected_trace_id", "expected_span_id"),
    [
        (
            {"X-Cloud-Trace-Context": "105445aa7843bc8bf206b120001000/1;o=1"},
            "105445aa7843bc8bf206b120001000",
            "1",
        ),
        (
            {"X-Cloud-Trace-Context": "abc123/456"},
            "abc123",
            "456",
        ),
        (
            {"X-Cloud-Trace-Context": "abc123"},
            "abc123",
            None,
        ),
        (
            {
                "traceparent": (
                    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
                )
            },
            "4bf92f3577b34da6a3ce929d0e0e4736",
            "00f067aa0ba902b7",
        ),
    ],
)
def test_middleware_propagates_trace_from_headers(
    headers: dict[str, str],
    expected_trace_id: str | None,
    expected_span_id: str | None,
) -> None:
    """リクエストヘッダーから trace / span が ContextVar に伝播すること。

    - X-Cloud-Trace-Context: Cloud Run が付与する形式（`;o=` 付きも可）
    - trace_id のみ（`/` 無し）も span 無しで受け付ける
    - traceparent: W3C Trace Context 形式
    """
    seen: list[tuple[str | None, str | None]] = []

    async def endpoint(request: Request) -> PlainTextResponse:
        seen.append((get_trace_id(), get_span_id()))
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", endpoint)])
    install(app)
    client = TestClient(app)

    res = client.get("/", headers=headers)

    assert res.status_code == 200
    assert seen == [(expected_trace_id, expected_span_id)]


def test_middleware_generates_trace_id_when_header_missing() -> None:
    """ヘッダーが無いリクエストには 32 桁 hex の trace_id を採番すること。"""
    seen: list[str | None] = []

    async def endpoint(request: Request) -> PlainTextResponse:
        seen.append(get_trace_id())
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", endpoint)])
    install(app)
    client = TestClient(app)

    res = client.get("/")

    assert res.status_code == 200
    assert len(seen) == 1
    assert seen[0] is not None
    assert _TRACE_ID_PATTERN.fullmatch(seen[0])


def test_middleware_echoes_trace_on_response() -> None:
    """レスポンスに X-Cloud-Trace-Context を付与して下流へ伝搬できること。"""
    app = Starlette(routes=[Route("/", lambda r: PlainTextResponse("ok"))])
    install(app)
    client = TestClient(app)

    res = client.get("/", headers={"X-Cloud-Trace-Context": "abc123/456;o=1"})

    assert res.status_code == 200
    assert res.headers["X-Cloud-Trace-Context"] == "abc123/456"


def test_middleware_echoes_generated_trace_on_response() -> None:
    """採番した trace_id もレスポンスヘッダーに載ること。"""
    trace_ids: list[str] = []

    async def endpoint(request: Request) -> PlainTextResponse:
        trace_id = get_trace_id()
        assert trace_id is not None
        trace_ids.append(trace_id)
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", endpoint)])
    install(app)
    client = TestClient(app)

    res = client.get("/")

    assert res.status_code == 200
    assert res.headers["X-Cloud-Trace-Context"] == trace_ids[0]
