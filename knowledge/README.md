# Knowledge cho Open WebUI

Thư mục này là **nguồn gốc duy nhất** của Knowledge (vector DB) trên Open WebUI. Knowledge mô tả dữ liệu mà các tool/API của NAW Agent trả về để model hiểu đúng ý nghĩa cột, đơn vị và cách diễn giải.

Không sửa trực tiếp trên giao diện Open WebUI: thay đổi ở đó sẽ bị ghi đè ở lần đồng bộ sau.

## Cấu trúc

| File | Nội dung |
|------|----------|
| `glossary.md` | Thuật ngữ chung: DMX, sell-in/sell-out, loại hàng, định dạng ngày tháng |
| `sellout.md` | Tool `get_sellout` / `GET /api/sellout` |
| `sellin.md` | Tool `get_sellin` / `GET /api/sellin` |
| `top_products.md` | Tool `get_top_products` / `GET /api/sellout/top-products` |

`README.md` này **không** được đồng bộ lên Open WebUI.

## Quy tắc viết

- Mỗi file một tool/domain, tiêu đề `##` ngắn để chia chunk tốt.
- Mỗi cột output ghi: tên cột, ý nghĩa, đơn vị, ví dụ giá trị.
- Ghi rõ cách diễn giải dễ nhầm (vd: tổng theo tháng, giá trị âm là trả hàng…).
- Không đưa mật khẩu, DSN, tên schema nội bộ không cần thiết.
- Khi thêm/sửa dimension, metric hoặc cột output trong service, **phải** cập nhật file ở đây. Test `tests/test_knowledge_docs.py` sẽ báo lỗi nếu thiếu.
- Chỗ đánh dấu `TODO` là ý nghĩa nghiệp vụ chưa được xác nhận — cần người nắm nghiệp vụ điền.

## Đồng bộ lên Open WebUI

Cấu hình trong `.env`:

```
OPENWEBUI_URL=http://localhost:3000
OPENWEBUI_API_KEY=sk-...        # API key của tài khoản admin (Settings → Account)
OPENWEBUI_KNOWLEDGE_ID=...      # id trong URL khi mở Knowledge: /workspace/knowledge/<id>
```

Chạy:

```sh
python scripts/sync_knowledge.py --dry-run   # xem sẽ thay đổi gì
python scripts/sync_knowledge.py             # thêm file mới, cập nhật file đổi nội dung
python scripts/sync_knowledge.py --prune     # thêm: gỡ file trên Open WebUI không còn trong repo
```

Script so khớp theo tên file. File không đổi nội dung sẽ được bỏ qua.

Sau khi đồng bộ, gắn Knowledge này vào model `qwen3.5:9b` trong Workspace → Models (chỉ cần làm một lần).
