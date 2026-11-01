# Sell-in / sell-out theo ngày tại DMX – tool `get_sellout`

API: `GET /api/sellout`. Nguồn: bảng lịch sử sell-in/sell-out theo ngày, cửa hàng và sản phẩm tại DMX.

## Khi nào dùng
- Hỏi số lượng bán ra (sell-out) hoặc số lượng / giá trị sell-in tại DMX trong một tháng.
- Muốn so sánh theo vùng, tỉnh, nhóm hàng, ngành hàng, loại hàng, luồng hàng.

## Tham số
- `month` (bắt buộc): `YYYYMM`, vd `202610`.
- `dimensions`: các cột để nhóm (GROUP BY), chọn trong danh sách dimension bên dưới.
- `metrics`: các chỉ số cần tính tổng (SUM), chọn trong danh sách metric bên dưới.
- Bộ lọc (so khớp chính xác): `date_`, `region`, `province`, `prod_class_dmx`, `prod_category`, `is_shibu`, `is_dummy`, `prod_type`, `gh_flow`.

## Cách kết quả được tạo
- Có `dimensions`: tổng các `metrics` theo từng tổ hợp dimension, sắp xếp giảm dần theo metric đầu tiên, tối đa 50 dòng.
- Có `dimensions` nhưng không có `metrics`: mặc định dùng `so_out_qty` và `si_amount`.
- Có `metrics` nhưng không có `dimensions`: một dòng tổng cho cả tháng (sau bộ lọc).
- Không có cả hai: trả 30 dòng chi tiết đầu tiên (chưa tổng hợp) — chỉ để xem mẫu, không dùng để tính tổng.

## Dimension
| Cột | Ý nghĩa | Ví dụ |
|-----|---------|-------|
| `date_` | Ngày, `YYYYMMDD` | `20261015` |
| `month_` | Tháng, `YYYYMM` | `202610` |
| `region` | Vùng của cửa hàng | |
| `province` | Tỉnh/thành của cửa hàng | |
| `prod_class_dmx` | Nhóm hàng (category BOD) | |
| `prod_category` | Ngành hàng con (sub category) | |
| `prod_type` | Loại hàng: `Shibu`, `Trung_bay`, `Con_lai` (xem glossary) | `Shibu` |
| `gh_flow` | Luồng hàng | TODO: liệt kê các giá trị và ý nghĩa |

## Metric
| Cột | Ý nghĩa | Đơn vị |
|-----|---------|--------|
| `so_qty` | Số lượng sell-out | sản phẩm |
| `so_promo_qty` | Số lượng sell-out hàng khuyến mãi | sản phẩm |
| `so_out_qty` | Số lượng sell-out (chỉ số chính khi hỏi "bán ra bao nhiêu") — TODO: xác nhận khác `so_qty` thế nào | sản phẩm |
| `so_out_qty_new` | Sell-out hàng mới — TODO: xác nhận định nghĩa "new" | sản phẩm |
| `si_amount` | Giá trị sell-in | VNĐ — TODO: xác nhận đơn vị |
| `si_qty` | Số lượng sell-in | sản phẩm |
| `si_promo_qty` | Số lượng sell-in hàng khuyến mãi | sản phẩm |
| `si_qty_new` | Sell-in hàng mới — TODO: xác nhận định nghĩa "new" | sản phẩm |

## Lưu ý khi trả lời
- Đây là dữ liệu tại DMX, không phải toàn bộ kênh bán của Kangaroo.
- Bộ lọc so khớp chính xác: tên vùng/tỉnh phải đúng như dữ liệu. Nếu kết quả rỗng, thử gọi với `dimensions=["region"]` để xem các giá trị hợp lệ.
