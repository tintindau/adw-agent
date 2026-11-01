"""Analytics layer: xử lý DataFrame sau khi repository lấy dữ liệu từ ADW.

Hàm ở đây là hàm thuần trên DataFrame: không gọi DB, không biết HTTP/MCP,
test được không cần Oracle. Service gọi repository lấy dữ liệu rồi gọi các
hàm này để tính chỉ số phái sinh và định dạng kết quả cho model.
"""

from app.analytics.export import export_csv_7z
from app.analytics.frames import to_frame, to_llm_result, to_records
from app.analytics.metrics import add_sell_through_pct, add_share_pct, compare_periods
from app.analytics.ranking import make_labels, top_n_with_others

__all__ = [
    "add_sell_through_pct",
    "add_share_pct",
    "compare_periods",
    "export_csv_7z",
    "make_labels",
    "to_frame",
    "to_llm_result",
    "to_records",
    "top_n_with_others",
]
