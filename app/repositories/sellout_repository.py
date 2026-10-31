from app.db.query_executor import QueryExecutor


class SelloutRepository:
    @staticmethod
    def execute(sql: str, params: dict):
        return QueryExecutor.execute(sql, params)
