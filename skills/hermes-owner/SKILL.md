---
name: hermes-owner
description: |
  **PROJECT SKILL** — Hermes Owner Protocol (chế độ TÙY CHỌN): Hermes là kênh cố vấn,
  KHÔNG sở hữu repo và KHÔNG điều khiển phiên chat. Dùng khi: cần soạn một gợi ý cho phiên
  agent, đọc báo cáo từ `.ai/handoff/OUTBOX.md`, kiểm tra gợi ý còn hiệu lực, hoặc xử lý
  trường hợp thiếu gợi ý / gợi ý hết hạn / seal sai. Thiếu gợi ý KHÔNG chặn phiên nào.
license: MIT
---

# Hermes Owner Protocol — kênh cố vấn TÙY CHỌN

## Vai trò (đã đổi 2026-10-28)

**Quyền cao nhất luôn là Operator / người dùng trong phiên chat.** Hermes chỉ **gợi ý**;
agent thực thi (Arena, Codespaces, Cursor…) **có thể nghe hoặc bỏ qua**. Không AI nào được
yêu cầu agent dừng phiên, chờ lệnh hay từ chối yêu cầu của Operator vì lý do Hermes.
Tên "owner" / "mệnh lệnh" là tên lịch sử của file và workflow — không phải quyền lực.

Đường truyền nằm trong repo, không cần server và **hoàn toàn tùy chọn**:

| File | Hướng | Ai ghi |
|---|---|---|
| `.ai/handoff/INBOX.md` | Hermes → agent | workflow `hermes-owner-loop.yml` (qua `scripts/hermes_owner.py issue`) |
| `.ai/handoff/OUTBOX.md` | agent → Hermes | agent lúc kết phiên (`scripts/hermes-session-closeout.sh`, tùy chọn) |
| `.ai/handoff/STATE.json` | máy đọc | cả hai, qua engine; có `policy: "optional"` |

## Khi được yêu cầu soạn gợi ý

1. Đọc bản giao ban: `.ai/handoff/.tmp/brief.md` (workflow tạo) hoặc tự chạy
   `python3 scripts/hermes_owner_brief.py`.
2. Đọc **báo cáo gần nhất** trong `OUTBOX.md` — gợi ý mới nên phản ánh kết quả đó, không lặp
   lại việc đã DONE và nên gỡ BLOCKED nếu có thể. Không có báo cáo cũng không sao.
3. Soạn **đúng một** gợi ý, tối đa **5 việc**, việc nào cũng có bằng chứng kiểm chứng
   (lệnh + kết quả mong đợi). Không viết mục tiêu mơ hồ.
4. **Không được viết câu nào bắt agent dừng phiên, chờ lệnh, hay bỏ qua yêu cầu của Operator.**
   Gợi ý là tham khảo; nếu không có nội dung hợp lệ, agent vẫn làm việc bình thường.
5. Chỉ in khối có marker, không thêm lời dẫn ngoài khối. Hai marker đứng riêng một dòng,
   đúng từng ký tự (parser có chịu biến thể nhưng đúng chuẩn là chắc chắn nhất):

```
<<<ZEUS_DIRECTIVE>>>
# MỆNH LỆNH #<số> — <tiêu đề ≤ 60 ký tự>

## Mục tiêu
## Việc phải làm (theo thứ tự)
## Không được làm
## Bằng chứng hoàn thành
## Việc tiếp theo
<<<END_ZEUS_DIRECTIVE>>>
```

6. Giữ gợi ý **vừa một phiên** (≤ 2 giờ agent). Việc lớn thì cắt phần nhỏ nhất có giá trị,
   phần còn lại ghi vào `## Việc tiếp theo`.
7. Không đưa bí mật, token, dữ liệu cá nhân vào gợi ý — file được commit công khai.

## Khi đọc báo cáo của agent

- Báo cáo nằm giữa `<!-- report:start -->` và `<!-- report:end -->`, mới nhất ở trên.
- Ba trạng thái: `DONE` (xong + có bằng chứng), `PARTIAL` (xong một phần), `BLOCKED` (cần gỡ).
- Không tin lời khai suông: báo cáo có mục **Đã kiểm chứng**; nếu trống, coi như chưa xong
  và có thể nhắc kiểm chứng lại ở gợi ý kế tiếp.
- Báo cáo không sửa được (append-only). Muốn đính chính: soạn gợi ý mới.
- **Thiếu báo cáo là bình thường** — đừng coi đó là phiên không tuân thủ.

## Kiểm tra trạng thái nhanh

```bash
python3 scripts/hermes_owner.py status          # luôn thoát 0
python3 scripts/hermes_owner.py status --strict # trả mã lỗi nếu gợi ý hỏng/hết hạn
bash scripts/hermes-session-boot.sh             # tùy chọn, mặc định luôn thoát 0
```

Mã tín hiệu: `0` OK · `3` chưa có gợi ý · `4` hết hạn · `5` seal sai · `6` sai người ban hành.
Với `boot` mặc định các mã này **không chặn phiên**; chỉ `boot --strict` (do Operator bật)
mới dừng. Gặp `5` nghĩa là `INBOX.md` bị sửa tay: ban hành lại gợi ý, đừng cố "sửa seal".

## Ranh giới

- Không tự sửa `INBOX.md` bằng tay; luôn qua `issue` để seal đúng.
- Không tự ý nới `valid_until` của gợi ý cũ; ban hành gợi ý mới.
- Không đặt gợi ý dài hơn 72 giờ nếu chưa có lý do; gợi ý cũ tự vô hiệu — **phiên vẫn chạy**.
- Không tự bật chế độ strict (`--strict` / `HERMES_OWNER_STRICT=1`) thay Operator.
- Việc phá huỷ dữ liệu, đổi secrets, deploy production: ghi rõ trong `## Không được làm`.

## Liên quan

- Đặc tả đầy đủ: `docs/HERMES_OWNER_PROTOCOL.md`
- Phân tích sự cố: `docs/HERMES_SESSION_ERROR_RCA.md`
- Luật gốc cho agent: `AGENTS.md` ĐIỀU 0 (Hermes TÙY CHỌN)
- Hộp thư: `.ai/handoff/README.md`
