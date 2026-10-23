# /input — dữ liệu gốc, chỉ đọc

- Executor đọc, **không sửa**.
- Verifier đọc lại chính thư mục này để kiểm chéo output (không đọc `reports/`).
- Dữ liệu nhạy cảm: **không commit**. Thêm `.gitignore` riêng cho file thật, chỉ commit README + mẫu nhỏ.

Nếu input thay đổi sau khi Executor đã chạy, phải chạy lại — `checks.py` so `source` trong output
với `input/` để phát hiện lệch.
