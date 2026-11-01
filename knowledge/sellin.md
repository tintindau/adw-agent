# Chi tiết sell-in / sell-out theo cửa hàng và sản phẩm – tool `get_sellin`

API: `GET /api/sellin`. Trả dữ liệu **chi tiết từng dòng** (ngày × cửa hàng × sản phẩm), không tổng hợp. Cùng nguồn với `get_sellout`.

## Khi nào dùng
- Cần xem cụ thể một cửa hàng, một sản phẩm, một model, hoặc một khoảng ngày.
- Muốn tổng theo vùng/tỉnh/nhóm hàng thì dùng `get_sellout` thay vì tool này.

## Tham số
- `month_` (bắt buộc): tháng, `YYYYMM`, vd `202610`.
- Ngày: `date_` **hoặc** `from_date` + `to_date` (đều `YYYYMMDD`), không dùng cùng lúc.
- Bộ lọc tìm gần đúng (chứa chuỗi, không phân biệt hoa thường, chấp nhận sai chính tả nhẹ): `store_name`, `region`, `province`, `prod_name`, `model_name`, `prod_class_dmx`, `prod_category`.
- Bộ lọc chứa chuỗi: `store_code`, `prod_code`.
- Cờ 0/1: `is_shibu`, `is_dummy`.

## Cột output
| Cột | Ý nghĩa |
|-----|---------|
| `date_` | Ngày, `YYYYMMDD` |
| `month_` | Tháng, `YYYYMM` |
| `store_name` | Tên cửa hàng DMX |
| `store_code` | Mã cửa hàng (stock code) |
| `region` | Vùng |
| `province` | Tỉnh/thành |
| `prod_code` | Mã sản phẩm Kangaroo |
| `prod_name` | Tên sản phẩm Kangaroo |
| `model_name` | Tên model |
| `prod_class_dmx` | Nhóm hàng (category BOD) |
| `prod_category` | Ngành hàng con |
| `is_shibu` | Cờ hàng Shibu (0/1) |
| `is_dummy` | Cờ hàng mô hình/trưng bày (0/1) |
| `gh_flow` | Luồng hàng |
| `gh_so_qty` | Số lượng sell-out |
| `gh_so_promo_qty` | Số lượng sell-out hàng khuyến mãi |
| `gh_so_out_qty` | Số lượng sell-out (chỉ số chính) |
| `gh_so_out_qty_new` | Sell-out hàng mới |
| `gh_si_amount` | Giá trị sell-in (VNĐ — TODO: xác nhận) |
| `gh_si_qty` | Số lượng sell-in |
| `gh_si_promo_qty` | Số lượng sell-in hàng khuyến mãi |
| `gh_si_qty_new` | Sell-in hàng mới |

Các metric có tiền tố `gh_` cùng ý nghĩa với metric không tiền tố trong `get_sellout` (vd `gh_so_out_qty` ≈ `so_out_qty`). Giá trị rỗng đã được đổi thành 0.

## Lưu ý khi trả lời
- Vì tìm gần đúng, một bộ lọc như `store_name="Q7"` có thể khớp nhiều cửa hàng; hãy nêu rõ các cửa hàng có trong kết quả.
- Dữ liệu chi tiết có thể rất nhiều dòng; nên thu hẹp bằng cửa hàng, sản phẩm hoặc ngày.
