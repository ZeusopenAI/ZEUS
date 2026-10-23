# `.ai/handoff/` — hộp thư giữa Hermes (chủ) và agent thực thi

Đây là **đường truyền** của Hermes Owner Protocol. Không phải tài liệu trang trí:
file ở đây quyết định phiên agent được làm gì và bị dừng khi nào.

| File | Ai ghi | Ai đọc | Nội dung |
|---|---|---|---|
| `INBOX.md` | Hermes (workflow `hermes-owner-loop`) | agent ở BƯỚC 0 | Mệnh lệnh đang hiệu lực: front matter có `id`, `issuer`, `valid_until`, `seal` + thân lệnh |
| `OUTBOX.md` | agent lúc kết phiên (`hermes-session-closeout.sh`) | Hermes ở chu kỳ sau | Báo cáo DONE / PARTIAL / BLOCKED kèm bằng chứng git |
| `STATE.json` | cả hai, qua `scripts/hermes_owner.py` | cả hai | Directive đang hiệu lực + lịch sử + báo cáo cuối |
| `archive/` | workflow | người | Bản lưu từng mệnh lệnh đã ban hành |
| `.cache/` | `boot`/`closeout` | máy | Nhật ký boot, directive đang dùng (không commit) |

## Quy tắc

1. **Không sửa tay `INBOX.md`.** Thân lệnh được bọc bằng seal SHA-256; sửa một ký tự là
   `boot` trả mã 5 và cả phiên dừng. Muốn đổi lệnh: chạy lại workflow.
2. **Không xoá báo cáo cũ** trong `OUTBOX.md`. Hermes đọc phần đầu file, nhưng lịch sử là
   bằng chứng kiểm toán.
3. **Không đặt bí mật** vào đây — file được commit và hiển thị công khai.
4. `INBOX.md` không có front matter hoặc chưa từng có mệnh lệnh ⇒ `boot` trả mã 3.

Đặc tả đầy đủ: [`docs/HERMES_OWNER_PROTOCOL.md`](../../docs/HERMES_OWNER_PROTOCOL.md).
