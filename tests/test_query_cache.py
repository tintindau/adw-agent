"""Test cache kết quả truy vấn, không cần Oracle."""

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health import router as health_router
from app.db import query_executor
from app.db.cache import QueryCache, make_key
from app.db.query_executor import QueryExecutor


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class MakeKeyTests(unittest.TestCase):
    def test_param_order_and_whitespace_do_not_matter(self):
        self.assertEqual(
            make_key("SELECT 1 ", {"a": 1, "b": 2}),
            make_key(" SELECT 1", {"b": 2, "a": 1}),
        )

    def test_different_params_give_different_keys(self):
        # Quan trọng cho phân quyền: bộ lọc region khác → không dùng chung cache.
        self.assertNotEqual(
            make_key("SELECT 1", {"region": "Bắc"}),
            make_key("SELECT 1", {"region": "Nam"}),
        )


class QueryCacheTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.cache = QueryCache(ttl_seconds=60, max_entries=2, clock=self.clock)
        self.df = pd.DataFrame({"a": [1, 2]})

    def test_hit_and_miss(self):
        self.assertIsNone(self.cache.get("k"))
        self.cache.set("k", self.df)
        pd.testing.assert_frame_equal(self.cache.get("k"), self.df)
        self.assertEqual(self.cache.stats()["hits"], 1)
        self.assertEqual(self.cache.stats()["misses"], 1)

    def test_expires_after_ttl(self):
        self.cache.set("k", self.df)
        self.clock.now = 61
        self.assertIsNone(self.cache.get("k"))
        self.assertEqual(self.cache.stats()["entries"], 0)

    def test_lru_eviction(self):
        self.cache.set("a", self.df)
        self.cache.set("b", self.df)
        self.cache.get("a")  # a mới dùng → b bị đẩy ra
        self.cache.set("c", self.df)
        self.assertIsNotNone(self.cache.get("a"))
        self.assertIsNone(self.cache.get("b"))
        self.assertIsNotNone(self.cache.get("c"))

    def test_returns_copy(self):
        self.cache.set("k", self.df)
        returned = self.cache.get("k")
        returned["a"] = 0
        self.assertEqual(self.cache.get("k")["a"].tolist(), [1, 2])

    def test_clear(self):
        self.cache.set("k", self.df)
        self.cache.clear()
        self.assertIsNone(self.cache.get("k"))


class QueryExecutorCacheTests(unittest.TestCase):
    def setUp(self):
        query_executor.query_cache.clear()
        self.pool = MagicMock()
        patch.object(query_executor, "get_pool", return_value=self.pool).start()
        self.read_sql = patch.object(
            query_executor.pd, "read_sql", return_value=pd.DataFrame({"A": [1]})
        ).start()
        self.addCleanup(patch.stopall)
        self.addCleanup(query_executor.query_cache.clear)

    def test_repeated_query_hits_database_once(self):
        first = QueryExecutor.execute("SELECT 1", {"m": 202610})
        second = QueryExecutor.execute("SELECT 1", {"m": 202610})
        self.assertEqual(first, second)
        self.assertEqual(self.read_sql.call_count, 1)

    def test_different_params_query_again(self):
        QueryExecutor.execute("SELECT 1", {"m": 202610})
        QueryExecutor.execute("SELECT 1", {"m": 202609})
        self.assertEqual(self.read_sql.call_count, 2)

    def test_use_cache_false_bypasses(self):
        QueryExecutor.execute("SELECT 1", {"m": 1})
        QueryExecutor.execute("SELECT 1", {"m": 1}, use_cache=False)
        self.assertEqual(self.read_sql.call_count, 2)

    def test_disabled_by_setting(self):
        with patch.object(query_executor.settings, "query_cache_enabled", False):
            QueryExecutor.execute("SELECT 1", {"m": 1})
            QueryExecutor.execute("SELECT 1", {"m": 1})
        self.assertEqual(self.read_sql.call_count, 2)

    def test_failed_query_is_not_cached(self):
        self.read_sql.side_effect = [RuntimeError("ORA-12345"), pd.DataFrame({"A": [1]})]
        with self.assertRaises(RuntimeError):
            QueryExecutor.execute("SELECT 1")
        self.assertEqual(QueryExecutor.execute("SELECT 1"), [{"A": 1}])


class HealthCacheStatsTests(unittest.TestCase):
    def test_health_reports_cache_stats(self):
        app = FastAPI()
        app.include_router(health_router, prefix="/api")
        data = TestClient(app).get("/api/health").json()["data"]
        self.assertEqual(data["status"], "ok")
        self.assertIn("hits", data["query_cache"])
