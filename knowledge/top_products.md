# Xếp hạng sản phẩm theo doanh thu sell-out – tool `get_top_products`

API: `GET /api/sellout/top-products`. Nguồn: bảng sell-out DMX, chỉ số là doanh thu (VNĐ).

## Khi nào dùng
- "Top sản phẩm bán chạy", "sản phẩm bán kém nhất", xếp hạng theo doanh thu trong tháng.

## Tham số
- `month` (bắt buộc): `YYYYMM`, vd `202610`.
- `rank_type`: `top` (doanh thu cao nhất trước, mặc định) hoặc `bad` (thấp nhất trước).
- `limit`: số dòng, 1–500, mặc định 20.
- `dimensions`: cột để nhóm, mặc định `prod_code` + `prod_name_kgr`.
- Bộ lọc (so khớp chính xác): `prod_code`, `prod_name`, `date_`, `prod_id_kgr`, `prod_name_kgr`, `category_bod`, `is_shibu`.

## Dimension
| Cột | Ý nghĩa |
|-----|---------|
| `prod_code` | Mã sản phẩm theo DMX |
| `prod_name` | Tên sản phẩm theo DMX |
| `date_` | Ngày, `YYYYMMDD` |
| `month_` | Tháng (1–12) |
| `year_` | Năm, vd `2026` |
| `prod_id_kgr` | Mã sản phẩm Kangaroo |
| `prod_name_kgr` | Tên sản phẩm Kangaroo |
| `category_bod` | Nhóm hàng (category BOD) |
| `is_shibu` | Cờ hàng Shibu (0/1) |

## Kết quả trả về
Không trả danh sách dòng thô mà trả object:

| Trường | Ý nghĩa |
|--------|---------|
| `status` | `ok` hoặc `empty` (không có dữ liệu) |
| `total_rows_fetched` | Số dòng (sản phẩm/nhóm) lấy được |
| `chart_data.labels` | Nhãn từng dòng, ghép các dimension bằng " - " |
| `chart_data.amount_vnd` | Doanh thu sell-out tương ứng từng nhãn, đơn vị **VNĐ** |
| `download_file_7z` | Đường dẫn file `.7z` chứa CSV đầy đủ khi có hơn 30 dòng, ngược lại `null` |

- Chỉ lấy dòng có doanh thu > 0.
- Khi có hơn 30 dòng: `chart_data` chỉ giữ 20 dòng đầu, các dòng còn lại gộp thành một nhãn "Others (n)". Khi trả lời, nói rõ phần "Others" là tổng của nhiều sản phẩm.
- `labels` và `amount_vnd` cùng thứ tự; dòng đầu là hạng 1.
