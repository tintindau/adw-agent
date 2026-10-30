#!/usr/bin/env python3

# Để chạy script này trong terminal:
# python test/test_connection.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import oracledb
from app.core.config import settings

try:
    print("Đang khởi tạo kết nối Thin mode tới Oracle ADW...")

    pool = oracledb.create_pool(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
        config_dir=settings.wallet_location,
        wallet_location=settings.wallet_location,
        wallet_password=settings.wallet_password,
        min=1,
        max=5,
        increment=1
    )
   
    # 3. Lấy một kết nối từ pool để kiểm tra
    with pool.acquire() as conn:
        print("✅ Kết nối ADW thành công!")
        print(f"📌 Oracle DB Version: {conn.version}")
        
        # 4. Thực thi câu query test hệ thống
        with conn.cursor() as cur:
            cur.execute("SELECT sys_context('userenv', 'db_name') FROM dual")
            row = cur.fetchone()
            print(f"📌 Tên Database đang kết nối: {row[0]}")

    # Đóng pool sau khi dùng xong
    pool.close()

except oracledb.Error as e:
    error_obj, = e.args
    print(f"❌ Lỗi kết nối Oracle: {error_obj.message}")
except Exception as e:
    print(f"❌ Lỗi khác: {e}")