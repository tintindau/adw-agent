"""Logging JSON có kèm ngữ cảnh request.

- Mọi dòng log tự gắn request_id, user, question của request hiện tại.
- `log_event()` ghi sự kiện audit (logger `naw.audit`): request, service, analytics, sql, response.
- `setup_logging()` gọi một lần trong app/main.py: ghi ra stdout và file xoay vòng trong LOG_DIR.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.request_context import get_context

AUDIT_LOGGER_NAME = "naw.audit"
LOG_FILE_NAME = "naw-agent.log"
_CONFIGURED_MARKER = "_naw_configured"


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.ctx = get_context()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **getattr(record, "ctx", {}),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            payload["traceback"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra = {**getattr(record, "ctx", {}), **getattr(record, "fields", {})}
        extra.pop("event", None)
        if extra:
            base += " " + json.dumps(extra, ensure_ascii=False, default=str)
        return base


def setup_logging(level: str = "INFO", log_dir: str | None = "logs", json_format: bool = True) -> None:
    root = logging.getLogger()
    if getattr(root, _CONFIGURED_MARKER, False):
        return

    formatter: logging.Formatter = (
        JsonFormatter() if json_format else TextFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                Path(log_dir) / LOG_FILE_NAME,
                maxBytes=20 * 1024 * 1024,
                backupCount=10,
                encoding="utf-8",
            )
        )

    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(ContextFilter())
        root.addHandler(handler)
    root.setLevel(level.upper())
    setattr(root, _CONFIGURED_MARKER, True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(event: str, level: int = logging.INFO, exc_info: bool = False, **fields: Any) -> None:
    """Ghi một sự kiện audit, vd log_event("sql", sql=..., rows=10)."""
    logging.getLogger(AUDIT_LOGGER_NAME).log(
        level,
        event,
        exc_info=exc_info,
        extra={"fields": {"event": event, **fields}},
    )
