"""Logging JSON có kèm ngữ cảnh request.

- Mọi dòng log tự gắn request_id, user, question của request hiện tại.
- `log_event()` ghi sự kiện audit (logger `naw.audit`): request, service, analytics, sql, response.
- `setup_logging()` gọi một lần trong app/main.py: ghi ra stdout và file tách theo ngày + user:

      logs/2026-11-01/an@kangaroo.vn.log
      logs/2026-11-01/_anonymous.log   (request không có thông tin user)
      logs/2026-11-01/_system.log      (log ngoài request: khởi động, lỗi nền…)

  Ngày tính theo LOG_TIMEZONE. Thư mục ngày cũ hơn LOG_RETENTION_DAYS tự xoá.
"""

import json
import logging
import re
import shutil
import sys
import threading
from datetime import date, datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.core.request_context import get_context

AUDIT_LOGGER_NAME = "naw.audit"
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
SYSTEM_LOG_NAME = "_system"
ANONYMOUS_LOG_NAME = "_anonymous"
_CONFIGURED_MARKER = "_naw_configured"
_DATE_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.ctx = get_context()
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, tz: tzinfo | None = None):
        super().__init__()
        self.tz = tz or ZoneInfo(DEFAULT_TIMEZONE)

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=self.tz).isoformat(timespec="milliseconds"),
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


def safe_file_name(value: str) -> str:
    """Tên file an toàn trên Windows/Linux, vd 'An Nguyen' → 'An_Nguyen'."""
    cleaned = re.sub(r"[^A-Za-z0-9@._-]+", "_", value.strip()).strip("._")
    return cleaned[:100] or ANONYMOUS_LOG_NAME


class UserDailyFileHandler(logging.Handler):
    """Ghi mỗi dòng log vào logs/<YYYY-MM-DD>/<user>.log.

    User lấy từ request context (email → id → name). Mở/đóng file mỗi lần ghi
    nên không giữ file handle, an toàn khi xoá/chép file log đang chạy.
    """

    def __init__(self, log_dir: str | Path, tz: tzinfo | None = None, retention_days: int = 90):
        super().__init__()
        self.log_dir = Path(log_dir)
        self.tz = tz or ZoneInfo(DEFAULT_TIMEZONE)
        self.retention_days = retention_days
        self._write_lock = threading.Lock()
        self._last_cleanup: date | None = None

    def user_key(self, record: logging.LogRecord) -> str:
        ctx = getattr(record, "ctx", None) or {}
        if not ctx.get("request_id"):
            return SYSTEM_LOG_NAME
        user = ctx.get("user_email") or ctx.get("user_id") or ctx.get("user_name")
        return safe_file_name(user) if user else ANONYMOUS_LOG_NAME

    def path_for(self, record: logging.LogRecord) -> Path:
        day = datetime.fromtimestamp(record.created, tz=self.tz).date()
        return self.log_dir / day.isoformat() / f"{self.user_key(record)}.log"

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
            path = self.path_for(record)
            with self._write_lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                self._cleanup_once_per_day(datetime.fromtimestamp(record.created, tz=self.tz).date())
        except Exception:
            self.handleError(record)

    def _cleanup_once_per_day(self, today: date) -> None:
        if self.retention_days <= 0 or self._last_cleanup == today:
            return
        self._last_cleanup = today
        self.cleanup(today)

    def cleanup(self, today: date) -> list[str]:
        """Xoá thư mục ngày cũ hơn retention_days. Trả về tên các thư mục đã xoá."""
        cutoff = today - timedelta(days=self.retention_days)
        removed = []
        if not self.log_dir.exists():
            return removed
        for child in self.log_dir.iterdir():
            if not (child.is_dir() and _DATE_DIR_PATTERN.match(child.name)):
                continue
            if date.fromisoformat(child.name) < cutoff:
                shutil.rmtree(child, ignore_errors=True)
                removed.append(child.name)
        return removed


def setup_logging(
    level: str = "INFO",
    log_dir: str | None = "logs",
    json_format: bool = True,
    timezone_name: str = DEFAULT_TIMEZONE,
    retention_days: int = 90,
) -> None:
    root = logging.getLogger()
    if getattr(root, _CONFIGURED_MARKER, False):
        return

    tz = ZoneInfo(timezone_name)
    formatter: logging.Formatter = (
        JsonFormatter(tz) if json_format else TextFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_dir:
        handlers.append(UserDailyFileHandler(log_dir, tz=tz, retention_days=retention_days))

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
