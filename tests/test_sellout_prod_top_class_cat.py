import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.sellout_prod_top_class_cat import router
from app.repositories.sellout_repository import SelloutRepository
from app.services.sellout_prod_top_class_cat_service import (
    SelloutProdTopClassCatService,
    build_result,
    build_top_class_cat_query,
)


class TopClassCatApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_params_are_forwarded(self):
        with patch.object(
            SelloutProdTopClassCatService, "get_top_products", return_value={}
        ) as query:
            response = self.client.get(
                "/sellout/top-products",
                params=[
                    ("month", "202610"),
                    ("dimensions", "category_bod"),
                    ("rank_type", "bad"),
                    ("limit", "10"),
                    ("category_bod", "TV"),
                ],
            )

        self.assertEqual(response.status_code, 200)
        kwargs = query.call_args.kwargs
        self.assertEqual(kwargs["month"], 202610)
        self.assertEqual(kwargs["dimensions"], ["category_bod"])
        self.assertEqual(kwargs["rank_type"], "bad")
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["category_bod"], "TV")

    def test_validation(self):
        self.assertEqual(self.client.get("/sellout/top-products").status_code, 422)
        self.assertEqual(
            self.client.get("/sellout/top-products", params={"month": "202613"}).status_code,
            422,
        )
        self.assertEqual(
            self.client.get(
                "/sellout/top-products", params={"month": "202610", "limit": "9999"}
            ).status_code,
            422,
        )


class TopClassCatQueryTests(unittest.TestCase):
    def test_default_query(self):
        sql, params = build_top_class_cat_query(month=202610)

        self.assertEqual(params, {"year_": "2026", "month_": 10, "limit_rows": 20})
        self.assertIn("SELECT prod_code, prod_name_kgr, SUM(amount_) AS amount_", sql)
        self.assertIn("d.cal_year_code = :year_", sql)
        self.assertIn("ORDER BY amount_ DESC", sql)
        self.assertIn("FETCH FIRST :limit_rows ROWS ONLY", sql)

    def test_bad_rank_filters_and_limit_clamp(self):
        sql, params = build_top_class_cat_query(
            month=202610,
            dimensions=["category_bod"],
            rank_type="bad",
            limit=100000,
            category_bod="TV",
            is_shibu=0,
        )

        self.assertIn("ORDER BY amount_ ASC", sql)
        self.assertIn("p.CATEGORY_BOD = :category_bod", sql)
        self.assertIn("p.IS_SHIBU_25PCT = :is_shibu", sql)
        self.assertEqual(params["category_bod"], "TV")
        self.assertEqual(params["is_shibu"], 0)
        self.assertEqual(params["limit_rows"], 500)

    def test_untrusted_dimensions_are_ignored(self):
        sql, _ = build_top_class_cat_query(
            month=202610, dimensions=["prod_code; DROP TABLE x"]
        )

        self.assertNotIn("DROP TABLE", sql)
        self.assertIn("GROUP BY prod_code, prod_name_kgr", sql)

    def test_invalid_month(self):
        with self.assertRaises(ValueError):
            build_top_class_cat_query(month=202613)


class TopClassCatResultTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(build_result([])["status"], "empty")

    def test_small_result_has_no_archive(self):
        rows = [{"PROD_CODE": "A", "AMOUNT_": 5}, {"PROD_CODE": "B", "AMOUNT_": 3}]
        result = build_result(rows)

        self.assertIsNone(result["download_file_7z"])
        self.assertEqual(result["chart_data"]["labels"], ["A", "B"])
        self.assertEqual(result["chart_data"]["amount_vnd"], [5.0, 3.0])

    def test_large_result_is_trimmed_and_archived(self):
        rows = [{"prod_code": f"P{i}", "amount_": 100 - i} for i in range(40)]
        with tempfile.TemporaryDirectory() as tmp:
            result = build_result(rows, export_dir=Path(tmp))
            self.assertTrue(Path(result["download_file_7z"]).exists())

        labels = result["chart_data"]["labels"]
        values = result["chart_data"]["amount_vnd"]
        self.assertEqual(len(labels), 21)
        self.assertEqual(labels[-1], "Others (20)")
        self.assertEqual(values[-1], float(sum(100 - i for i in range(20, 40))))


class TopClassCatServiceTests(unittest.TestCase):
    def test_service_goes_through_repository(self):
        with patch.object(
            SelloutRepository, "execute", return_value=[{"prod_code": "A", "amount_": 1}]
        ) as execute:
            result = SelloutProdTopClassCatService.get_top_products(month=202610)

        self.assertEqual(result["total_rows_fetched"], 1)
        sql, params = execute.call_args.args
        self.assertIn("SUM(amount_)", sql)
        self.assertEqual(params["month_"], 10)


class ApplicationRouteTests(unittest.TestCase):
    def test_route_registered(self):
        from app.main import app

        self.assertIn("/api/sellout/top-products", set(app.openapi()["paths"]))


if __name__ == "__main__":
    unittest.main()
