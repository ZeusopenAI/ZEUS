# Arena Agent vs Hermes — so sánh thực tế

Tài liệu này so sánh **Arena Agent** (agent đang chạy phiên làm việc này) với **Hermes Agent**
(runtime nằm trong `agents/hermes/` của repo). Số liệu về Hermes lấy trực tiếp từ mã nguồn
trong repo này, không phải phỏng đoán.

---

## 1. Bảng so sánh nhanh

| Tiêu chí | Arena Agent | Hermes Agent |
|---|---|---|
| Bản chất | Agent trên hạ tầng Arena, gắn với 1 phiên + 1 nhánh git | Runtime Python tự host (Nous Research, MIT), vendored tại `agents/hermes/` |
| Nơi chạy | Sandbox của Arena | Máy bạn / VPS / Docker / Modal / Daytona / SSH |
| Thời gian sống | Trong phiên; hết phiên là dừng | 24/7, gateway chạy nền, tự khởi động lại |
| Model | Arena route nhiều model (Claude, ChatGPT, Gemini, Grok, Qwen, Kimi…) | Bạn chọn: OpenRouter, OpenAI, Nous Portal, endpoint riêng (`hermes model`) |
| Cần API key? | Không (Arena lo) | Có — key của bạn, tốn credit theo token |
| Bộ nhớ dài hạn | Không có xuyên phiên; chỉ context trong phiên | `MEMORY.md` + `USER.md` + `state.db` (SQLite + FTS5) + `session_search` |
| Tự tạo/sửa skill | Không (đọc file skill nếu được trỏ) | Có — `skill_manage`, curator tự archive/prune, `learning_graph` |
| Skill format | Đọc file `.md` trong repo | Chuẩn `agentskills.io`: `skills_list` / `skill_view` (progressive disclosure) |
| Đa kênh chat | Chỉ trong Arena | 20 platform: Telegram, Discord, Slack, WhatsApp, Signal, Matrix, IRC, Teams, Email… (`plugins/platforms/`) |
| Cron / chạy không người | Không | Có — scheduler + `cronjob_tools`, giao kết quả về mọi kênh |
| Tool phụ | bash, edit file, web search/fetch, tạo ảnh, tạo giọng nói, server + live preview | 92 module: terminal, browser/CDP, computer_use, MCP, image_gen, subagent, kanban, code_execution |
| Connector sẵn | Gmail, Google Calendar/Docs/Drive, Linear, Notion, GitHub | MCP server (tự cấu hình) |
| Internet | Chỉ allowlist host (ví dụ `raw.githubusercontent.com` bị chặn) | Không giới hạn theo host, nhưng phụ thuộc máy chạy |
| Chi phí | Theo phiên Arena | Token API + VPS/điện |

---

## 2. Điểm mạnh của Arena Agent

- **Không cần cài đặt gì.** Mở phiên là có môi trường: bash, đọc/sửa file, git, `gh`, chạy server preview.
- **Hiểu repo theo chiều sâu.** Đọc hàng chục file, grep chéo, đối chiếu chéo rồi mới kết luận — phù hợp việc audit, refactor, viết tài liệu.
- **Đa model do Arena điều phối**, không phải quản lý key hay so sánh giá từng model.
- **Connector chính thức**: Gmail, Drive, Docs, Calendar, Linear, Notion — thao tác trực tiếp, không cần dựng MCP.
- **Preview trực tiếp**: dựng web/server và xem ngay trong trình duyệt.
- **An toàn hơn về credential**: bạn không phải đưa API key cá nhân cho agent.

## 3. Điểm yếu của Arena Agent

- **Không thường trực.** Đóng phiên là hết; không có cron, không nhắn bạn lúc 7h sáng.
- **Không nhớ bạn giữa các phiên.** Mọi thứ "học" trong phiên này không tự sang phiên sau; muốn giữ thì phải ghi ra file trong repo (như tài liệu này hoặc `skills/`).
- **Mạng bị allowlist.** Đã kiểm chứng trong phiên này: `curl raw.githubusercontent.com` trả `SSL_ERROR_SYSCALL`, phải chuyển sang `api.github.com`.
- **Một phiên = một mạch công việc.** Việc quá dài phải chia nhỏ, context có hạn.

## 4. Điểm mạnh của Hermes

