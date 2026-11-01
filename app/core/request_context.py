"""Ngữ cảnh của request hiện tại (request_id, user, câu hỏi) dùng chung cho mọi log.

Lưu trong ContextVar nên đi theo request qua service → analytics → SQL, kể cả
khi FastAPI chạy endpoint đồng bộ trong threadpool.
"""

import uuid
from collections.abc import Mapping
from contextvars import ContextVar, Token
from typing import Any
from urllib.parse import unquote

MAX_QUESTION_LENGTH = 2000

# Header → khoá trong context. Header user do Open WebUI gửi
# (ENABLE_FORWARD_USER_INFO_HEADERS) hoặc do webui/connect.py gửi kèm.
HEADER_FIELDS = {
    "x-openwebui-user-id": "user_id",
    "x-openwebui-user-email": "user_email",
    "x-openwebui-user-name": "user_name",
    "x-openwebui-user-role": "user_role",
    "x-openwebui-chat-id": "chat_id",
    "x-openwebui-message-id": "message_id",
    "x-user-question": "question",
}

_context: ContextVar[dict[str, Any] | None] = ContextVar("request_context", default=None)


def get_context() -> dict[str, Any]:
    return dict(_context.get() or {})


def set_context(**fields: Any) -> Token:
    return _context.set({k: v for k, v in fields.items() if v not in (None, "")})


def reset_context(token: Token) -> None:
    _context.reset(token)


def context_from_headers(headers: Mapping[str, str]) -> dict[str, Any]:
    """Đọc request_id và thông tin user/câu hỏi từ header.

    Giá trị có thể được URL-encode (để gửi tiếng Việt qua header) nên luôn unquote.
    """
    lowered = {k.lower(): v for k, v in headers.items()}
    context: dict[str, Any] = {
        "request_id": lowered.get("x-request-id") or uuid.uuid4().hex[:16],
    }
    for header, key in HEADER_FIELDS.items():
        value = lowered.get(header)
        if value:
            context[key] = unquote(value).strip()
    if "question" in context:
        context["question"] = context["question"][:MAX_QUESTION_LENGTH]
    return context
