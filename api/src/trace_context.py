"""ContextVar + ASGI ミドルウェアによる Trace コンテキストの伝播。

各リクエストの W3C `traceparent` ヘッダから trace_id / span_id を抽出して ContextVar に保存する。
これにより logger が全てのログレコードに trace_id を付与できる。
"""

from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

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


class TraceContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        traceparent = request.headers.get("traceparent")
        tid_token = sid_token = None
        if traceparent:
            tid, sid = _parse_traceparent(traceparent)
            if tid:
                tid_token = _trace_id.set(tid)
            if sid:
                sid_token = _span_id.set(sid)
        try:
            return await call_next(request)
        finally:
            if tid_token is not None:
                _trace_id.reset(tid_token)
            if sid_token is not None:
                _span_id.reset(sid_token)


def install(app: ASGIApp) -> None:
    app.add_middleware(TraceContextMiddleware)
