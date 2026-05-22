"""src/trace_context.py の振る舞いを担保する test。

TraceContextMiddleware が HTTP ヘッダーから trace_id / span_id を読み取り、
リクエスト処理中だけ ContextVar に載せることを検証する。
"""

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.trace_context import get_span_id, get_trace_id, install


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
            {
                "traceparent": (
                    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
                )
            },
            "4bf92f3577b34da6a3ce929d0e0e4736",
            "00f067aa0ba902b7",
        ),
        (
            {"X-Cloud-Trace-Context": "invalid"},
            None,
            None,
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
    - traceparent: W3C Trace Context 形式
    - 不正なヘッダー: trace / span は None のまま（アプリは通常どおり動く）
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
