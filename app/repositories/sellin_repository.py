from pathlib import Path

from app.db.query_executor import QueryExecutor

SQL_DIR = Path(
    "app/sql/revenue"
)


class RevenueRepository:

    @staticmethod
    def sales_by_customer(period):

        sql = (
            SQL_DIR /
            "selin_by_customer_quer.sql"
        ).read_text()

        return QueryExecutor.execute(
            sql,
            {
                "period": period
            }
        )