# Bộ nhớ thứ hai (Second Brain) — Quang Quý AI / Zeus

Cập nhật: 2026-09-17

## 1. Mục tiêu

Gom **tất cả thông tin đã trao đổi trên mạng** với các AI (ChatGPT, Claude.ai,
Gemini, Hermes) về **một kho ký ức duy nhất, tìm kiếm được**, không AI nào "quên" những gì đã bàn trước đó.

Thiết kế độc lập, nhẹ và linh hoạt: chạy bằng script Node.js standalone (`scripts/second-brain-import.mjs`), không cần cài đặt các framework cồng kềnh hay cấu trúc doanh nghiệp phức tạp.

## 2. Kiến trúc

```text
ChatGPT export (conversations.json)   ──┐
Claude.ai export (conversations.json) ──┼──▶  scripts/second-brain-import.mjs
Gemini Takeout (JSON / Chat-*.html)   ──┤     (tự động redact secrets, chuyển thành Markdown)
Hermes MEMORY.md / USER.md            ──┘
        │
        ▼
~/.hermes/memory/imports/chatgpt|claude-ai|gemini/*.md
        │
        ▼
Hermes memory search & recall
        │
        ▼
Phối hợp đồng bộ: ChatGPT · Claude · Hermes · Gemini
```

Ba tầng dữ liệu:

| Tầng | Nơi lưu | Vai trò |
| --- | --- | --- |
| Lõi được chọn lọc | `MEMORY.md`, `USER.md` | Sự thật bền vững, nạp mỗi phiên |
| Lưu trữ tình tiết | `~/.hermes/memory/imports/<nguồn>/*.md` | Lịch sử chat nhập về, tìm theo yêu cầu |
| Ghi chú hằng ngày | `memory/YYYY-MM-DD.md` | Quan sát đang diễn ra |

Lịch sử nhập về là **kho lưu trữ chỉ đọc**: tìm kiếm được, nhưng **không tự động trộn vào** `MEMORY.md` bootstrap. Khi một sự thật bền vững lặp lại nhiều nguồn, đưa nó vào `MEMORY.md` một cách có chủ đích (xem mục 6).

## 3. Cách dùng

### 3.1. Lấy file xuất từ từng AI

| Nguồn | Đường lấy |
| --- | --- |
| ChatGPT | Settings → Data controls → **Export data** → file `conversations.json` |
| Claude.ai | Settings → Data controls / **Export** → `conversations.json` (dạng zip, giải nén trước) |
| Gemini | **Google Takeout** → chọn Gemini → tải về → thư mục `Gemini/` (JSON `conversations.json` ưu tiên; hỗ trợ cả `Chat-*.html` cũ) |

### 3.2. Nhập bằng script standalone

Chạy được ngay trên Termux, VPS, Colab hoặc máy tính cá nhân bằng Node.js ≥ 22:

```bash
# Nhập từng nguồn
node scripts/second-brain-import.mjs import chatgpt --from ~/Downloads/conversations.json
node scripts/second-brain-import.mjs import claude-ai --from ~/Downloads/claude-export/
node scripts/second-brain-import.mjs import gemini --from ~/Downloads/Takeout/Gemini/

# Xem trước không ghi file
node scripts/second-brain-import.mjs import chatgpt --from ~/Downloads/conversations.json --dry-run

# Nhập toàn bộ từ một thư mục inbox chứa nhiều file export
node scripts/second-brain-import.mjs ingest --from ~/Downloads/ai-inbox/

# Xem danh sách nguồn đã nhập
node scripts/second-brain-import.mjs list
```

Mặc định ghi vào `~/.hermes/memory/imports`; có thể đổi đường dẫn bằng tham số `--out <thư mục>` hoặc biến môi trường `SECOND_BRAIN_IMPORTS_DIR`.

### 3.3. Chạy test

Bộ test dùng `node:test` và file `.ts` (Node tự strip type từ 22.18, không cần `tsc`):

```bash
npm test --prefix scripts/second-brain     # 20 test
```

CI: `.github/workflows/second-brain-ci.yml` (chạy khi `scripts/second-brain/**` đổi).
Ghi chú: gọi `node --test scripts/second-brain/test/` (truyền **thư mục**) sẽ lỗi
`ERR_MODULE_NOT_FOUND` — phải dùng script trong `package.json` để glob `.ts`.

## 4. Kết nối với các AI khác (hợp đồng bộ nhớ dùng chung)

ChatGPT, Claude, Gemini tham gia phối hợp qua các tài liệu Markdown dùng chung:

- **Giao việc cho AI khác**: đưa `USER.md` + `MEMORY.md` + trích đoạn `memory/imports/<nguồn>/*.md` liên quan làm ngữ cảnh.
- **Đưa trở lại**: nhờ AI kia tóm tắt quyết định, rồi xuất lịch sử của nó và chạy `second-brain-import.mjs`.
- `USER.md`/`MEMORY.md` là **nguồn duy nhất đúng**; các AI khác chỉ đọc bản sao.

### Điều phối đa model (routing)

| AI | Vai trò |
| --- | --- |
| Hermes Agent | Điều phối, sở hữu bộ nhớ (import, tìm, tổng hợp) |
| ChatGPT | Chiến lược, kế hoạch, nội dung tiếp thị |
| Claude | Lập trình chuyên sâu, refactor mã nguồn |
| Gemini | Nghiên cứu tài liệu, media, tác vụ Colab/Python |

## 5. Bảo mật

- Bộ import **tự động redact** secret thường gặp (API key `sk-...`, Google `AIza...`, token `ghp_...`/`xox...`, JWT, `password=...`) thành `[redacted]` trước khi ghi.
- Không commit file xuất hoặc nội dung chat cá nhân lên GitHub public.
- File nhập nằm trong thư mục local của agent (`HERMES_HOME`), không nằm trong repository Git.
- Quá trình nhập là idempotent (chạy lại không trùng lặp file); dùng `--overwrite` nếu muốn ghi đè.

## 6. Tổng hợp từ tình tiết lên lõi

Khi một sự thật bền vững lặp lại nhiều nguồn:
1. Viết nháp sự thật dưới dạng chỉ thị ngắn gọn.
2. Xác nhận thông tin quan trọng.
3. Ghi vào `MEMORY.md` (hoặc `USER.md` cho sở thích cá nhân).
