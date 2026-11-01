---
name: add-data-feature
description: Thêm một tính năng lấy dữ liệu mới từ Oracle ADW (SQL → repository → service → API → MCP tool → quyền → test). Dùng khi được yêu cầu thêm báo cáo, chỉ số, endpoint hoặc tool dữ liệu mới, hay thêm bộ lọc/dimension cho tính năng có sẵn.
---

# Thêm tính năng dữ liệu mới

Làm đúng thứ tự dưới đây. Mỗi bước theo pattern code có sẵn, không tự nghĩ kiến trúc mới.

## 0. Hỏi / xác định trước khi viết code

- Domain và tên tính năng (vd `inventory`, `onhand`) → đặt tên file theo đó.
- Bảng/view nguồn trong ADW và các cột cần dùng. **Không đoán tên bảng/cột**: nếu người dùng chưa đưa SQL hoặc tên cột, hỏi lại.
- Tham số bắt buộc (thường là `month` dạng YYYYMM), các bộ lọc, dimensions, metrics.
- Group nào trên Open WebUI được dùng tính năng này.

## 1. SQL file

- Vị trí: `app/sql/<domain>/<feature>.sql`. Lưu ý repo đang lẫn: `sellout` đọc từ `sql/` ở gốc, `sellin` đọc từ `app/sql/`. Tính năng mới dùng `app/sql/` và đọc bằng đường dẫn tương đối `Path(__file__)`, không dùng đường dẫn phụ thuộc thư mục chạy (như `Path("app/sql/...")` trong `RevenueRepository`).
- Chỉ `SELECT`. Kết thúc bằng `WHERE 1=1` nếu service sẽ ghép thêm điều kiện.
- Đặt alias cột ở dạng snake_case chữ thường — đây là tên mà dimensions/metrics và LLM sẽ thấy.
- Kiểm tra `Dockerfile` có `COPY` thư mục chứa file SQL vào image.

## 2. Repository — `app/repositories/<domain>_repository.py`

Lớp duy nhất được thực thi SQL, chỉ gọi `QueryExecutor.execute(sql, params)`:

```python
from app.db.query_executor import QueryExecutor


class InventoryRepository:
    @staticmethod
    def execute(sql: str, params: dict):
        return QueryExecutor.execute(sql, params)
```

## 3. Service — `app/services/<domain>_service.py`

Theo mẫu `app/services/sellout_service.py`:

- Hằng whitelist: `VALID_DIMENSIONS`, `VALID_METRICS`, `FILTER_COLUMNS` (tên tham số → cột SQL).
- Hàm thuần `build_<feature>_query(...) -> tuple[str, dict]` để test được mà không cần DB:
  - đọc SQL file, `.strip().rstrip(";")`;
  - mỗi bộ lọc khác rỗng → `f"{column} = :{key}"` và `params[key] = value`. Chỉ tên cột từ whitelist được đưa vào chuỗi SQL; **giá trị luôn là bind parameter**;
  - lọc `dimensions`/`metrics` theo whitelist, bỏ giá trị lạ;
  - luôn giới hạn số dòng (`ROWNUM <= 50` hoặc `FETCH FIRST :limit_rows ROWS ONLY`, có `MAX_LIMIT`).
- Class `<Domain>Service` với `@staticmethod` gọi `build_...` rồi repository.

## 4. API endpoint — `app/api/<domain>.py`

- `APIRouter()`, validate tham số (`month % 100 in range(1, 13)`, ngày `YYYYMMDD`, `Literal` cho giá trị cố định), lỗi → `HTTPException(422)`.
- Trả `{"success": True, "data": ...}`. Không SQL, không logic nghiệp vụ.
- Đăng ký router trong `app/main.py` với `prefix="/api"`.

## 5. MCP tool — `app/mcp/tools/<domain>.py`

Chỉ làm bước này nếu `app/mcp/` đã tồn tại (xem `docs/MCP_PLAN.md`); nếu chưa, ghi chú lại cho người dùng.

- Vỏ mỏng gọi service; không SQL.
- Tên tool dạng động từ (`get_inventory`), docstring tiếng Việt nói rõ khi nào dùng, mỗi tham số có ví dụ (`month: 202610`).
- `Literal[...]` cho dimensions/metrics/rank_type để model 9B không bịa tên cột.
- Trả ≤ 50 dòng kèm `row_count`, `truncated`, đơn vị (số lượng / VNĐ).
- Đi qua lớp phân quyền (`app/auth/policy.py`) trước khi gọi service.

## 6. Phân quyền — `app/auth/permissions.yaml`

Nếu file đã có: thêm tool vào các group được phép, kèm bộ lọc bắt buộc nếu có. Hỏi người dùng nếu chưa rõ group nào.

## 7. Test — `tests/test_<domain>.py`

Theo mẫu `tests/test_sellout.py`, không gọi DB thật:

- `build_<feature>_query`: SQL chứa đúng điều kiện, params đúng, dimension/metric lạ bị loại, có giới hạn dòng, giá trị người dùng không xuất hiện trong chuỗi SQL.
- API: `TestClient` + `patch.object(<Domain>Service, ...)` — tham số được chuyển đúng, thiếu `month` → 422, tháng sai → 422 và service không bị gọi.
- MCP tool (nếu có): mock service, kiểm tra quyền bị từ chối và bộ lọc bị ghi đè.

## 8. Hoàn tất

- `python -m pytest tests/` phải pass.
- Nếu tính năng thay thế phần trong `webui/connect.py`, cập nhật hoặc ghi chú.
- Tick mục liên quan trong `docs/MCP_PLAN.md`.
- Tóm tắt cho người dùng: file đã thêm, endpoint/tool mới, việc còn cần họ làm (vd kiểm tra SQL trên ADW thật).
