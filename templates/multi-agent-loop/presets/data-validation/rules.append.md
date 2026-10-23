
## 9. Luật riêng — data-validation

- `violations` phải **cụ thể**: `"<trường>: <lý do>"`. Câu chung chung như "dữ liệu sai" không dùng
  được để sửa, và không kiểm được bằng máy.
- `valid = true` ⇒ `violations` rỗng. `valid = false` ⇒ `violations` có ít nhất 1 mục.
  Hai vế đều bị `checks.py` kiểm qua schema.
- `metrics.violation_count` bắt buộc mỗi record. **`violation_count = 0` phải có `measured_by`
  + `evidence`** trỏ tới dòng log của lần chạy validator. Đây là chỗ dễ ghi 0 giả nhất: "chắc là
  không có vi phạm" không phải là đo.
- `validator_version` nên ghi: đổi luật kiểm mà không đổi version thì số vi phạm trước/sau không
  so sánh được.
- Khi validator không chạy được trên một bản ghi (file hỏng, encoding lạ): `status = skipped`,
  `reason` nêu lý do, `metrics.violation_count = null` + reason. **Không** ghi 0.
