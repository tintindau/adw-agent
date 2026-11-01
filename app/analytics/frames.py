"""Chuyển đổi giữa dữ liệu repository và DataFrame, định dạng kết quả cho LLM."""

from typing import Any

import pandas as pd

from app.core.tracing import traced

DEFAULT_MAX_ROWS = 50


def to_frame(rows: list[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    """Tạo DataFrame với tên cột chữ thường (Oracle trả tên cột in hoa)."""
    df = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    df.columns = [str(column).lower() for column in df.columns]
    return df


def to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame → list[dict], NaN/NaT đổi thành None để serialize JSON được."""
    return df.astype(object).where(pd.notna(df), None).to_dict(orient="records")


@traced("analytics")
def to_llm_result(df: pd.DataFrame, max_rows: int = DEFAULT_MAX_ROWS) -> dict[str, Any]:
    """Cắt kết quả cho gọn và báo rõ có bị cắt hay không."""
    row_count = len(df)
    return {
        "row_count": row_count,
        "truncated": row_count > max_rows,
        "data": to_records(df.head(max_rows)),
    }