- **Sống 24/7, ở đúng nơi bạn ở**: Telegram/Discord/Slack/WhatsApp/Signal — nhắn từ điện thoại.
- **Vòng học khép kín**: tự tạo skill sau việc phức tạp, tự sửa skill khi dùng, curator dọn skill rác theo thời gian (`agent/curator.py`).
- **Nhớ dài hạn thật**: `MEMORY.md` (ghi chú về môi trường/dự án) + `USER.md` (về bạn) được nhúng vào system prompt đầu phiên; `state.db` lưu toàn bộ hội thoại, `session_search` tra lại bằng FTS5 **không tốn token**.
- **Tự động hoá**: cron bằng ngôn ngữ tự nhiên, báo cáo định kỳ, backup, audit.
- **Uỷ quyền & song song hoá**: subagent cô lập cho từng nhánh việc.
- **Dữ liệu thuộc về bạn**: tất cả nằm trong `~/.hermes` trên máy/VPS của bạn.

## 5. Điểm yếu của Hermes

- **Phải cài và phải nuôi**: Python 3.11+, key, cấu hình `config.yaml`, cập nhật định kỳ.
- **Tốn tiền theo token** — chạy vòng lặp nhiều bước là tốn thật; phải đặt `max_turns`.
- **Bề mặt bảo mật lớn**: nó có shell, đọc file, giữ credential. Chạy sai quyền hoặc mở gateway ra Internet mà không khoá là rủi ro thật.
- **Chất lượng phụ thuộc model + skill.** Skill viết mơ hồ → agent làm sai một cách tự tin.
- **Tự tạo skill không miễn phí**: nếu curator hoạt động kém, kho skill phình rác.

---

## 6. Có lưu nội dung chat không?

**Cả hai đều lưu — khác nhau ở chỗ ai giữ.**

### Hermes

| Thứ được lưu | Vị trí |
|---|---|
| Toàn bộ hội thoại (JSON từng message, có index FTS5) | `~/.hermes/state.db` (SQLite, WAL) |
| Ghi chú agent tự rút ra | `~/.hermes/MEMORY.md` |
| Hồ sơ về người dùng | `~/.hermes/USER.md` |
| Skill do agent tạo / archive | `~/.hermes/skills/` + `.curator_state` |

Tra lại bằng `session_search` với 3 chế độ: **discovery** (tìm theo từ khoá), **scroll** (cuộn quanh 1 message), **browse** (liệt kê phiên gần đây). Tất cả đọc thẳng từ SQLite — không gọi LLM, không tốn token.

Hệ quả: **xoá `state.db` = xoá lịch sử chat**; đây là dữ liệu local, bạn toàn quyền.

### Arena Agent

- Hội thoại thuộc **phiên Arena** — Arena lưu để bạn xem lại; thời hạn lưu do Arena quy định.
- **Tôi không có công cụ đọc lại phiên cũ**, nên với tôi mỗi phiên là trang giấy trắng.
- Thay đổi file trong workspace và repo được lưu tự động; đó mới là "bộ nhớ" thật sự bền của phiên.

### Một điểm dễ hiểu nhầm

Skill `edit-anh` đã cài vào `~/.hermes/skills/edit-anh` **không chứa nội dung chat nào**. Nó là 3 file tĩnh (`SKILL.md`, `prompts.md`, `README.md`). Cài skill ≠ Hermes nhớ cuộc trò chuyện này.

---

## 7. Nên dùng cái nào

| Việc | Dùng |
|---|---|
| Audit/refactor repo, viết tài liệu, sửa nhiều file | Arena Agent |
| Dựng web + xem preview ngay | Arena Agent |
| Thao tác Gmail/Drive/Docs/Calendar/Linear/Notion | Arena Agent |
| Nhắn từ điện thoại, nhớ lâu, chạy 24/7, báo cáo định kỳ | Hermes |
| Tự tạo skill sau mỗi việc phức tạp | Hermes |

**Cách kết hợp tốt nhất:** Arena Agent viết skill / workflow / devcontainer → commit vào repo →
Hermes cài và vận hành. Arena giỏi *xây*, Hermes giỏi *chạy thường trực*.

> **Chính sách 28/10/2026:** Hermes là kênh **TÙY CHỌN**. Phiên Arena có thể gọi Hermes để
> lấy gợi ý, nhưng không bắt buộc; không có gợi ý / gợi ý hết hạn / workflow lỗi đều không
> chặn phiên chat. Chi tiết: `AGENTS.md` ĐIỀU 0 · `docs/HERMES_SESSION_ERROR_RCA.md`.
