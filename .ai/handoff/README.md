# `.ai/handoff/` — hộp thư TÙY CHỌN giữa Hermes và agent thực thi

Đây là **kênh tham khảo**, không phải cổng kiểm soát phiên. Không có file hợp lệ ở đây,
file hết hạn, seal sai hay workflow lỗi đều **không chặn** bất kỳ phiên agent nào.
Quyền quyết định luôn thuộc Operator / người dùng trong phiên chat (`AGENTS.md` ĐIỀU 0).

| File | Ai ghi | Ai đọc | Nội dung |
|---|---|---|---|
| `INBOX.md` | Hermes (workflow `hermes-owner-loop`) | agent (tùy chọn) | Gợi ý đang hiệu lực: front matter có `id`, `issuer`, `valid_until`, `seal` + thân gợi ý |
| `OUTBOX.md` | agent lúc kết phiên (`hermes-session-closeout.sh`, tùy chọn) | Hermes ở chu kỳ sau | Báo cáo DONE / PARTIAL / BLOCKED kèm bằng chứng git |
| `STATE.json` | cả hai, qua `scripts/hermes_owner.py` | cả hai | Gợi ý đang hiệu lực + lịch sử + báo cáo cuối + `policy: "optional"` |
| `archive/` | workflow | người | Bản lưu từng gợi ý đã ban hành |
| `.cache/` | `boot`/`closeout` | máy | Nhật ký boot, gợi ý đang dùng (không commit) |

## Quy tắc

1. **Không sửa tay `INBOX.md`.** Thân gợi ý được bọc bằng seal SHA-256; sửa một ký tự là
   `boot --strict` trả mã 5. `boot` mặc định vẫn thoát 0 và chỉ cảnh báo — **phiên không dừng**.
   Muốn đổi gợi ý: chạy lại workflow. Đừng cố sửa seal.
2. **Không xoá báo cáo cũ** trong `OUTBOX.md`. Hermes đọc phần đầu file, nhưng lịch sử là
   bằng chứng kiểm toán. Báo cáo là tùy chọn: thiếu báo cáo không phải lỗi.
3. **Không đặt bí mật** vào đây — file được commit và hiển thị công khai.
4. `INBOX.md` không có front matter hoặc chưa từng có gợi ý ⇒ `boot` in
   "KHÔNG BẮT BUỘC, KHÔNG CHẶN PHIÊN" và **thoát 0**. Đây là trạng thái bình thường.
5. Từ "mệnh lệnh" / "owner" trong dữ liệu cũ chỉ là tên lịch sử, không trao quyền điều khiển
   phiên chat. Xem [`docs/HERMES_SESSION_ERROR_RCA.md`](../../docs/HERMES_SESSION_ERROR_RCA.md).

Đặc tả đầy đủ: [`docs/HERMES_OWNER_PROTOCOL.md`](../../docs/HERMES_OWNER_PROTOCOL.md).
