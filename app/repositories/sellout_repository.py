import pandas as pd

from app.db.query_executor import QueryExecutor


class SelloutRepository:
    @staticmethod
    def execute(sql: str, params: dict):
        return QueryExecutor.execute(sql, params)

    @staticmethod
    def execute_df(sql: str, params: dict) -> pd.DataFrame:
        return QueryExecutor.execute_df(sql, params)
