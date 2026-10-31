import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pandas as pd

from app.api.sellin import router
from app.db.query_executor import QueryExecutor
from app.repositories.sellin_repository import SellinRepository
from app.services.sellin_service import SellinService


class SellinApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_month_is_required(self):
        response = self.client.get("/sellin")

        self.assertEqual(response.status_code, 422)

    def test_optional_filters_are_forwarded(self):
        with patch.object(SellinService, "get_by_month", return_value=[]) as get_by_month:
            response = self.client.get(
                "/sellin",
                params={
                    "month_": "202610",
                    "province": "HANOI",
                    "prod_code": "P001",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "data": []})
        filters = get_by_month.call_args.args[0]
        self.assertEqual(filters["month_"], "202610")
        self.assertEqual(filters["province"], "HANOI")
        self.assertEqual(filters["prod_code"], "P001")
        self.assertIsNone(filters["date_"])
        self.assertIsNone(filters["from_date"])
        self.assertIsNone(filters["store_name"])

    def test_date_range_is_forwarded_and_must_be_ordered(self):
        with patch.object(SellinService, "get_by_month", return_value=[]) as get_by_month:
            response = self.client.get(
                "/sellin",
                params={
                    "month_": "202610",
                    "from_date": "20261001",
                    "to_date": "20261031",
                },
            )

        self.assertEqual(response.status_code, 200)
        filters = get_by_month.call_args.args[0]
        self.assertEqual(filters["from_date"], "20261001")
        self.assertEqual(filters["to_date"], "20261031")
        self.assertIsNone(filters["date_"])

        reversed_range = self.client.get(
            "/sellin",
            params={
                "month_": "202610",
                "from_date": "20261031",
                "to_date": "20261001",
            },
        )
        self.assertEqual(reversed_range.status_code, 422)

    def test_single_date_cannot_be_combined_with_date_range(self):
        response = self.client.get(
            "/sellin",
            params={
                "month_": "202610",
                "date_": "20261015",
                "from_date": "20261001",
            },
        )

        self.assertEqual(response.status_code, 422)


class SellinRepositoryTests(unittest.TestCase):
    def test_repository_binds_month_and_optional_filters(self):
        filters = {
            "month_": "202610",
            "date_": None,
            "from_date": "20261001",
            "to_date": "20261031",
            "store_name": None,
            "store_code": None,
            "region": None,
            "province": "HANOI",
            "prod_code": "P001",
            "prod_name": None,
            "model_name": None,
            "prod_class_dmx": None,
            "prod_category": None,
            "is_shibu": None,
            "is_dummy": None,
        }
        with patch.object(QueryExecutor, "execute", return_value=[]) as execute:
            SellinRepository.get_by_month(filters)

        sql, params = execute.call_args.args
        self.assertEqual(params, filters)
        self.assertIn("si.gh_month_key = :month_", sql)
        self.assertIn("si.gh_date_key >= :from_date", sql)
        self.assertIn("si.gh_date_key <= :to_date", sql)
        for column in (
            "gh_so_qty",
            "gh_so_promo_qty",
            "gh_so_out_qty",
            "gh_so_out_qty_new",
            "gh_si_amount",
            "gh_si_qty",
            "gh_si_promo_qty",
            "gh_si_qty_new",
        ):
            self.assertIn(f"NVL(si.{column}, 0) AS {column}", sql)
        self.assertIn("UTL_MATCH.JARO_WINKLER_SIMILARITY(UPPER(s.province)", sql)
        self.assertIn("INSTR(UPPER(p.prod_id_kgr)", sql)
        self.assertIn("UPPER(TRIM(:prod_name))", sql)
        self.assertIn(":is_dummy IS NULL OR p.is_mockup_dummy = :is_dummy", sql)


class QueryExecutorTests(unittest.TestCase):
    def test_database_nulls_are_converted_for_json(self):
        frame = pd.DataFrame({"PROD_CLASS_DMX": [float("nan")]})
        with (
            patch("app.db.query_executor.get_pool"),
            patch("app.db.query_executor.pd.read_sql", return_value=frame),
        ):
            rows = QueryExecutor.execute("SELECT NULL FROM dual")

        self.assertEqual(rows, [{"PROD_CLASS_DMX": None}])


if __name__ == "__main__":
    unittest.main()