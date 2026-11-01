"""Middleware ghi log mỗi request: câu hỏi của user, tham số, kết quả, thời gian.

Đồng thời đặt request context để log service/analytics/sql cùng request_id,
và chặn lỗi không xử lý: ghi traceback vào log, trả message ngắn cho client.
"""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logger import log_event
from app.core.request_context import context_from_headers, reset_context, set_context

# Không ghi log cho các path này để log không bị nhiễu.
SKIP_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}


def register_audit_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def audit_requests(request: Request, call_next):
        context = context_from_headers(request.headers)
        token = set_context(**context)
        request_id = context["request_id"]
        audited = request.url.path not in SKIP_PATHS
        started = time.perf_counter()

        try:
            if audited:
                log_event(
                    "request",
                    method=request.method,
                    path=request.url.path,
                    query=dict(request.query_params.multi_items()),
                )
            try:
                response = await call_next(request)
            except Exception as exc:
                log_event(
                    "response",
                    level=logging.ERROR,
                    exc_info=True,
                    path=request.url.path,
                    status=500,
                    error=f"{type(exc).__name__}: {exc}"[:500],
                    duration_ms=round((time.perf_counter() - started) * 1000, 1),
                )
                response = JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "message": f"Lỗi hệ thống, vui lòng thử lại. Mã tra cứu: {request_id}",
                    },
                )
            else:
                if audited:
                    log_event(
                        "response",
                        level=logging.WARNING if response.status_code >= 400 else logging.INFO,
                        path=request.url.path,
                        status=response.status_code,
                        duration_ms=round((time.perf_counter() - started) * 1000, 1),
                    )
        finally:
            reset_context(token)

        response.headers["X-Request-Id"] = request_id
        return response
