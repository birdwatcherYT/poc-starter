"""ContextVar + ASGI ミドルウェアによる Trace コンテキストの伝播。

Cloud Run が付与する `X-Cloud-Trace-Context` と W3C `traceparent` から trace_id / span_id を抽出して ContextVar に保存する。
logger が全てのログレコードに trace フィールドを付与できる。
"""

from contextvars import ContextVar

from starlette.types import ASGIApp, Receive, Scope, Send

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)


def get_trace_id() -> str | None:
    return _trace_id.get()


def get_span_id() -> str | None:
    return _span_id.get()


def _parse_traceparent(header: str) -> tuple[str | None, str | None]:
    parts = header.split("-")
    if len(parts) >= 3:
        return parts[1], parts[2]
    return None, None


def _parse_cloud_trace_context(header: str) -> tuple[str | None, str | None]:
    """`X-Cloud-Trace-Context: TRACE_ID/SPAN_ID;o=OPTIONS` をパースする。"""
    trace_part = header.split(";", 1)[0]
    trace_id, sep, span_id = trace_part.partition("/")
    if not sep or not trace_id:
        return None, None
    return trace_id, span_id or None


def _extract_trace(headers: list[tuple[bytes, bytes]]) -> tuple[str | None, str | None]:
    header_map = {name.lower(): value for name, value in headers}

    traceparent = header_map.get(b"traceparent")
    if traceparent:
        trace_id, span_id = _parse_traceparent(traceparent.decode())
        if trace_id:
            return trace_id, span_id

    cloud_trace = header_map.get(b"x-cloud-trace-context")
    if cloud_trace:
        return _parse_cloud_trace_context(cloud_trace.decode())

    return None, None


class TraceContextMiddleware:
    """BaseHTTPMiddleware ではなく pure ASGI で ContextVar を確実に伝播する。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        trace_id, span_id = _extract_trace(scope.get("headers", []))
        tid_token = sid_token = None
        if trace_id:
            tid_token = _trace_id.set(trace_id)
        if span_id:
            sid_token = _span_id.set(span_id)
        try:
            await self.app(scope, receive, send)
        finally:
            if tid_token is not None:
                _trace_id.reset(tid_token)
            if sid_token is not None:
                _span_id.reset(sid_token)


def install(app: ASGIApp) -> None:
    app.add_middleware(TraceContextMiddleware)
