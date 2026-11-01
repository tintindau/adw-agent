import time

import pandas as pd

from app.analytics.frames import to_records
from app.core.config import settings
from app.core.logger import get_logger
from app.db.cache import QueryCache, make_key
from app.db.connection import get_pool

logger = get_logger(__name__)

query_cache = QueryCache(
    ttl_seconds=settings.query_cache_ttl_seconds,
    max_entries=settings.query_cache_max_entries,
)


class QueryExecutor:

    @staticmethod
    def execute_df(sql, params=None, use_cache: bool = True) -> pd.DataFrame:
        """Chạy SELECT và trả DataFrame (tên cột giữ nguyên như Oracle trả về).

        Kết quả được cache theo SQL + params (xem app/db/cache.py).
        Truyền use_cache=False cho truy vấn cần dữ liệu tức thời.
        """
        cacheable = use_cache and settings.query_cache_enabled
        key = make_key(sql, params) if cacheable else None

        if cacheable:
            cached = query_cache.get(key)
            if cached is not None:
                logger.info("query cache hit key=%s rows=%d", key[:12], len(cached))
                return cached

        started = time.perf_counter()
        with get_pool().acquire() as conn:
            df = pd.read_sql(sql, conn, params=params)
        logger.info(
            "query executed key=%s rows=%d duration_ms=%d",
            key[:12] if key else "-",
            len(df),
            (time.perf_counter() - started) * 1000,
        )

        if cacheable:
            query_cache.set(key, df)
        return df

    @staticmethod
    def execute(sql, params=None, use_cache: bool = True) -> list[dict]:
        """Chạy SELECT và trả list[dict], NaN đổi thành None."""
        return to_records(QueryExecutor.execute_df(sql, params, use_cache=use_cache))
