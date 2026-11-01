"""Test log audit: request (câu hỏi user) → service → analytics → sql → response."""

import json
import logging
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.analytics import top_n_with_others
from app.core.audit_middleware import register_audit_middleware
from app.core.logger import AUDIT_LOGGER_NAME, ContextFilter, JsonFormatter, log_event
from app.core.request_context import context_from_headers, get_context, reset_context, set_context
from app.core.tracing import summarize, traced
from app.db import query_executor
from app.db.query_executor import QueryExecutor, compact_sql


class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.addFilter(ContextFilter())
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)

    def events(self, name=None):
        result = [{**r.ctx, **r.fields} for r in self.records if hasattr(r, "fields")]
        return [e for e in result if name is None or e["event"] == name]


class AuditTestCase(unittest.TestCase):
    def setUp(self):
        self.capture = CaptureHandler()
        self.audit_logger = logging.getLogger(AUDIT_LOGGER_NAME)
        self.audit_logger.addHandler(self.capture)
        self.audit_logger.setLevel(logging.DEBUG)
        self.addCleanup(self.audit_logger.removeHandler, self.capture)


class RequestContextTests(unittest.TestCase):
    def test_headers_are_decoded(self):
        context = context_from_headers(
            {
                "X-Request-Id": "abc",
                "X-OpenWebUI-User-Email": "a%40kangaroo.vn",
                "X-User-Question": quote("Doanh số tháng 10 miền Bắc?"),
            }
        )
        self.assertEqual(context["request_id"], "abc")
        self.assertEqual(context["user_email"], "a@kangaroo.vn")
        self.assertEqual(context["question"], "Doanh số tháng 10 miền Bắc?")

    def test_request_id_is_generated(self):
        self.assertTrue(context_from_headers({})["request_id"])

    def test_set_and_reset(self):
        token = set_context(request_id="r1", question="")
        self.assertEqual(get_context(), {"request_id": "r1"})
        reset_context(token)
        self.assertEqual(get_context(), {})


class TracingTests(AuditTestCase):
    def test_summarize_dataframe_and_long_list(self):
        self.assertEqual(summarize(pd.DataFrame({"a": [1, 2]}))["rows"], 2)
        self.assertEqual(summarize(list(range(100))), {"type": "list", "len": 100})

    def test_traced_logs_success(self):
        @traced("service")
        def add(a, b=1):
            return a + b

        self.assertEqual(add(2, b=3), 5)
        event = self.capture.events("service")[0]
        self.assertEqual(event["args"], {"a": 2, "b": 3})
        self.assertEqual(event["result"], 5)
        self.assertEqual(event["status"], "ok")
        self.assertIn("duration_ms", event)

    def test_traced_logs_error_and_reraises(self):
        @traced("service")
        def boom():
            raise ValueError("sai tháng")

        with self.assertRaises(ValueError):
            boom()
        event = self.capture.events("service")[0]
        self.assertEqual(event["status"], "error")
        self.assertIn("sai tháng", event["error"])

    def test_analytics_functions_are_traced(self):
        df = pd.DataFrame({"code": ["A", "B"], "amount_": [2, 1]})
        top_n_with_others(df, "amount_", ["code"], n=1)
        event = self.capture.events("analytics")[0]
        self.assertTrue(event["func"].endswith("top_n_with_others"))
        self.assertEqual(event["args"]["df"]["rows"], 2)


class SqlLoggingTests(AuditTestCase):
    def setUp(self):
        super().setUp()
        query_executor.query_cache.clear()
        patch.object(query_executor, "get_pool", return_value=MagicMock()).start()
        self.read_sql = patch.object(
            query_executor.pd, "read_sql", return_value=pd.DataFrame({"A": [1, 2]})
        ).start()
        self.addCleanup(patch.stopall)
        self.addCleanup(query_executor.query_cache.clear)

    def test_compact_sql(self):
        self.assertEqual(compact_sql("SELECT a -- cột a\n  FROM t\n WHERE 1=1"), "SELECT a FROM t WHERE 1=1")

    def test_sql_logged_with_params_and_cache_status(self):
        QueryExecutor.execute("SELECT *\nFROM t WHERE m = :m", {"m": 202610})
        QueryExecutor.execute("SELECT *\nFROM t WHERE m = :m", {"m": 202610})

        first, second = self.capture.events("sql")
        self.assertEqual(first["sql"], "SELECT * FROM t WHERE m = :m")
        self.assertEqual(first["params"], {"m": 202610})
        self.assertEqual(first["rows"], 2)
        self.assertEqual(first["cache"], "miss")
        self.assertEqual(second["cache"], "hit")

    def test_sql_text_hidden_when_disabled(self):
        with patch.object(query_executor.settings, "log_sql", False):
            QueryExecutor.execute("SELECT 1", {"m": 1})
        event = self.capture.events("sql")[0]
        self.assertNotIn("sql", event)
        self.assertNotIn("params", event)

    def test_sql_error_logged(self):
        self.read_sql.side_effect = RuntimeError("ORA-00942")
        with self.assertRaises(RuntimeError):
            QueryExecutor.execute("SELECT 1")
        event = self.capture.events("sql")[0]
        self.assertEqual(event["status"], "error")
        self.assertIn("ORA-00942", event["error"])


class MiddlewareTests(AuditTestCase):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        register_audit_middleware(app)

        @app.get("/api/demo")
        def demo(month: int):
            log_event("inside", month=month)
            return {"success": True, "data": []}

        @app.get("/api/crash")
        def crash():
            raise RuntimeError("secret detail")

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_request_flow_shares_request_id_and_question(self):
        response = self.client.get(
            "/api/demo",
            params={"month": 202610},
            headers={"X-Request-Id": "req-1", "X-User-Question": quote("Sell-out tháng 10?")},
        )
        self.assertEqual(response.headers["X-Request-Id"], "req-1")

        request, inside, done = self.capture.events()
        self.assertEqual(request["event"], "request")
        self.assertEqual(request["question"], "Sell-out tháng 10?")
        self.assertEqual(request["query"], {"month": "202610"})
        self.assertEqual(inside["request_id"], "req-1")  # log trong endpoint có cùng request_id
        self.assertEqual(inside["question"], "Sell-out tháng 10?")
        self.assertEqual(done["event"], "response")
        self.assertEqual(done["status"], 200)

    def test_unhandled_error_is_logged_but_hidden_from_client(self):
        response = self.client.get("/api/crash", headers={"X-Request-Id": "req-2"})
        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertNotIn("secret detail", body["message"])
        self.assertIn("req-2", body["message"])

        record = [r for r in self.capture.records if r.fields.get("event") == "response"][0]
        self.assertIsNotNone(record.exc_info)
        self.assertIn("secret detail", record.fields["error"])


class JsonFormatterTests(unittest.TestCase):
    def test_json_line_contains_context_and_fields(self):
        token = set_context(request_id="r9", question="Top sản phẩm?")
        try:
            record = logging.LogRecord(AUDIT_LOGGER_NAME, logging.INFO, __file__, 1, "sql", None, None)
            record.fields = {"event": "sql", "rows": 3}
            ContextFilter().filter(record)
        finally:
            reset_context(token)
        line = json.loads(JsonFormatter().format(record))
        self.assertEqual(line["request_id"], "r9")
        self.assertEqual(line["question"], "Top sản phẩm?")
        self.assertEqual(line["rows"], 3)
