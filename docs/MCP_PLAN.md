# Kế hoạch xây dựng MCP Server cho NAW Agent

> Mục tiêu: Open WebUI (model `qwen3.5:9b`) gọi dữ liệu ADW/NSAW qua giao thức MCP, và mỗi người dùng chỉ thấy dữ liệu mà group của họ trên Open WebUI được phép xem.

## 1. Hiện trạng repo (tính đến commit `3a0484d`)

**Đã có**
- FastAPI REST API (`app/main.py`) với các endpoint: `/api/health`, `/api/sellin`, `/api/sales/customer`, `/api/sellout`, `/api/sellout/top-products`.
- Kiến trúc phân lớp `api → services → repositories → db` theo `SKILL.md`; SQL nằm trong file, LLM không sinh SQL.
- Kết nối ADW bằng `oracledb.create_pool()` + wallet (`app/db/connection.py`).
- Docker Compose chạy `oracle-agent` (port 8000) và `open-webui` (port 3000).
- Open WebUI gọi API qua Python tool `webui/connect.py`.
- Test pytest cho sellin, sellout, top-products.

**Vấn đề cần xử lý trước / song song**
| # | Vấn đề | Ảnh hưởng |
|---|--------|-----------|
| 1 | `webui/connect.py` gửi `start_date`/`end_date`, nhưng `/api/sellout` yêu cầu `month` (YYYYMM) | Tool hiện tại luôn lỗi 422 |
| 2 | SQL nằm ở 2 nơi: `sql/` (được service đọc) và `app/sql/` (trùng lặp, không dùng) — trái quy tắc `app/sql` trong `SKILL.md` | Dễ sửa nhầm file |
| 3 | `app/core/logger.py`, `app/core/security.py`, `app/models/*`, `app/rag/*`, `tests/test_agent.py` đang rỗng | Chưa có log, chưa có xác thực |
| 4 | API không có xác thực, ai gọi được port 8000 là xem được toàn bộ dữ liệu | Rủi ro bảo mật |
| 5 | `QueryExecutor` không đặt timeout truy vấn | Query nặng có thể treo pool |
| 6 | Service `open-webui` không có volume | Mất user/group/cấu hình khi recreate container |
| 7 | `requirements.txt` không ghim phiên bản | Build không ổn định |

## 2. Kiến trúc đích

```
Open WebUI
    |-- Knowledge (Vector DB)  ← knowledge/*.md, scripts/sync_knowledge.py
    |
Qwen (qwen3.5:9b)
    |
MCP Client (trong Open WebUI)
    |  MCP (Streamable HTTP) + định danh user
Data MCP Server  ──  /mcp (FastMCP)  |  /api (REST cũ)
    |
auth layer: user → groups (Open WebUI API) → quyền (policy)
    |
Service: build SQL từ whitelist, điều phối
    |
Analytics Layer (Pandas)  ← app/analytics
    |
Repository
    |
Oracle ADW / NSAW
```

Nguyên tắc:
- **Tái sử dụng service hiện có.** MCP tool chỉ là lớp vỏ mỏng như `app/api/*`, không viết SQL mới trong tool.
- **SQL tổng hợp, Pandas tính phần sau.** SUM/GROUP BY ở ADW; analytics layer tính tỉ trọng, tăng trưởng, xếp hạng, định dạng kết quả để model 9B không phải tự làm phép tính.
- **Giữ nguyên quy tắc `SKILL.md`**: LLM không sinh SQL, chỉ chọn tool và tham số.
- **Một container, hai cổng giao tiếp**: mount MCP vào FastAPI hiện tại ở `/mcp`, REST `/api` vẫn chạy cho đến khi bỏ `webui/connect.py`.

## 3. Cấu trúc thư mục bổ sung

