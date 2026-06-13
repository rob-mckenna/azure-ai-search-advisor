"""Logging helpers for the API service."""

from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_RESERVED_LOG_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
}


def get_correlation_id() -> str | None:
    """Return the current request correlation identifier, if any."""

    return _correlation_id.get()


def set_correlation_id(value: str | None) -> Token[str | None]:
    """Store a correlation identifier in request-local context."""

    return _correlation_id.set(value)


def reset_correlation_id(token: Token[str | None]) -> None:
    """Reset the request-local correlation identifier."""

    _correlation_id.reset(token)


class CorrelationIdFilter(logging.Filter):
    """Inject the active correlation ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id") or record.correlation_id is None:
            record.correlation_id = get_correlation_id()
        return True


def _record_extras(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RESERVED_LOG_RECORD_FIELDS and not key.startswith("_")
    }


class JsonFormatter(logging.Formatter):
    """Serialize logs as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
            "module": record.module,
        }
        payload.update(_record_extras(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    """Format logs for local development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, timezone.utc).isoformat()
        correlation_id = getattr(record, "correlation_id", None) or "-"
        extras = " ".join(
            f"{key}={value}"
            for key, value in sorted(_record_extras(record).items())
        )
        message = (
            f"{timestamp} {record.levelname} [{record.module}] "
            f"[correlation_id={correlation_id}] {record.getMessage()}"
        )
        if extras:
            message = f"{message} {extras}"
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return message


def configure_logging() -> None:
    """Configure application logging from environment variables."""

    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_format = os.environ.get("LOG_FORMAT", "text").lower()

    handler = logging.StreamHandler()
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(JsonFormatter() if log_format == "json" else TextFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

