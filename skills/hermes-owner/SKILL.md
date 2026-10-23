---
name: hermes-owner
description: |
  **PROJECT SKILL** — Hermes Owner Protocol: Hermes là chủ của repo ZEUS, các phiên
  agent (Arena, Codespaces, Cursor) chỉ thực thi. Dùng khi: cần ban hành mệnh lệnh cho
  một phiên agent, đọc báo cáo từ `.ai/handoff/OUTBOX.md`, kiểm tra mệnh lệnh còn hiệu
  lực, hoặc xử lý trường hợp agent dừng vì không có lệnh / lệnh hết hạn / seal sai.
license: MIT
---

# Hermes Owner Protocol — Hermes là chủ

## Vai trò

Hermes **ban hành mệnh lệnh**, không tự thực thi trong lượt ra lệnh. Agent thực thi
(Arena, Codespaces, Cursor…) chỉ được làm đúng mệnh lệnh và phải báo cáo lại.

Đường truyền nằm trong repo, không cần server:

| File | Hướng | Ai ghi |
|---|---|---|
| `.ai/handoff/INBOX.md` | Hermes → agent | workflow `hermes-owner-loop.yml` (qua `scripts/hermes_owner.py issue`) |
| `.ai/handoff/OUTBOX.md` | agent → Hermes | agent lúc kết phiên (`scripts/hermes-session-closeout.sh`) |
| `.ai/handoff/STATE.json` | máy đọc | cả hai, qua engine |

## Khi được yêu cầu ban hành mệnh lệnh

1. Đọc bản giao ban: `.ai/handoff/.tmp/brief.md` (workflow tạo) hoặc tự chạy
   `python3 scripts/hermes_owner_brief.py`.
2. Đọc **báo cáo gần nhất** trong `OUTBOX.md` — mệnh lệnh mới phải phản ánh kết quả đó,
   không lặp lại việc đã DONE và phải gỡ BLOCKED nếu có thể.
3. Ban hành **đúng một** mệnh lệnh, tối đa **5 việc**, việc nào cũng có bằng chứng kiểm
   chứng (lệnh + kết quả mong đợi). Không viết mục tiêu mơ hồ.
4. Chỉ in khối có marker, không thêm lời dẫn ngoài khối:

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

5. Giữ mệnh lệnh **vừa một phiên** (≤ 2 giờ agent). Việc lớn thì cắt phần nhỏ nhất có giá
   trị, phần còn lại ghi vào `## Việc tiếp theo`.
6. Không đưa bí mật, token, dữ liệu cá nhân vào mệnh lệnh — file được commit công khai.

## Khi đọc báo cáo của agent

- Báo cáo nằm giữa `<!-- report:start -->` và `<!-- report:end -->`, mới nhất ở trên.
- Ba trạng thái: `DONE` (xong + có bằng chứng), `PARTIAL` (xong một phần), `BLOCKED`
  (cần chủ gỡ).
- Không tin lời khai suông: báo cáo có mục **Đã kiểm chứng**; nếu trống, coi như chưa xong
  và yêu cầu chạy lại kiểm chứng trong mệnh lệnh kế tiếp.
- Báo cáo không sửa được (append-only). Muốn đính chính: ban hành mệnh lệnh mới.

## Kiểm tra trạng thái nhanh

```bash
python3 scripts/hermes_owner.py status          # in mệnh lệnh hiện hành + báo cáo cuối
python3 scripts/hermes_owner.py status --strict # trả mã lỗi nếu lệnh hỏng/hết hạn
```

Mã thoát: `0` OK · `3` chưa có lệnh · `4` hết hạn · `5` seal sai · `6` sai người ban hành.
Gặp `5` nghĩa là `INBOX.md` bị sửa tay: ban hành lại mệnh lệnh, đừng cố "sửa seal".

## Ranh giới

- Không tự sửa `INBOX.md` bằng tay; luôn qua `issue` để seal đúng.
- Không tự ý nới `valid_until` của lệnh cũ; ban hành lệnh mới.
- Không đặt lệnh dài hơn 72 giờ nếu chưa có lý do; lệnh cũ sẽ tự vô hiệu và mọi phiên dừng.
- Việc phá huỷ dữ liệu, đổi secrets, deploy production: ghi rõ trong `## Không được làm`.

## Liên quan

- Đặc tả đầy đủ: `docs/HERMES_OWNER_PROTOCOL.md`
- Luật gốc cho agent: `AGENTS.md` ĐIỀU 0
- Hộp thư: `.ai/handoff/README.md`
