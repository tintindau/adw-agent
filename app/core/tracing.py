"""Decorator `@traced(layer)` ghi log mỗi lần gọi service / analytics.

Log gồm: hàm, tham số (đã tóm tắt), thời gian chạy, tóm tắt kết quả, lỗi nếu có.
DataFrame và danh sách dài chỉ ghi kích thước để log không phình to.
"""

import functools
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

import pandas as pd

from app.core.logger import log_event

F = TypeVar("F", bound=Callable[..., Any])

MAX_STRING = 300
MAX_ITEMS = 20


def summarize(value: Any, depth: int = 0) -> Any:
    """Rút gọn giá trị để đưa vào log."""
    if isinstance(value, pd.DataFrame):
        return {"type": "DataFrame", "rows": len(value), "columns": list(value.columns)[:MAX_ITEMS]}
    if isinstance(value, pd.Series):
        return {"type": "Series", "rows": len(value)}
    if isinstance(value, str):
        return value if len(value) <= MAX_STRING else value[:MAX_STRING] + "…"
    if isinstance(value, (list, tuple, set)):
        if len(value) > MAX_ITEMS or depth > 1:
            return {"type": type(value).__name__, "len": len(value)}
        return [summarize(item, depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > MAX_ITEMS or depth > 1:
            return {"type": "dict", "keys": list(value)[:MAX_ITEMS], "len": len(value)}
        return {str(k): summarize(v, depth + 1) for k, v in value.items()}
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return repr(value)[:MAX_STRING]


def traced(layer: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        name = f"{func.__module__.rsplit('.', 1)[-1]}.{func.__qualname__}"
        signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                arguments = dict(signature.bind_partial(*args, **kwargs).arguments)
            except TypeError:
                arguments = {"args": args, "kwargs": kwargs}
            started = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                log_event(
                    layer,
                    level=logging.ERROR,
                    func=name,
                    args=summarize(arguments),
                    status="error",
                    error=f"{type(exc).__name__}: {exc}"[:MAX_STRING],
                    duration_ms=round((time.perf_counter() - started) * 1000, 1),
                )
                raise
            log_event(
                layer,
                func=name,
                args=summarize(arguments),
                status="ok",
                result=summarize(result),
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
