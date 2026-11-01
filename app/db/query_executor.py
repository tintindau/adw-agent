import logging
import re
import time

import pandas as pd

from app.analytics.frames import to_records
from app.core.config import settings
from app.core.logger import log_event
from app.core.tracing import summarize
from app.db.cache import QueryCache, make_key
from app.db.connection import get_pool

query_cache = QueryCache(
    ttl_seconds=settings.query_cache_ttl_seconds,
    max_entries=settings.query_cache_max_entries,
)


def compact_sql(sql: str) -> str:
    """Bỏ comment và gộp khoảng trắng để câu SQL nằm trên một dòng log."""
    without_comments = re.sub(r"--[^\n]*", "", sql)
    return re.sub(r"\s+", " ", without_comments).strip()


def _sql_fields(sql, params, key) -> dict:
    fields = {"query_key": key[:12] if key else None}
    if settings.log_sql:
        fields["sql"] = compact_sql(sql)
        fields["params"] = summarize(params)
    return fields


class QueryExecutor:

    @staticmethod
    def execute_df(sql, params=None, use_cache: bool = True) -> pd.DataFrame:
        """Chạy SELECT và trả DataFrame (tên cột giữ nguyên như Oracle trả về).

        Kết quả được cache theo SQL + params (xem app/db/cache.py).
        Truyền use_cache=False cho truy vấn cần dữ liệu tức thời.
        Mỗi lần gọi ghi một sự kiện log "sql" (câu lệnh, params, số dòng, thời gian, cache).
        """
        cacheable = use_cache and settings.query_cache_enabled
        key = make_key(sql, params) if cacheable else None

        if cacheable:
            cached = query_cache.get(key)
            if cached is not None:
                log_event("sql", cache="hit", rows=len(cached), duration_ms=0, **_sql_fields(sql, params, key))
                return cached

        started = time.perf_counter()
        try:
            with get_pool().acquire() as conn:
                df = pd.read_sql(sql, conn, params=params)
        except Exception as exc:
            log_event(
                "sql",
                level=logging.ERROR,
                cache="miss" if cacheable else "off",
                status="error",
                error=f"{type(exc).__name__}: {exc}"[:500],
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                **_sql_fields(sql, params, key),
            )
            raise

        log_event(
            "sql",
            cache="miss" if cacheable else "off",
            status="ok",
            rows=len(df),
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
            **_sql_fields(sql, params, key),
        )
        if cacheable:
            query_cache.set(key, df)
        return df

    @staticmethod
    def execute(sql, params=None, use_cache: bool = True) -> list[dict]:
        """Chạy SELECT và trả list[dict], NaN đổi thành None."""
        return to_records(QueryExecutor.execute_df(sql, params, use_cache=use_cache))
