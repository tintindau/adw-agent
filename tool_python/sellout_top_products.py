"""
title: Sellout Top/Bad Products (DMX)
description: Xếp hạng sản phẩm theo doanh thu sellout DMX của một tháng (Top N cao nhất hoặc Bad N thấp nhất) từ Data Agent nội bộ.
author: Admin
version: 1.1.0
requirements: requests, pydantic
"""

import json
from typing import List, Optional
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
        TIMEOUT_SECONDS: int = Field(
            default=60, description="Thời gian chờ tối đa khi gọi API (giây)"
        )

    def __init__(self):
        self.valves = self.Valves()

    def get_top_products(
        self,
        month: int,
        rank_type: str = "top",
        limit: int = 20,
        dimensions: Optional[List[str]] = None,
        category_bod: Optional[str] = None,
        prod_code: Optional[str] = None,
        prod_name_kgr: Optional[str] = None,
        is_shibu: Optional[int] = None,
        __user__: dict = {},
        __messages__: list = [],
        __metadata__: dict = {},
    ) -> str:
        """
        Lấy Top N (doanh thu cao nhất) hoặc Bad N (doanh thu thấp nhất) sản phẩm sellout DMX theo tháng.
        Dùng khi người dùng hỏi về top/bán chạy nhất/bán kém nhất/doanh thu sellout theo sản phẩm hoặc ngành hàng.

        :param month: Tháng cần xem, BẮT BUỘC định dạng YYYYMM (ví dụ: 202610 là tháng 10 năm 2026).
        :param rank_type: "top" là doanh thu cao nhất (mặc định), "bad" là doanh thu thấp nhất.
        :param limit: Số dòng cần lấy, từ 1 đến 500 (mặc định 20). Ví dụ Top 10 thì truyền 10.
        :param dimensions: Danh sách chiều gom nhóm. Giá trị hợp lệ: prod_code, prod_name, date_, month_, year_, prod_id_kgr, prod_name_kgr, category_bod, is_shibu. Bỏ trống thì gom theo prod_code và prod_name_kgr.
        :param category_bod: Lọc theo ngành hàng (tên chính xác, ví dụ: "Tủ lạnh, đông, mát").
        :param prod_code: Lọc theo mã sản phẩm.
        :param prod_name_kgr: Lọc theo tên sản phẩm Kangaroo.
        :param is_shibu: Lọc hàng Shibu: 1 là có, 0 là không.
        :return: Chuỗi JSON gồm chart_data (labels, amount_vnd tính bằng VND), total_rows_fetched và download_file_7z nếu kết quả hơn 30 dòng.
        """
        url = f"{self.valves.API_BASE_URL}/api/sellout/top-products"

        params = {"month": month, "rank_type": rank_type, "limit": limit}
        if dimensions:
            params["dimensions"] = dimensions
        optional = {
            "category_bod": category_bod,
            "prod_code": prod_code,
            "prod_name_kgr": prod_name_kgr,
            "is_shibu": is_shibu,
        }
        params.update({k: v for k, v in optional.items() if v not in (None, "")})

        response = None
        try:
            response = requests.get(
                url,
                params=params,
                headers=_audit_headers(__user__, __messages__, __metadata__),
                timeout=self.valves.TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return json.dumps(response.json(), ensure_ascii=False)

        except requests.exceptions.Timeout:
            return "Lỗi: Quá thời gian kết nối (Timeout) đến Data Agent."
        except requests.exceptions.RequestException as e:
            detail = response.text if response is not None else ""
            return f"Không thể lấy dữ liệu từ Data Agent. Lỗi: {e}. Chi tiết: {detail}"
