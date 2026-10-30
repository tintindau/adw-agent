from datetime import date, timedelta
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.sellout import router
from app.db.query_executor import QueryExecutor
from app.repositories.sellout_repository import SelloutRepository
from app.services.sellout_service import SelloutService


class SelloutApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_default_date_returns_sellout_data(self):
        with patch.object(SelloutService, "get_sellout", return_value=[]) as get_sellout:
            response = self.client.get("/sellout")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "data": []})
        today = date.today()
        get_sellout.assert_called_once_with(
            (today - timedelta(days=30)).strftime("%Y%m%d"),
            (today + timedelta(days=1)).strftime("%Y%m%d"),
        )

    def test_explicit_date_bounds_are_forwarded(self):
        with patch.object(SelloutService, "get_sellout", return_value=[]) as get_sellout:
            response = self.client.get(
                "/sellout",
                params={"start_date": "20261001", "end_date": "20261101"},
            )

        self.assertEqual(response.status_code, 200)
        get_sellout.assert_called_once_with("20261001", "20261101")

    def test_invalid_calendar_date_is_rejected(self):
        with patch.object(SelloutService, "get_sellout") as get_sellout:
            response = self.client.get(
                "/sellout",
                params={"start_date": "20260230"},
            )

        self.assertEqual(response.status_code, 422)
        get_sellout.assert_not_called()

    def test_start_date_must_precede_exclusive_end_date(self):
        with patch.object(SelloutService, "get_sellout") as get_sellout:
            response = self.client.get(
                "/sellout",
                params={"start_date": "20261101", "end_date": "20261101"},
            )

        self.assertEqual(response.status_code, 422)
        get_sellout.assert_not_called()


class SelloutRepositoryTests(unittest.TestCase):
    def test_query_uses_date_bind_and_requested_projection(self):
        with patch.object(QueryExecutor, "execute", return_value=[]) as execute:
            SelloutRepository.get_sellout("20261001", "20261101")

        sql, params = execute.call_args.args
        self.assertEqual(
            params,
            {"start_date": "20261001", "end_date": "20261101"},
        )
        self.assertIn("o.NET_QUANTITY * o.REVENUE_SRC_VND AS Revenue", sql)
        self.assertIn("REGEXP_REPLACE(o.store_key", sql)
        self.assertIn("WHERE o.date_key >= :start_date", sql)
        self.assertIn("AND o.date_key < :end_date", sql)


class ApplicationRouteTests(unittest.TestCase):
    def test_sellout_and_health_routes_are_registered(self):
        from app.main import app

        paths = set(app.openapi()["paths"])
        self.assertIn("/api/sellout", paths)
        self.assertIn("/api/health", paths)


if __name__ == "__main__":
    unittest.main()