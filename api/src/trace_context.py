"""ContextVar + ASGI ミドルウェアによる Trace コンテキストの伝播。

Cloud Run の `X-Cloud-Trace-Context` / W3C `traceparent` から trace を読み取り、
ContextVar に載せる。ヘッダーが無ければ trace_id を採番し、レスポンスにも付け返す。

pure ASGI のみで実装する。BaseHTTPMiddleware は ContextVar の伝播が壊れやすく、
StreamingResponse 等をバッファする副作用もあるため使わない。
レスポンスヘッダーは ASGI の send ラップで `http.response.start` に付与する。
"""

import secrets
from contextvars import ContextVar, Token

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_CLOUD_TRACE = b"x-cloud-trace-context"

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)


def get_trace_id() -> str | None:
    return _trace_id.get()


def get_span_id() -> str | None:
    return _span_id.get()


def _header(headers: list[tuple[bytes, bytes]], name: bytes) -> str | None:
    for key, value in headers:
        if key.lower() == name:
            return value.decode()
    return None


def _parse_traceparent(header: str) -> tuple[str | None, str | None]:
    parts = header.split("-")
    if len(parts) >= 3:
        return parts[1], parts[2] or None
    return None, None


def _parse_cloud_trace_context(header: str) -> tuple[str | None, str | None]:
    head = header.split(";", 1)[0]
    trace_id, sep, span_id = head.partition("/")
    if not trace_id:
        return None, None
    if not sep:
        return trace_id, None
    return trace_id, span_id or None


def _extract_trace(headers: list[tuple[bytes, bytes]]) -> tuple[str | None, str | None]:
    # W3C traceparent を優先し、無ければ Cloud Run の X-Cloud-Trace-Context を見る。
    if value := _header(headers, b"traceparent"):
        trace_id, span_id = _parse_traceparent(value)
        if trace_id:
            return trace_id, span_id

    if value := _header(headers, _CLOUD_TRACE):
        return _parse_cloud_trace_context(value)

    return None, None


def _generate_trace_id() -> str:
    return secrets.token_hex(16)


def _cloud_trace_header(trace_id: str, span_id: str | None) -> bytes:
    if span_id:
        return f"{trace_id}/{span_id}".encode()
    return trace_id.encode()


def _bind(
    trace_id: str, span_id: str | None
) -> tuple[Token[str | None], Token[str | None]]:
    return _trace_id.set(trace_id), _span_id.set(span_id)


def _unbind(tokens: tuple[Token[str | None], Token[str | None]]) -> None:
    _trace_id.reset(tokens[0])
    _span_id.reset(tokens[1])


def _send_with_response_header(send: Send, name: bytes, value: bytes) -> Send:
    """ASGI レベルでレスポンスヘッダーを差し替え付与する send ラッパー。"""

    async def wrapper(message: Message) -> None:
        if message["type"] == "http.response.start":
            headers = [
                (key, val)
                for key, val in message.get("headers", [])
                if key.lower() != name
            ]
            message = {**message, "headers": [*headers, (name, value)]}
        await send(message)

    return wrapper


class TraceContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        trace_id, span_id = _extract_trace(scope.get("headers", []))
        if not trace_id:
            trace_id = _generate_trace_id()

        tokens = _bind(trace_id, span_id)
        try:
            await self.app(
                scope,
                receive,
                _send_with_response_header(
                    send, _CLOUD_TRACE, _cloud_trace_header(trace_id, span_id)
                ),
            )
        finally:
            _unbind(tokens)


def install(app: ASGIApp) -> None:
    app.add_middleware(TraceContextMiddleware)
