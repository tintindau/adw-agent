# Thuật ngữ chung – dữ liệu bán hàng Kangaroo

## Sell-in và sell-out
- **Sell-in (SI)**: hàng Kangaroo bán vào hệ thống đối tác (nhập vào cửa hàng/kho đối tác).
- **Sell-out (SO)**: hàng đối tác bán ra cho người tiêu dùng cuối.
- Chênh lệch sell-in và sell-out phản ánh tồn kho ở kênh đối tác; không nên cộng hai chỉ số này với nhau.

## DMX
- **DMX** là chuỗi Điện Máy Xanh. Các cột có chữ `dmx` (vd `prod_class_dmx`, mã sản phẩm DMX) là thông tin theo cách phân loại/mã của DMX.
- Mã sản phẩm Kangaroo là `prod_id_kgr` / `prod_code` (KGR = Kangaroo).

## Loại hàng (`prod_type`)
| Giá trị | Ý nghĩa | Điều kiện |
|---------|---------|-----------|
| `Shibu` | Hàng thuộc nhóm Shibu | `is_shibu = 1` |
| `Trung_bay` | Hàng mô hình / trưng bày (mockup, dummy) | `is_dummy = 1` |
| `Con_lai` | Hàng bán thông thường còn lại | không thuộc hai nhóm trên |

- `is_shibu` và `is_dummy` là cờ 0/1.
- TODO: xác nhận định nghĩa nghiệp vụ của "Shibu 25%".

## Định dạng thời gian
- Tháng: số nguyên `YYYYMM`, vd `202610` = tháng 10/2026.
- Ngày: chuỗi `YYYYMMDD`, vd `20261015` = 15/10/2026.
- Khi người dùng nói "tháng này", "tháng trước", hãy quy đổi sang `YYYYMM` trước khi gọi tool.

## Địa lý
- `region`: vùng/miền theo phân vùng của cửa hàng.
- `province`: tỉnh/thành phố của cửa hàng.

## Nguyên tắc diễn giải kết quả
- Kết quả tool đã được tổng hợp sẵn; không tự tính lại từ dữ liệu bị cắt bớt.
- Nếu kết quả có `truncated = true` hoặc số dòng chạm giới hạn, nói rõ với người dùng là danh sách chưa đầy đủ.
- Không bịa số liệu; nếu tool trả rỗng, trả lời là không có dữ liệu cho bộ lọc đó.
