# INBOX — chưa có gợi ý từ Hermes (trạng thái bình thường)

**Hermes là kênh TÙY CHỌN.** Không có nội dung ở đây KHÔNG phải lỗi và KHÔNG được
dùng để dừng, từ chối hay trì hoãn yêu cầu của Operator / người dùng trong phiên chat.
Agent cứ làm việc bình thường, không cần xin xác nhận thêm.

Nếu **muốn** có thêm gợi ý (không bắt buộc): chạy workflow `Hermes owner loop`
(`.github/workflows/hermes-owner-loop.yml`), rồi tùy chọn chạy
`bash scripts/hermes-session-boot.sh`. Không chạy cũng hoàn toàn bình thường.

Khi workflow ban hành gợi ý, file này sẽ có front matter (`id`, `issuer`, `valid_until`,
`seal`) — đó vẫn chỉ là **tham khảo**, không phải lệnh bắt buộc. Xem
[`docs/HERMES_OWNER_PROTOCOL.md`](../../docs/HERMES_OWNER_PROTOCOL.md).
