from pathlib import Path
from typing import Any

from app.core.tracing import traced
from app.repositories.sellout_repository import SelloutRepository

SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / "sql"
    / "sellout"
    / "sellout_sql.sql"
)

VALID_DIMENSIONS = {
    "date_",
    "month_",
    "region",
    "province",
    "prod_class_dmx",
    "prod_category",
    "prod_type",
    "gh_flow",
}
VALID_METRICS = {
    "so_qty",
    "so_promo_qty",
    "so_out_qty",
    "so_out_qty_new",
    "si_amount",
    "si_qty",
    "si_promo_qty",
    "si_qty_new",
}
FILTER_COLUMNS = {
    "date_": "si.gh_date_key",
    "region": "s.REGION_NAME_TMP",
    "province": "s.PROVINCE",
    "prod_class_dmx": "p.category_bod",
    "prod_category": "p.sub_category",
    "is_shibu": "p.IS_SHIBU_25PCT",
    "is_dummy": "p.IS_MOCKUP_DUMMY",
    "gh_flow": "si.GH_FLOW",
}
VALID_PROD_TYPES = {"Shibu", "Trung_bay", "Con_lai"}


def build_aggregated_siso_query(
    month: int,
    dimensions: list[str] | None = None,
    metrics: list[str] | None = None,
    **filters: Any,
) -> tuple[str, dict[str, Any]]:
    if month % 100 not in range(1, 13):
        raise ValueError("month must be in YYYYMM format with a valid month")

    try:
        base_query = SQL_FILE.read_text(encoding="utf-8").strip().rstrip(";")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Sellout SQL template not found: {SQL_FILE}") from exc

    conditions = ["si.gh_month_key = :month"]
    params: dict[str, Any] = {"month": month}

    for key, column in FILTER_COLUMNS.items():
        value = filters.get(key)
        if value is not None and value != "":
            conditions.append(f"{column} = :{key}")
            params[key] = value

    prod_type = filters.get("prod_type")
    if prod_type not in (None, ""):
        if prod_type not in VALID_PROD_TYPES:
            raise ValueError(f"prod_type must be one of {sorted(VALID_PROD_TYPES)}")
        params["prod_type"] = prod_type
        conditions.append(
            "CASE "
            "WHEN p.IS_SHIBU_25PCT = 1 THEN 'Shibu' "
            "WHEN p.IS_MOCKUP_DUMMY = 1 THEN 'Trung_bay' "
            "ELSE 'Con_lai' END = :prod_type"
        )

    filtered_base_query = f"{base_query}\nAND " + "\nAND ".join(conditions)
    safe_dimensions = [item for item in (dimensions or []) if item in VALID_DIMENSIONS]
    safe_metrics = [item for item in (metrics or []) if item in VALID_METRICS]

    if safe_dimensions and not safe_metrics:
        safe_metrics = ["so_out_qty", "si_amount"]

    if not safe_dimensions and not safe_metrics:
        return (
            f"SELECT * FROM (\n{filtered_base_query}\n) WHERE ROWNUM <= 30",
            params,
        )

    select_parts = list(safe_dimensions)
    select_parts.extend(f"SUM({metric}) AS {metric}" for metric in safe_metrics)
    query = f"SELECT {', '.join(select_parts)}\nFROM (\n{filtered_base_query}\n)"

    if safe_dimensions:
        query += f"\nGROUP BY {', '.join(safe_dimensions)}"
        if safe_metrics:
            query += f"\nORDER BY {safe_metrics[0]} DESC"

    return f"SELECT * FROM (\n{query}\n) WHERE ROWNUM <= 50", params


class SelloutService:
    @staticmethod
    @traced("service")
    def get_aggregated_siso(
        month: int,
        dimensions: list[str] | None = None,
        metrics: list[str] | None = None,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        sql, params = build_aggregated_siso_query(
            month=month,
            dimensions=dimensions,
            metrics=metrics,
            **filters,
        )
        return SelloutRepository.execute(sql, params)