```
app/
├── mcp/
│   ├── server.py        # khởi tạo FastMCP, đăng ký tool
│   ├── context.py       # lấy user hiện tại từ request MCP
│   └── tools/
│       ├── sellin.py
│       ├── sellout.py
│       └── catalog.py   # list_metrics, list_dimensions, list_regions…
├── auth/
│   ├── openwebui_client.py  # gọi API Open WebUI lấy user, group (có cache)
│   ├── policy.py            # group → tool được dùng + bộ lọc dữ liệu
│   └── permissions.yaml     # cấu hình quyền, không hardcode trong code
└── core/
    ├── logger.py        # hoàn thiện
    └── security.py      # xác thực token / API key
```

## 4. Các giai đoạn

### Giai đoạn 0 — Dọn nền (≈2–3 ngày)
- [ ] Gộp SQL về một chỗ (`app/sql/`), cập nhật đường dẫn trong service và `Dockerfile`, xoá bản trùng.
- [ ] Hoàn thiện `app/core/logger.py` (JSON log, có `request_id`, `user`, `tool`, `duration_ms`).
- [ ] Thêm `call_timeout` cho connection (vd 30s) và giới hạn số dòng trả về ở `QueryExecutor`.
- [ ] Ghim phiên bản trong `requirements.txt`, thêm `mcp` (Python SDK) và `httpx`, `pyyaml`.
- [ ] Thêm volume `open-webui-data:/app/backend/data` cho service `open-webui`.
- [ ] Sửa `webui/connect.py` dùng `month` cho đúng API (giữ chạy tạm trong lúc làm MCP).

### Giai đoạn 1 — MCP server tối thiểu (≈3 ngày)
- [ ] `app/mcp/server.py`: tạo `FastMCP("naw-agent")`, mount Streamable HTTP app vào FastAPI tại `/mcp`.
- [ ] Tool đầu tiên: `ping`, `list_metrics`, `list_dimensions` (trả về `VALID_METRICS`, `VALID_DIMENSIONS` kèm mô tả tiếng Việt).
- [ ] Trong Open WebUI: Admin → Settings → External Tools, thêm server kiểu MCP (Streamable HTTP) trỏ `http://oracle-agent:8000/mcp` (cùng network compose).
- [ ] Kiểm tra qwen gọi được tool và đọc được kết quả.

### Giai đoạn 2 — Định danh & phân quyền theo user/group Open WebUI (≈1 tuần)
- [ ] **Spike (làm đầu tiên):** xác định cách bản Open WebUI đang chạy gửi danh tính user tới MCP server (token phiên của user, header user-info, hay chỉ bearer cố định). Kết quả quyết định thiết kế bên dưới.
- [ ] `openwebui_client.py`: dùng API key admin (`OPENWEBUI_URL`, `OPENWEBUI_API_KEY` trong `.env`) để tra user và group; cache TTL 5 phút.
- [ ] `permissions.yaml`: map group → tool được phép + bộ lọc bắt buộc. Ví dụ:
  ```yaml
  groups:
    sales_mien_bac:
      tools: [get_sellout, get_sellin, get_top_products]
      filters: { region: "Miền Bắc" }
    bod:
      tools: ["*"]
      filters: {}
  default:
    tools: [ping, list_metrics, list_dimensions]
  ```
- [ ] `policy.py`: trước mỗi tool, kiểm tra quyền dùng tool; **ghi đè** bộ lọc bắt buộc vào tham số (user không thể bỏ qua bằng cách đổi prompt).
- [ ] User không thuộc group nào → chỉ dùng tool mặc định.
- [ ] Bảo vệ `/api` REST bằng API key trong `app/core/security.py`.

### Giai đoạn 2b — Analytics layer
- [x] `app/analytics/`: `to_frame`, `to_records`, `to_llm_result`, `top_n_with_others`, `add_share_pct`, `compare_periods`, `add_sell_through_pct`, `export_csv_7z`, có test.
- [x] `QueryExecutor.execute_df()` và `SelloutRepository.execute_df()`.
- [x] Chuyển `build_result` của top-products sang dùng analytics (giữ nguyên output).
- [ ] Tool so sánh kỳ (tháng này / tháng trước) cho sellout dùng `compare_periods`.
- [ ] Thêm `row_count`/`truncated` (qua `to_llm_result`) cho output sellout, sellin; cập nhật `knowledge/` tương ứng.

