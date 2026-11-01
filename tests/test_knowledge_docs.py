"""Bảo đảm knowledge/ mô tả đủ các dimension, metric, bộ lọc mà service hỗ trợ."""

import re
import unittest
from pathlib import Path

from app.services import sellout_prod_top_class_cat_service as top_products
from app.services import sellout_service as sellout

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
SELLIN_SQL = Path(__file__).resolve().parents[1] / "app" / "sql" / "sellin" / "get_by_month.sql"


def documented_names(file_name: str) -> set[str]:
    """Các tên nằm trong dấu `...` của file knowledge."""
    text = (KNOWLEDGE_DIR / file_name).read_text(encoding="utf-8")
    return set(re.findall(r"`([a-z0-9_]+)`", text))


class KnowledgeDocsTests(unittest.TestCase):
    def assert_documented(self, file_name: str, names: set[str]):
        missing = sorted(names - documented_names(file_name))
        self.assertFalse(missing, f"knowledge/{file_name} thiếu mô tả cho: {missing}")

    def test_sellout_documents_all_dimensions_metrics_filters(self):
        self.assert_documented(
            "sellout.md",
            sellout.VALID_DIMENSIONS | sellout.VALID_METRICS | set(sellout.FILTER_COLUMNS) | {"prod_type"},
        )

    def test_top_products_documents_all_dimensions_filters(self):
        self.assert_documented(
            "top_products.md",
            top_products.VALID_DIMENSIONS | set(top_products.FILTER_COLUMNS),
        )

    def test_sellin_documents_all_output_columns(self):
        sql = SELLIN_SQL.read_text(encoding="utf-8")
        columns = {name.lower() for name in re.findall(r"\bAS\s+([A-Za-z0-9_]+)", sql)}
        self.assertTrue(columns)
        self.assert_documented("sellin.md", columns)

    def test_knowledge_files_are_not_empty(self):
        for path in KNOWLEDGE_DIR.glob("*.md"):
            self.assertTrue(path.read_text(encoding="utf-8").strip(), path.name)
