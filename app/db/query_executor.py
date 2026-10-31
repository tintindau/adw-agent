import pandas as pd

from app.db.connection import get_pool


class QueryExecutor:

    @staticmethod
    def execute(sql, params=None):

        with get_pool().acquire() as conn:

            data = pd.read_sql(
                sql,
                conn,
                params=params
            )
            data = data.astype(object).where(pd.notna(data), None)

            return data.to_dict(
                orient="records"
            )