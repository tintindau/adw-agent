# CLAUDE.md

Hướng dẫn cho Claude khi làm việc trong repo này. Trả lời và viết comment/doc bằng **tiếng Việt**; tên biến, hàm, class bằng tiếng Anh.

## Dự án

NAW Agent: hệ thống AI nội bộ cho Kangaroo. API Python (FastAPI) lấy dữ liệu từ Oracle ADW / NetSuite Analytics Warehouse cho Open WebUI (model `qwen3.5:9b`). Đang bổ sung **MCP server** và phân quyền theo user/group của Open WebUI — xem `docs/MCP_PLAN.md` trước khi làm việc liên quan.

```
User → Open WebUI → (tool call / MCP) → NAW Agent → Oracle ADW
```

Server chạy bằng Docker Desktop trên Windows.

## Lệnh thường dùng

```sh
pip install -r requirements.txt
python -m pytest tests/                 # chạy test
uvicorn app.main:app --reload --port 8000
docker compose up -d --build            # API :8000, Open WebUI :3000
curl http://localhost:8000/api/health
```

Test không cần kết nối Oracle: mock service/repository (xem `tests/test_sellout.py`). Không viết test gọi DB thật.

## Kiến trúc

```
app/
├── api/           endpoint HTTP, chỉ validate tham số rồi gọi service
├── services/      logic nghiệp vụ, ghép điều kiện lọc từ whitelist
├── repositories/  lớp DUY NHẤT được thực thi SQL (qua QueryExecutor)
├── db/            connection pool (oracledb + wallet), QueryExecutor
├── core/          config (pydantic-settings), logger, security
├── models/        request/response model
├── mcp/           (sắp có) MCP server + tool, xem docs/MCP_PLAN.md
└── main.py
sql/               file SQL template mà service đang đọc
webui/connect.py   Python tool cũ cài trong Open WebUI (sẽ thay bằng MCP)
```

Thêm tính năng mới theo thứ tự: SQL file → Repository → Service → API endpoint → MCP tool → khai báo quyền → test.

## Quy tắc bắt buộc

**SQL**
- Không viết SQL trong api/ hoặc mcp/. SQL nền nằm trong file `.sql`; service chỉ được ghép thêm điều kiện `WHERE`/`GROUP BY` từ danh sách cột whitelist (`VALID_DIMENSIONS`, `VALID_METRICS`, `FILTER_COLUMNS`) như `sellout_service.py`.
- Giá trị người dùng luôn đi qua bind parameter (`:month`), không bao giờ f-string vào SQL.
- Chỉ `SELECT`. Cấm DML/DDL (INSERT, UPDATE, DELETE, MERGE, CREATE, ALTER, DROP, TRUNCATE).
- Luôn giới hạn số dòng trả về (`ROWNUM <= n` hoặc `FETCH FIRST n ROWS ONLY`).
- LLM không được sinh SQL; không thêm tool nhận SQL tự do.

**Lưu ý vị trí SQL:** repo đang lẫn hai nơi — `sellout` đọc từ `sql/` ở thư mục gốc, `sellin` đọc từ `app/sql/`. Tính năng mới đặt ở `app/sql/`. Kế hoạch là gom về một chỗ (Giai đoạn 0 trong plan) — khi sửa SQL, kiểm tra service/repository đang đọc file nào.

Thêm tính năng dữ liệu mới: dùng skill `add-data-feature` (`.claude/skills/add-data-feature/SKILL.md`).

**Bảo mật**
- Không hardcode hay log: `ORACLE_PASSWORD`, `WALLET_PASSWORD`, nội dung wallet, DSN, API key.
- Không commit `.env` hay thư mục `wallet/`.
- Không trả stack trace cho client; trả `{"success": false, "message": "..."}` ngắn gọn.
- Bộ lọc dữ liệu theo quyền group phải được áp ở server, ghi đè tham số do model truyền vào.

**Code**
- Dùng logger trong `app/core/logger.py`, không dùng `print()`.
- Response thành công: `{"success": true, "data": [...]}`.
- Cấu hình mới thêm vào `app/core/config.py` và `.env.example`.
- Tham số tháng dạng `YYYYMM` (int), ngày dạng `YYYYMMDD` (string), validate ở api/.

## MCP tool (cho model 9B)

- Ít tool, mỗi tool một việc; tên và mô tả rõ ràng bằng tiếng Việt, có ví dụ giá trị.
- Dùng `Literal`/enum cho dimensions, metrics, rank_type để model không bịa tên cột.
- Tool chỉ là vỏ mỏng gọi service có sẵn.
- Kết quả gọn (≤ 50 dòng), kèm `row_count` và `truncated`.

## Khi kết thúc thay đổi

- Chạy `python -m pytest tests/` và đảm bảo pass.
- Tick các mục tương ứng trong `docs/MCP_PLAN.md` nếu vừa hoàn thành.
