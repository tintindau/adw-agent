# CLAUDE.md

Hướng dẫn cho Claude khi làm việc trong repo này. Trả lời và viết comment/doc bằng **tiếng Việt**; tên biến, hàm, class bằng tiếng Anh.

## Dự án

NAW Agent: hệ thống AI nội bộ cho Kangaroo. API Python (FastAPI) lấy dữ liệu từ Oracle ADW / NetSuite Analytics Warehouse cho Open WebUI (model `qwen3.5:9b`). Đang bổ sung **MCP server** và phân quyền theo user/group của Open WebUI — xem `docs/MCP_PLAN.md` trước khi làm việc liên quan.

```
Open WebUI ── Knowledge (vector DB, từ knowledge/)
    ↓
Qwen → MCP Client (trong Open WebUI)
    ↓
Data MCP Server (app/mcp, sắp có) / REST API (app/api)
    ↓
Service (app/services): build SQL từ whitelist, điều phối
    ↓                     ↘
Repository → Oracle ADW    Analytics Layer (app/analytics, Pandas)
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
├── analytics/     hàm thuần trên DataFrame: chỉ số phái sinh, xếp hạng, định dạng kết quả
├── db/            connection pool (oracledb + wallet), QueryExecutor (execute / execute_df), cache.py
├── core/          config (pydantic-settings), logger, security
├── models/        request/response model
├── mcp/           (sắp có) MCP server + tool, xem docs/MCP_PLAN.md
└── main.py
sql/               file SQL template mà service đang đọc
webui/connect.py   Python tool cũ cài trong Open WebUI (sẽ thay bằng MCP)
knowledge/         Knowledge (vector DB) của Open WebUI: mô tả output tool cho model
scripts/sync_knowledge.py  đồng bộ knowledge/ lên Open WebUI
```

Thêm tính năng mới theo thứ tự: SQL file → Repository → Service → API endpoint → MCP tool → khai báo quyền → knowledge → test.

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
- Dùng logger trong `app/core/logger.py`, không dùng `print()`. Sự kiện audit ghi bằng `log_event(...)`.
- Response thành công: `{"success": true, "data": [...]}`.
- Cấu hình mới thêm vào `app/core/config.py` và `.env.example`.
- Tham số tháng dạng `YYYYMM` (int), ngày dạng `YYYYMMDD` (string), validate ở api/.

**Analytics layer (`app/analytics/`)**
- Tổng hợp nặng (SUM, GROUP BY, lọc) làm ở SQL để ADW xử lý; Pandas chỉ xử lý sau đó: tỉ trọng %, tăng trưởng so kỳ trước, sell-through, top-N + Others, cắt kết quả, xuất file.
- Hàm thuần nhận/trả DataFrame: không gọi DB, không import repository, api hay mcp.
- Service lấy DataFrame qua `Repository.execute_df()` rồi gọi analytics. Trả cho model qua `to_llm_result()` (có `row_count`, `truncated`).
- Mỗi hàm analytics mới phải có test trong `tests/test_analytics.py`.
- Giá trị không tính được (chia cho 0) trả `None`, không trả `inf`/`NaN`.

**Cache truy vấn (`app/db/cache.py`)**
- `QueryExecutor` tự cache kết quả theo SQL + params (TTL + LRU, trong bộ nhớ). Cấu hình: `QUERY_CACHE_ENABLED`, `QUERY_CACHE_TTL_SECONDS`, `QUERY_CACHE_MAX_ENTRIES`.
- Bộ lọc quyền luôn phải nằm trong SQL/params để key cache tách theo quyền; không bao giờ lọc dữ liệu theo user **sau** khi lấy từ cache.
- Truy vấn cần dữ liệu tức thời → `execute(..., use_cache=False)`.
- Theo dõi tỉ lệ hit qua `GET /api/health` (`query_cache`).

**Log audit (`app/core/logger.py`, `tracing.py`, `audit_middleware.py`)**
- Mỗi request có `request_id` (header `X-Request-Id` hoặc tự sinh, trả lại trong response). Mọi dòng log của request tự gắn `request_id`, user và `question`.
- Chuỗi sự kiện: `request` (câu hỏi, tham số) → `service` → `analytics` → `sql` (câu lệnh, params, số dòng, thời gian, cache hit/miss) → `response` (status, thời gian).
- Câu hỏi và user lấy từ header `X-User-Question`, `X-OpenWebUI-User-*`, `X-OpenWebUI-Chat-Id` (giá trị URL-encode). `webui/connect.py` gửi các header này; MCP server sau này cũng phải đặt cùng context.
- Hàm service/analytics mới phải gắn `@traced("service")` / `@traced("analytics")` (dưới `@staticmethod`).
- Log ghi JSON ra stdout và file tách theo ngày + user: `logs/<YYYY-MM-DD>/<email user>.log` (`_anonymous.log`: request không có user, `_system.log`: ngoài request). Ngày theo `LOG_TIMEZONE`, thư mục cũ hơn `LOG_RETENTION_DAYS` tự xoá. Cấu hình khác: `LOG_LEVEL`, `LOG_DIR`, `LOG_JSON`, `LOG_SQL`.
- Không log credential. Lỗi không xử lý: traceback chỉ nằm trong log; client nhận message ngắn kèm mã `request_id` để tra.

## MCP tool (cho model 9B)

- Ít tool, mỗi tool một việc; tên và mô tả rõ ràng bằng tiếng Việt, có ví dụ giá trị.
- Dùng `Literal`/enum cho dimensions, metrics, rank_type để model không bịa tên cột.
- Tool chỉ là vỏ mỏng gọi service có sẵn.
- Kết quả gọn (≤ 50 dòng), kèm `row_count` và `truncated`.

## Knowledge (vector DB trên Open WebUI)

- `knowledge/*.md` là nguồn gốc duy nhất; không sửa Knowledge trực tiếp trên giao diện Open WebUI. Chi tiết: `knowledge/README.md`.
- Thêm/sửa/xoá dimension, metric, bộ lọc hoặc cột output → cập nhật file knowledge tương ứng trong cùng commit. `tests/test_knowledge_docs.py` kiểm tra điều này.
- Ý nghĩa nghiệp vụ chưa chắc chắn → ghi `TODO`, không đoán.
- Đồng bộ: `python scripts/sync_knowledge.py --dry-run` rồi chạy thật. Không tự chạy lệnh đồng bộ thật nếu người dùng chưa yêu cầu.
- `app/rag/` là file rỗng cũ, không dùng.

## Khi kết thúc thay đổi

- Chạy `python -m pytest tests/` và đảm bảo pass.
- Nếu output tool thay đổi: nhắc người dùng chạy `scripts/sync_knowledge.py`.
- Tick các mục tương ứng trong `docs/MCP_PLAN.md` nếu vừa hoàn thành.
