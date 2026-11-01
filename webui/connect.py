"""
title: API Bán hàng (Sellout Data Agent)
description: Lấy dữ liệu sell-in / sell-out tại DMX từ hệ thống Data Agent nội bộ theo tháng.
author: Admin
version: 1.2.0
requirements: requests, pydantic
"""

import json
from urllib.parse import quote

import requests
from pydantic import BaseModel, Field

MAX_QUESTION_LENGTH = 2000


def _last_user_question(messages: list) -> str:
    """Lấy câu hỏi gần nhất của user trong cuộc hội thoại."""
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if isinstance(content, list):  # tin nhắn có ảnh/file: lấy phần text
            content = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
        return str(content)[:MAX_QUESTION_LENGTH]
    return ""


def _audit_headers(user: dict, messages: list, metadata: dict) -> dict:
    """Header để Data Agent ghi log: ai hỏi, hỏi gì, trong chat nào.

    Giá trị được URL-encode vì header HTTP không chứa được tiếng Việt có dấu.
    """
    values = {
        "X-OpenWebUI-User-Id": (user or {}).get("id"),
        "X-OpenWebUI-User-Email": (user or {}).get("email"),
        "X-OpenWebUI-User-Name": (user or {}).get("name"),
        "X-OpenWebUI-User-Role": (user or {}).get("role"),
        "X-OpenWebUI-Chat-Id": (metadata or {}).get("chat_id"),
        "X-OpenWebUI-Message-Id": (metadata or {}).get("message_id"),
        "X-User-Question": _last_user_question(messages),
    }
    return {key: quote(str(value), safe="") for key, value in values.items() if value}


class Tools:
    class Valves(BaseModel):
        API_BASE_URL: str = Field(
            default="http://10.0.22.103:8000",
            description="Địa chỉ gốc của Data Agent API",
        )

    def __init__(self):
        self.valves = self.Valves()

    def get_sellout_data(
        self,
        month: int,
        __user__: dict = {},
        __messages__: list = [],
        __metadata__: dict = {},
    ) -> str:
        """
        Lấy tổng hợp sell-in / sell-out tại DMX của một tháng.

        :param month: Tháng cần xem, BẮT BUỘC định dạng YYYYMM (ví dụ: 202610 là tháng 10/2026).
        :return: Chuỗi JSON chứa dữ liệu hoặc thông báo lỗi.
        """
        url = f"{self.valves.API_BASE_URL}/api/sellout"
        response = None
        try:
            response = requests.get(
                url,
                params={"month": month},
                headers=_audit_headers(__user__, __messages__, __metadata__),
                timeout=30,
            )
            response.raise_for_status()
            return json.dumps(response.json(), ensure_ascii=False)
        except requests.exceptions.Timeout:
            return "Lỗi: Quá thời gian kết nối (Timeout) đến Data Agent."
        except requests.exceptions.RequestException as e:
            details = response.text if response is not None else ""
            return f"Không thể lấy dữ liệu từ Data Agent. Lỗi: {e}. Chi tiết: {details}"
