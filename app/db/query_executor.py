import pandas as pd

from app.db.connection import get_pool


class QueryExecutor:

    @staticmethod
    def execute(sql, params=None):

        with get_pool().acquire() as conn:

            return pd.read_sql(
                sql,
                conn,
                params=params
            ).to_dict(
                orient="records"
            )