"""Test analytics layer: hàm thuần trên DataFrame, không cần Oracle."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.analytics import (
    add_sell_through_pct,
    add_share_pct,
    compare_periods,
    export_csv_7z,
    to_frame,
    to_llm_result,
    to_records,
    top_n_with_others,
)


class FramesTests(unittest.TestCase):
    def test_to_frame_lowercases_columns(self):
        df = to_frame([{"PROD_CODE": "A", "AMOUNT_": 1}])
        self.assertEqual(list(df.columns), ["prod_code", "amount_"])

    def test_to_records_turns_nan_into_none(self):
        records = to_records(pd.DataFrame({"a": [1.0, None]}))
        self.assertEqual(records, [{"a": 1.0}, {"a": None}])

    def test_to_llm_result_truncates(self):
        result = to_llm_result(pd.DataFrame({"a": range(60)}), max_rows=50)
        self.assertEqual(result["row_count"], 60)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["data"]), 50)

    def test_to_llm_result_small(self):
        result = to_llm_result(pd.DataFrame({"a": [1, 2]}))
        self.assertFalse(result["truncated"])
        self.assertEqual(result["data"], [{"a": 1}, {"a": 2}])


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {"code": ["A", "B", "C", "D"], "name": ["a", "b", "c", "d"], "amount_": [40, 30, 20, 10]}
        )

    def test_keeps_all_when_under_n(self):
        result = top_n_with_others(self.df, "amount_", ["code"], n=10)
        self.assertEqual(result["label"].tolist(), ["A", "B", "C", "D"])

    def test_groups_rest_into_others(self):
        result = top_n_with_others(self.df, "amount_", ["code", "name"], n=2)
        self.assertEqual(result["label"].tolist(), ["A - a", "B - b", "Others (2)"])
        self.assertEqual(result["value"].tolist(), [40.0, 30.0, 30.0])

    def test_keeps_sql_order(self):
        reversed_df = self.df.iloc[::-1]
        result = top_n_with_others(reversed_df, "amount_", ["code"], n=1)
        self.assertEqual(result["label"].tolist(), ["D", "Others (3)"])


class MetricsTests(unittest.TestCase):
    def test_share_pct_total(self):
        df = pd.DataFrame({"region": ["N", "S"], "si_amount": [75, 25]})
        result = add_share_pct(df, "si_amount")
        self.assertEqual(result["si_amount_share_pct"].tolist(), [75.0, 25.0])

    def test_share_pct_by_group(self):
        df = pd.DataFrame({"region": ["N", "N", "S"], "province": ["a", "b", "c"], "qty": [1, 3, 5]})
        result = add_share_pct(df, "qty", by=["region"], output_column="share")
        self.assertEqual(result["share"].tolist(), [25.0, 75.0, 100.0])

    def test_share_pct_zero_total_is_none(self):
        result = add_share_pct(pd.DataFrame({"qty": [0, 0]}), "qty")
        self.assertEqual(result["qty_share_pct"].tolist(), [None, None])

    def test_compare_periods(self):
        current = pd.DataFrame({"region": ["N", "S", "C"], "qty": [120, 50, 7]})
        previous = pd.DataFrame({"region": ["N", "S", "W"], "qty": [100, 0, 9]})
        result = compare_periods(current, previous, ["region"], ["qty"]).set_index("region")

        self.assertEqual(result.loc["N", "qty_prev"], 100)
        self.assertEqual(result.loc["N", "qty_diff"], 20)
        self.assertEqual(result.loc["N", "qty_growth_pct"], 20.0)
        self.assertIsNone(result.loc["S", "qty_growth_pct"])  # kỳ trước = 0
        self.assertEqual(result.loc["C", "qty_prev"], 0)  # chỉ có ở kỳ này
        self.assertEqual(result.loc["W", "qty"], 0)  # chỉ có ở kỳ trước
        self.assertEqual(result.loc["W", "qty_growth_pct"], -100.0)

    def test_sell_through_pct(self):
        df = pd.DataFrame({"so_out_qty": [80, 5], "si_qty": [100, 0]})
        result = add_sell_through_pct(df)
        self.assertEqual(result["sell_through_pct"].tolist(), [80.0, None])


class ExportTests(unittest.TestCase):
    def test_export_creates_archive_only(self):
        df = pd.DataFrame({"tên": ["Máy lọc nước"], "amount_": [1]})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(export_csv_7z(df, Path(tmp), prefix="t"))
            self.assertTrue(path.exists())
            self.assertEqual(path.suffix, ".7z")
            self.assertEqual(list(Path(tmp).glob("*.csv")), [])
