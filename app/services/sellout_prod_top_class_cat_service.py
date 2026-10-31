import csv
import tempfile
import uuid
from pathlib import Path
from typing import Any

from app.repositories.sellout_repository import SelloutRepository

SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / "sql"
    / "sellout"
    / "sqlout_prod_top_class_cat.sql"
)

VALID_DIMENSIONS = {
    "prod_code",
    "prod_name",
    "date_",
    "month_",
    "year_",
    "prod_id_kgr",
    "prod_name_kgr",
    "category_bod",
    "is_shibu",
}
DEFAULT_DIMENSIONS = ["prod_code", "prod_name_kgr"]
FILTER_COLUMNS = {
    "prod_code": "o.dmx_prod_id",
    "prod_name": "o.DMX_PROD_NAME",
    "date_": "o.date_key",
    "prod_id_kgr": "p.PROD_ID_KGR",
    "prod_name_kgr": "p.PROD_NAME_KGR",
    "category_bod": "p.CATEGORY_BOD",
    "is_shibu": "p.IS_SHIBU_25PCT",
}
BAD_RANK_TYPES = {"bad", "bottom", "asc"}
MAX_LIMIT = 500
CHART_ROW_THRESHOLD = 30
CHART_TOP_ROWS = 20
EXPORT_DIR = Path(tempfile.gettempdir()) / "naw_agent_exports"


def build_top_class_cat_query(
    month: int,
    dimensions: list[str] | None = None,
    rank_type: str = "top",
    limit: int = 20,
    **filters: Any,
) -> tuple[str, dict[str, Any]]:
    if month % 100 not in range(1, 13):
        raise ValueError("month must be in YYYYMM format with a valid month")

    try:
        base_query = SQL_FILE.read_text(encoding="utf-8").strip().rstrip(";")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Sellout SQL template not found: {SQL_FILE}") from exc

    conditions = ["d.cal_year_code = :year_", "d.cal_month_number = :month_"]
    params: dict[str, Any] = {"year_": str(month // 100), "month_": month % 100}

    for key, column in FILTER_COLUMNS.items():
        value = filters.get(key)
        if value is not None and value != "":
            conditions.append(f"{column} = :{key}")
            params[key] = value

    filtered_base_query = f"{base_query}\nAND " + "\nAND ".join(conditions)

    safe_dimensions = list(
        dict.fromkeys(d for d in (dimensions or []) if d in VALID_DIMENSIONS)
    ) or DEFAULT_DIMENSIONS
    dim_clause = ", ".join(safe_dimensions)

    order_dir = "ASC" if str(rank_type).lower() in BAD_RANK_TYPES else "DESC"
    params["limit_rows"] = min(max(int(limit), 1), MAX_LIMIT)

    query = (
        f"SELECT {dim_clause}, SUM(amount_) AS amount_\n"
        f"FROM (\n{filtered_base_query}\n)\n"
        f"GROUP BY {dim_clause}\n"
        f"HAVING SUM(amount_) > 0\n"
        f"ORDER BY amount_ {order_dir}, {dim_clause}\n"
        f"FETCH FIRST :limit_rows ROWS ONLY"
    )
    return query, params


def _label(row: dict[str, Any]) -> str:
    return " - ".join(str(v) for k, v in row.items() if k != "amount_")


def _amount(row: dict[str, Any]) -> float:
    return float(row.get("amount_") or 0)


def _export_7z(rows: list[dict[str, Any]], export_dir: Path) -> str:
    import py7zr

    export_dir.mkdir(parents=True, exist_ok=True)
    name = f"sellout_top_{len(rows)}_{uuid.uuid4().hex[:8]}"
    csv_path = export_dir / f"{name}.csv"
    archive_path = export_dir / f"{name}.7z"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with py7zr.SevenZipFile(archive_path, "w") as archive:
        archive.write(csv_path, arcname=csv_path.name)
    csv_path.unlink()

    return str(archive_path)


def build_result(rows: list[dict[str, Any]], export_dir: Path = EXPORT_DIR) -> dict[str, Any]:
    """Shape rows for the LLM: small result inline, large result as a .7z plus a trimmed chart."""
    rows = [{k.lower(): v for k, v in r.items()} for r in rows]
    total_rows = len(rows)
    if total_rows == 0:
        return {"status": "empty", "message": "No data matches the filters."}

    archive_path = None
    labels = [_label(r) for r in rows]
    values = [_amount(r) for r in rows]

    if total_rows > CHART_ROW_THRESHOLD:
        archive_path = _export_7z(rows, export_dir)
        labels = labels[:CHART_TOP_ROWS] + [f"Others ({total_rows - CHART_TOP_ROWS})"]
        values = values[:CHART_TOP_ROWS] + [sum(values[CHART_TOP_ROWS:])]

    return {
        "status": "ok",
        "total_rows_fetched": total_rows,
        "download_file_7z": archive_path,
        "chart_data": {"labels": labels, "amount_vnd": values},
    }


class SelloutProdTopClassCatService:
    @staticmethod
    def get_top_products(
        month: int,
        dimensions: list[str] | None = None,
        rank_type: str = "top",
        limit: int = 20,
        **filters: Any,
    ) -> dict[str, Any]:
        sql, params = build_top_class_cat_query(
            month=month,
            dimensions=dimensions,
            rank_type=rank_type,
            limit=limit,
            **filters,
        )
        return build_result(SelloutRepository.execute(sql, params))
