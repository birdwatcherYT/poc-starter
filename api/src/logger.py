"""アプリケーション用ロガー。

- LOG_FORMAT=text（ローカル既定）: 色付き 1 行フォーマットで stdout に出力。
- LOG_FORMAT=json または K_SERVICE が設定されている（Cloud Run）場合:
  Cloud Logging 互換 JSON で stdout に出力する。
- Cloud Run 上では stdout の JSON を自動で Cloud Logging に集約する。

ヘルパー:
- log_request(body, **fields) / log_response(body, **fields) で構造化ログ出力。
- 任意の追加フィールド: logger.info("msg", extra={"extra_fields": {"foo": 1}})
"""

import json
import logging
import os
import sys
from typing import Any

from .trace_context import get_span_id, get_trace_id

_LEVEL_COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
}
_RESET = "\033[0m"
_DIM = "\033[2m"


class CloudLoggingJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        trace_id = get_trace_id()
        if trace_id:
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            payload["logging.googleapis.com/trace"] = (
                f"projects/{project}/traces/{trace_id}" if project else trace_id
            )
            span_id = get_span_id()
            if span_id:
                payload["logging.googleapis.com/spanId"] = span_id

        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


class HumanReadableFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "")
        ts = self.formatTime(record, "%H:%M:%S")
        level = f"{color}{record.levelname:<8}{_RESET}"
        name = f"{_DIM}{record.name}{_RESET}"
        line = f"{ts} {level} {name} {record.getMessage()}"

        trace_id = get_trace_id()
        if trace_id:
            line += f" {_DIM}trace={trace_id[:8]}{_RESET}"

        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict) and extra:
            parts = " ".join(
                f"{k}={json.dumps(v, ensure_ascii=False, default=str)}"
                for k, v in extra.items()
            )
            line += f" {parts}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line


def _is_cloud_logging() -> bool:
    fmt = (os.getenv("LOG_FORMAT") or "").lower()
    if fmt == "json":
        return True
    if fmt == "text":
        return False
    return bool(os.getenv("K_SERVICE"))


def _build_formatter() -> logging.Formatter:
    if _is_cloud_logging():
        return CloudLoggingJsonFormatter()
    return HumanReadableFormatter()


def configure_logging(level: str | None = None) -> None:
    log_level = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_build_formatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "gunicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _to_payload(obj: Any) -> object:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: _to_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_payload(v) for v in obj]
    if isinstance(obj, str | int | float | bool):
        return obj
    return repr(obj)


_logger = logging.getLogger(__name__)


def log_request(body: Any, *, message: str = "request received", **fields: Any) -> None:
    _logger.info(
        message,
        extra={"extra_fields": {"body": _to_payload(body), **fields}},
    )


def log_response(body: Any, *, message: str = "response sent", **fields: Any) -> None:
    _logger.info(
        message,
        extra={"extra_fields": {"body": _to_payload(body), **fields}},
    )