### Giai đoạn 3 — Tool dữ liệu (≈1 tuần)
Bọc các service có sẵn, tham số gọn để model 9B chọn đúng:

| Tool | Service dùng lại | Tham số chính |
|------|------------------|---------------|
| `get_sellout` | `SelloutService.get_aggregated_siso` | `month`, `dimensions`, `metrics`, `region`, `province`, `prod_category` |
| `get_sellin` | `SellinService.get_by_month` | `month`, `from_date`, `to_date`, `region`, `store_code`, `prod_code` |
| `get_top_products` | `SelloutProdTopClassCatService.get_top_products` | `month`, `rank_type`, `limit`, `category_bod` |
| `get_sales_by_customer` | `RevenueService.sales_by_customer` | `period` |

- [ ] Mô tả tool và tham số bằng tiếng Việt, có ví dụ giá trị (`month=202610`).
- [ ] Dùng `Literal`/enum cho `dimensions`, `metrics`, `rank_type` để model không bịa tên cột.
- [ ] Kết quả trả về: tối đa 50 dòng, kèm `row_count`, `truncated`, và đơn vị (số lượng / VNĐ).
- [ ] Lỗi trả về câu ngắn, dễ hiểu cho model (không lộ stack trace, theo `SKILL.md`).
- [ ] Sau khi MCP chạy ổn: ngừng dùng `webui/connect.py`.
- [x] Knowledge mô tả output tool quản lý trong `knowledge/`, đồng bộ bằng `scripts/sync_knowledge.py`, có test kiểm tra đủ cột.
- [ ] Điền các mục `TODO` trong `knowledge/` (ý nghĩa nghiệp vụ metric, `gh_flow`, Shibu).
- [ ] Đổi tên tool trong `knowledge/` cho khớp tên MCP tool thực tế khi làm xong.

### Giai đoạn 4 — Kiểm thử & vận hành (≈1 tuần)
- [ ] Unit test cho `policy.py` (đủ quyền / thiếu quyền / bộ lọc bị ghi đè) và cho từng tool (mock service).
- [ ] Bộ 30–50 câu hỏi thực tế của người dùng → chạy với qwen, ghi lại tool được chọn và tham số; chỉnh mô tả tool cho đến khi đạt tỉ lệ đúng mong muốn.
- [ ] Audit log mỗi lần gọi tool: user, group, tool, tham số, số dòng, thời gian.
- [ ] Health check trong `docker-compose.yml`; ghi chú cài trên Docker Desktop Windows (đường dẫn `wallet/`, `.env`).
- [ ] Cập nhật `README.md` và `SKILL.md` với quy tắc thêm MCP tool mới.

## 5. Quy trình thêm tính năng mới (mở rộng `SKILL.md`)
1. SQL file trong `app/sql/<domain>/`
2. Repository
3. Service
4. REST endpoint (nếu cần)
5. **MCP tool** trong `app/mcp/tools/<domain>.py`
6. Khai báo tool trong `permissions.yaml`
7. Mô tả output trong `knowledge/<domain>.md`, đồng bộ bằng `scripts/sync_knowledge.py`
8. Test

## 6. Câu hỏi cần chốt
- Bản Open WebUI đang dùng gửi danh tính user tới MCP server bằng cách nào? (spike giai đoạn 2)
- Danh sách group trên Open WebUI và quyền dữ liệu của từng group — ai là người duyệt?
- Có cần phân quyền theo dòng ngoài `region` không (cửa hàng, ngành hàng…)?
- Có giữ REST `/api` lâu dài cho hệ thống khác không, hay chỉ còn MCP?
