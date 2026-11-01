"""Xếp hạng và gộp nhóm nhỏ."""

import pandas as pd

from app.core.tracing import traced

LABEL_SEPARATOR = " - "


def make_labels(df: pd.DataFrame, label_columns: list[str]) -> pd.Series:
    """Ghép các cột thành nhãn, vd 'P01 - Máy lọc nước'."""
    return df[label_columns].astype(str).agg(LABEL_SEPARATOR.join, axis=1)


@traced("analytics")
def top_n_with_others(
    df: pd.DataFrame,
    value_column: str,
    label_columns: list[str],
    n: int,
) -> pd.DataFrame:
    """Giữ n dòng đầu theo thứ tự hiện tại, gộp phần còn lại thành 'Others (k)'.

    Trả DataFrame hai cột `label`, `value`. Không sắp xếp lại: thứ tự xếp hạng
    đã được quyết định ở SQL (top hoặc bad).
    """
    result = pd.DataFrame(
        {
            "label": make_labels(df, label_columns),
            "value": pd.to_numeric(df[value_column], errors="coerce").fillna(0).astype(float),
        }
    ).reset_index(drop=True)

    if len(result) <= n:
        return result

    rest = result.iloc[n:]
    others = pd.DataFrame({"label": [f"Others ({len(rest)})"], "value": [float(rest["value"].sum())]})
    return pd.concat([result.iloc[:n], others], ignore_index=True)
