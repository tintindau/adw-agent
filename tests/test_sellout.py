import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.sellout import router
from app.repositories.sellout_repository import SelloutRepository
from app.services.sellout_service import (
    SelloutService,
    build_aggregated_siso_query,
)


class SelloutApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_month_dimensions_metrics_and_filters_are_forwarded(self):
        with patch.object(SelloutService, "get_aggregated_siso", return_value=[]) as query:
            response = self.client.get(
                "/sellout",
                params=[
                    ("month", "202610"),
                    ("dimensions", "province"),
                    ("metrics", "so_out_qty"),
                    ("province", "HANOI"),
                ],
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "data": []})
        query.assert_called_once_with(
            month=202610,
            dimensions=["province"],
            metrics=["so_out_qty"],
            date_=None,
            region=None,
            province="HANOI",
            prod_class_dmx=None,
            prod_category=None,
            is_shibu=None,
            is_dummy=None,
            prod_type=None,
            gh_flow=None,
        )

    def test_month_is_required(self):
        response = self.client.get("/sellout")

        self.assertEqual(response.status_code, 422)

    def test_month_must_have_valid_month_number(self):
        with patch.object(SelloutService, "get_aggregated_siso") as query:
            response = self.client.get("/sellout", params={"month": "202613"})

        self.assertEqual(response.status_code, 422)
        query.assert_not_called()


class SelloutQueryBuilderTests(unittest.TestCase):
    def test_builds_aggregate_query_with_bound_filters(self):
        sql, params = build_aggregated_siso_query(
            month=202610,
            dimensions=["province"],
            metrics=["so_out_qty"],
            province="HANOI",
            prod_type="Con_lai",
        )

        self.assertEqual(
            params,
            {"month": 202610, "province": "HANOI", "prod_type": "Con_lai"},
        )
        self.assertIn("SUM(so_out_qty) AS so_out_qty", sql)
        self.assertIn("GROUP BY province", sql)
        self.assertIn("s.PROVINCE = :province", sql)
        self.assertIn("END = :prod_type", sql)
        self.assertIn("NVL(si.GH_SI_AMOUNT, 0) AS si_amount", sql)
        self.assertIn("ROWNUM <= 50", sql)

    def test_defaults_metrics_when_dimensions_are_provided(self):
        sql, _ = build_aggregated_siso_query(
            month=202610,
            dimensions=["region"],
        )

        self.assertIn("SUM(so_out_qty) AS so_out_qty", sql)
        self.assertIn("SUM(si_amount) AS si_amount", sql)

    def test_ignores_untrusted_dimension_and_metric_identifiers(self):
        sql, _ = build_aggregated_siso_query(
            month=202610,
            dimensions=["province; DROP TABLE dim_product"],
            metrics=["so_qty DESC"],
        )

        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("so_qty DESC", sql)
        self.assertIn("ROWNUM <= 30", sql)

    def test_rejects_invalid_month_and_product_type(self):
        with self.assertRaises(ValueError):
            build_aggregated_siso_query(month=202613)
        with self.assertRaises(ValueError):
            build_aggregated_siso_query(month=202610, prod_type="Unknown")


class SelloutRepositoryTests(unittest.TestCase):
    def test_service_executes_built_query_through_repository(self):
        with patch.object(SelloutRepository, "execute", return_value=[]) as execute:
            result = SelloutService.get_aggregated_siso(
                month=202610,
                dimensions=["province"],
                metrics=["si_amount"],
            )

        self.assertEqual(result, [])
        sql, params = execute.call_args.args
        self.assertIn("SUM(si_amount) AS si_amount", sql)
        self.assertEqual(params, {"month": 202610})


class ApplicationRouteTests(unittest.TestCase):
    def test_sellout_and_health_routes_are_registered(self):
        from app.main import app

        paths = set(app.openapi()["paths"])
        self.assertIn("/api/sellout", paths)
        self.assertIn("/api/health", paths)


if __name__ == "__main__":
    unittest.main()