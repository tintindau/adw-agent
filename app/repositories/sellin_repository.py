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


class SellinRepository:
    @staticmethod
    def get_by_month(filters: dict[str, str | None]):
        sql_file = (
            Path(__file__).resolve().parents[1]
            / "sql"
            / "sellin"
            / "get_by_month.sql"
        )
        sql = sql_file.read_text(encoding="utf-8")
        return QueryExecutor.execute(sql, filters)