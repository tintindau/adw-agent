"""Chỉ số phái sinh tính sau khi SQL đã tổng hợp.

Nguyên tắc: SUM/GROUP BY làm ở SQL; ở đây chỉ tính các chỉ số khó viết
trong SQL hoặc cần kết hợp nhiều kết quả, để model không phải tự làm phép tính.
"""

import pandas as pd

from app.core.tracing import traced


def _safe_ratio(numerator: pd.Series, denominator: pd.Series, scale: float = 100.0) -> pd.Series:
    """numerator / denominator * scale, làm tròn 2 chữ số; mẫu số 0 hoặc rỗng → None."""
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce")
    ratio = (num / den.where(den != 0)) * scale
    return ratio.round(2).astype(object).where(ratio.notna(), None)


@traced("analytics")
def add_share_pct(
    df: pd.DataFrame,
    value_column: str,
    by: list[str] | None = None,
    output_column: str | None = None,
) -> pd.DataFrame:
    """Thêm cột tỉ trọng % của mỗi dòng trên tổng (hoặc trên tổng trong nhóm `by`)."""
    output_column = output_column or f"{value_column}_share_pct"
    values = pd.to_numeric(df[value_column], errors="coerce")
    totals = values.groupby([df[c] for c in by]).transform("sum") if by else pd.Series(values.sum(), index=df.index)
    result = df.copy()
    result[output_column] = _safe_ratio(values, totals)
    return result


@traced("analytics")
def compare_periods(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    keys: list[str],
    value_columns: list[str],
) -> pd.DataFrame:
    """So sánh hai kỳ (vd tháng này và tháng trước) theo các cột khoá.

    Với mỗi chỉ số `x` tạo: `x` (kỳ hiện tại), `x_prev`, `x_diff`, `x_growth_pct`.
    Dòng chỉ có ở một kỳ được coi giá trị kỳ còn lại là 0; growth = None khi kỳ trước = 0.
    """
    merged = current[keys + value_columns].merge(
        previous[keys + value_columns],
        on=keys,
        how="outer",
        suffixes=("", "_prev"),
    )
    for column in value_columns:
        cur = pd.to_numeric(merged[column], errors="coerce").fillna(0)
        prev = pd.to_numeric(merged[f"{column}_prev"], errors="coerce").fillna(0)
        merged[column] = cur
        merged[f"{column}_prev"] = prev
        merged[f"{column}_diff"] = cur - prev
        merged[f"{column}_growth_pct"] = _safe_ratio(cur - prev, prev)
    return merged


@traced("analytics")
def add_sell_through_pct(
    df: pd.DataFrame,
    sell_out_column: str = "so_out_qty",
    sell_in_column: str = "si_qty",
    output_column: str = "sell_through_pct",
) -> pd.DataFrame:
    """Tỉ lệ bán ra trên nhập vào (%): sell-out / sell-in * 100."""
    result = df.copy()
    result[output_column] = _safe_ratio(df[sell_out_column], df[sell_in_column])
    return result
