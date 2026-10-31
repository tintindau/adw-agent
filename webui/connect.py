"""
title: API Bán hàng (Sellout Data Agent)
description: Lấy dữ liệu bán ra (sellout) từ hệ thống Data Agent nội bộ (Yêu cầu khoảng thời gian).
author: Admin
version: 1.1.0
requirements: requests, pydantic
"""

import requests
import json
from pydantic import BaseModel, Field

class Tools:
    class Valves(BaseModel):
        # Thiết lập địa chỉ IP gốc
        API_BASE_URL: str = Field(
            default="http://10.0.22.103:8000", 
            description="Địa chỉ gốc của Data Agent API"
        )

    def __init__(self):
        self.valves = self.Valves()

    def get_sellout_data(self, start_date: str, end_date: str) -> str:
        """
        Sử dụng công cụ này để lấy dữ liệu bán ra (sellout) từ hệ thống kho dữ liệu nội bộ trong một khoảng thời gian cụ thể.
        
        :param start_date: Ngày bắt đầu. BẮT BUỘC định dạng YYYYMMDD (Ví dụ: 20261001).
        :param end_date: Ngày kết thúc. BẮT BUỘC định dạng YYYYMMDD (Ví dụ: 20261030).
        :return: Chuỗi JSON chứa dữ liệu sellout hoặc thông báo lỗi.
        """
        # Khởi tạo URL chuẩn
        url = f"{self.valves.API_BASE_URL}/api/sellout"
        
        # Truyền cả start_date và end_date vào Query Parameters
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        try:
            # Gọi API nội bộ
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Ép dữ liệu về chuỗi JSON để mô hình AI đọc hiểu
            return json.dumps(data, ensure_ascii=False)
            
        except requests.exceptions.Timeout:
            return "Lỗi: Quá thời gian kết nối (Timeout) đến Data Agent."
        except requests.exceptions.RequestException as e:
            error_details = response.text if 'response' in locals() and response else ""
            return f"Không thể kết nối đến Data Agent nội bộ. Lỗi: {str(e)}. Chi tiết: {error_details}"