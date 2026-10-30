from pathlib import Path

from app.db.query_executor import QueryExecutor

SQL_FILE = (
	Path(__file__).resolve().parents[1]
	/ "sql"
	/ "sellout"
	/ "get_sellout.sql"
)


class SelloutRepository:
	@staticmethod
	def get_sellout(start_date: str, end_date: str):
		sql = SQL_FILE.read_text(encoding="utf-8")
		return QueryExecutor.execute(
			sql,
			{
				"start_date": start_date,
				"end_date": end_date,
			},
		)
