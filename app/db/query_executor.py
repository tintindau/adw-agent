import pandas as pd

from app.analytics.frames import to_records
from app.db.connection import get_pool


class QueryExecutor:

    @staticmethod
    def execute_df(sql, params=None) -> pd.DataFrame:
        """Chạy SELECT và trả DataFrame (tên cột giữ nguyên như Oracle trả về)."""
        with get_pool().acquire() as conn:
            return pd.read_sql(sql, conn, params=params)

    @staticmethod
    def execute(sql, params=None) -> list[dict]:
        """Chạy SELECT và trả list[dict], NaN đổi thành None."""
        return to_records(QueryExecutor.execute_df(sql, params))
