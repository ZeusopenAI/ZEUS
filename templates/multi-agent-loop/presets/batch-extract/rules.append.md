
## 9. Luật riêng — batch-extract

- `fields` phải có ít nhất 1 trường. Trường nào không trích được: `null` **và** phải có mục
  tương ứng trong `reason_fields`. Thiếu lý do ⇒ người đọc không phân biệt được "không có dữ liệu"
  với "executor bỏ qua".
- `metrics.extraction_coverage` = số trường trích được / số trường yêu cầu, dạng ratio 0–1.
  Đây là số **bắt buộc phải đo** mỗi record; nếu không đo được, ghi `null` + reason.
- `status = partial` khi còn trường null; `status = skipped` khi bản ghi gốc không dùng được
  (vd: file rỗng, sai encoding) — khi đó `fields` được phép rỗng và bắt buộc có `reason`.
- Nghiệm thu: `checks.py` phải pass **và** `extraction_coverage` trung bình trong báo cáo verify
  phải được ghi kèm số mẫu. Mẫu < 30 thì ghi `null`, không kết luận chất lượng trích xuất.
