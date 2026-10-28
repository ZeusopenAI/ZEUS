---
name: hermes-web-automation
description: |
  **PROJECT SKILL** — Web automation cho Hermes: đọc toàn Internet qua Agent Reach (17+ nền tảng: web, GitHub, YouTube, X/Twitter, Reddit, Bilibili, Xiaohongshu, RSS) và điều khiển trình duyệt qua Browser MCP / Playwright MCP / Chrome DevTools MCP. Activate khi người dùng yêu cầu Hermes đọc URL, tìm kiếm MXH, lấy transcript YouTube, thao tác browser (click/fill/screenshot), hoặc nghiên cứu đa nguồn.
license: MIT
---

# Hermes Web Automation — Agent Reach + Browser MCP

## Mục tiêu

Cho Hermes hai năng lực bổ trợ:

- **ĐỌC (Agent Reach):** lấy nội dung từ web, GitHub, YouTube, X/Twitter, Reddit, Bilibili, Xiaohongshu, V2EX, RSS… qua CLI `agent-reach` + upstream tools (`gh`, `yt-dlp`, `mcporter`, Jina Reader).
- **LÀM (Browser MCP):** điều khiển trình duyệt thật — navigate, snapshot, click, fill, screenshot, history — qua MCP servers (`browser-mcp`, `playwright`, `chrome-devtools`).

```
Người dùng nói việc → Hermes phân loại intent → chọn ĐỌC hay LÀM → gọi tool phù hợp
```

---

## 0. Điều kiện tiên quyết

### Kiểm tra nhanh

```bash
bash scripts/hermes-web-tools-setup.sh --check
agent-reach doctor --json | python3 -m json.tool
hermes mcp catalog
```

Nếu thiếu:

```bash
bash scripts/hermes-web-tools-setup.sh --install
```

### Cấu hình MCP (một lần)

**VPS (khuyên dùng Playwright, headless):**

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  playwright:
    command: "npx"
    args: ["-y", "@executeautomation/playwright-mcp-server"]
```

**Desktop (giữ login):**

```yaml
mcp_servers:
  browser-mcp:
    url: "http://127.0.0.1:12306/mcp"
    type: "streamableHttp"
```

Cài extension trước: `BrowserMCP/mcp` hoặc `hangwin/mcp-chrome` → Load unpacked → Connect.

Xem chi tiết: `docs/HERMES_WEB_AUTOMATION.md`.

---

## 1. Khi nào dùng ĐỌC (Agent Reach)

| Intent người dùng | Tool Hermes gọi (qua `terminal`) |
|-------------------|----------------------------------|
| “Đọc bài này: https://…” / “tóm tắt URL” | `curl -s "https://r.jina.ai/URL"` |
| “Tìm repo / search GitHub” | `gh search repos "query" --limit 10` / `gh api ...` |
| “Lấy transcript YouTube / Bilibili” | `yt-dlp --write-auto-sub --skip-download "URL"` |
| “Tìm web / nghiên cứu” | `mcporter call 'exa.web_search_exa(query:"…", numResults:5)'` |
| “Tìm Twitter/X / Reddit / XHS” | `agent-reach` routing: `mcporter` / `rdt` / OpenCLI |
| “Đọc RSS” | `feedparser` / `curl Jina` |
| “Kiểm tra kênh nào sẵn sàng” | `agent-reach doctor` |

### Ví dụ

```bash
# Đọc web bất kỳ (Jina Reader → Markdown)
curl -s "https://r.jina.ai/https://example.com/article" | head -n 100

# GitHub search
gh search repos "AI agent browser automation" --sort stars --limit 5

# Web search (Exa qua MCP)
mcporter call 'exa.web_search_exa(query:"Hermes agent MCP", numResults:5)'

# YouTube transcript
yt-dlp --write-auto-sub --skip-download --sub-lang vi -o "/tmp/%(id)s" "https://www.youtube.com/watch?v=..."

# Kiểm tra sức khỏe
agent-reach doctor
agent-reach doctor --json | python3 -c "import json,sys; d=json.load(sys.stdin); print([k for k,v in d.items() if '✅' in str(v)])"
```

### Cấu hình kênh cần login (tùy chọn)

```bash
gh auth login
agent-reach configure twitter-cookies "auth_token=xxx; ct0=yyy"
agent-reach configure proxy http://user:pass@ip:port
# xem gợi ý: agent-reach doctor
```

> **An toàn:** Cookie lưu `~/.agent-reach/config.yaml` mode 600. Không commit, không dán vào chat công khai. Dùng tài khoản phụ cho X/Reddit.

---

## 2. Khi nào dùng LÀM (Browser MCP)

| Intent người dùng | Tool Hermes gọi (qua `mcp_servers.*`) |
|-------------------|---------------------------------------|
| “Mở trang X / điều hướng” | `browser_navigate(url="https://…")` |
| “Chụp màn hình / xem trang” | `browser_screenshot`, `browser_snapshot` |
| “Click / điền form / gõ” | `browser_click(ref="…")`, `browser_fill(ref="…", value="…")`, `browser_keyboard` |
| “Lấy nội dung / phần tử” | `chrome_get_web_content`, `chrome_get_interactive_elements` |
| “Lịch sử / bookmark / tab” | `chrome_history`, `chrome_bookmark_search`, `get_windows_and_tabs` |
| “Đo network / console” | `chrome_network_capture_start`, `chrome_console` |
| “Test E2E / đăng nhập” | `playwright` snapshot → fill → click → assert |

### Ví dụ (Hermes nói chuyện với MCP tools)

```text
# Sau khi mcp_servers.playwright đã được cấu hình, Hermes thấy tools:
- browser_navigate
- browser_snapshot
- browser_click
- browser_fill
- browser_screenshot
- browser_evaluate
# …và gọi trực tiếp:

browser_navigate(url="https://example.com")
browser_snapshot()  # trả về accessibility tree với refs
browser_click(ref="e12")
browser_screenshot(path="/tmp/page.png")
```

> **Lưu ý:** Tên tool chính xác phụ thuộc manifest. Kiểm tra bằng `hermes mcp catalog` hoặc `skill_view` sau khi cài.

---

## 3. Quy trình chuẩn cho Hermes

### 3.1 Nghiên cứu đa nguồn (READ)

```bash
# 1. Tìm kiếm
mcporter call 'exa.web_search_exa(query:"AI filmmaking FlowKit 2026", numResults:5)'

# 2. Đọc chi tiết từng URL
curl -s "https://r.jina.ai/https://example.com/post-1" > /tmp/post-1.md
curl -s "https://r.jina.ai/https://example.com/post-2" > /tmp/post-2.md

# 3. GitHub bổ sung
gh search repos "AI video generation" --limit 5

# 4. Tổng hợp
cat /tmp/post-*.md | python3 scripts/read-article.py --stdin > report.md

# 5. Commit
git switch -c hermes/research-xxx origin/main
git add report.md && git commit -m "research: …" && git push -u origin HEAD
gh pr create --base main --title "…" --body "…"
```

### 3.2 Thao tác browser (ACT)

```text
1. browser_navigate(url="https://staging.quangquy.ai/login")
2. browser_snapshot() → tìm ref của input email/password
3. browser_fill(ref="e5", value="test@example.com")
4. browser_fill(ref="e6", value="***")
5. browser_click(ref="e7")  # nút Login
6. browser_snapshot() → kiểm tra đã đăng nhập
7. browser_screenshot(path="/tmp/after-login.png")
```

### 3.3 Kết hợp READ + ACT

```text
Bạn: “Nghiên cứu 3 đối thủ, rồi chụp màn hình trang giá của họ”

Hermes:
  1. READ: mcporter search + Jina đọc 3 site → tóm tắt
  2. ACT: browser_navigate từng site/pricing → screenshot
  3. Tổng hợp report.md + screenshots → commit → PR
```

---

## 4. Ranh giới an toàn (bắt buộc)

- **Không spam / vượt rate limit:** delay giữa các request, không gửi hàng loạt.
- **Không vượt paywall / hack:** chỉ đọc nội dung user có quyền (cookie do user tự cấp).
- **Không thao tác nguy hiểm:** không tự xóa dữ liệu, không tự đăng bài công khai mà không hỏi.
- **Việc tốn tiền hoặc phá hủy:** hỏi trước (theo `AGENTS.md`).
- **Cookie/secret:** không in ra log/PR, không commit. Nếu lộ → báo thu hồi ngay.
- **Extension MCP:** chỉ trên profile riêng, không lưu mật khẩu nhạy cảm.
- **Tuân thủ TOS:** X, Reddit, Facebook… có giới hạn automation — dùng tài khoản phụ, không lạm dụng.

---

## 5. Xử lý sự cố

| Triệu chứng | Cách khắc phục |
|-------------|---------------|
| `agent-reach: command not found` | `pipx ensurepath; exec $SHELL` hoặc thêm `~/.local/bin` vào PATH |
| `doctor` báo `off` cho X/Reddit | Thiếu cookie → `agent-reach configure …` |
| `playwright` probe timeout khi `hermes mcp install` | Bình thường — cài vẫn OK, chạy `hermes mcp configure playwright` sau |
| BrowserMCP không kết nối | Kiểm extension “Connected”, port 12306 có trống không |
| VPS bị 403 X/Reddit | Cấu hình proxy: `agent-reach configure proxy …` |
| Hermes không thấy tools mới | Restart Hermes session (`hermes chat` lại) |

---

## 6. Cập nhật & kiểm tra định kỳ

```bash
agent-reach check-update && agent-reach update
npm update -g browser-mcp mcp-chrome-bridge
hermes mcp catalog
bash scripts/hermes-web-tools-setup.sh --check
bash scripts/hermes-sync.sh  # đồng bộ skill mới từ repo
```

---

## 7. Tài liệu liên quan

| File | Vai trò |
|------|---------|
| `docs/AGENT_REACH_BROWSER_MCP_RESEARCH.md` | Nghiên cứu đầy đủ (so sánh, kiến trúc, rủi ro) |
| `docs/HERMES_WEB_AUTOMATION.md` | Hướng dẫn vận hành cho người dùng |
| `scripts/hermes-web-tools-setup.sh` | Cài + kiểm tra toàn bộ |
| `agents/hermes/optional-mcps/browser-mcp/manifest.yaml` | Catalog BrowserMCP |
| `agents/hermes/optional-mcps/playwright-mcp/manifest.yaml` | Catalog Playwright MCP |
| `agents/hermes/optional-mcps/chrome-devtools-mcp/manifest.yaml` | Catalog Chrome DevTools MCP |

---

*Skill này tuân thủ `CONTRIBUTING.md`: mọi tool trong prose là `terminal` hoặc `mcp_servers` đã khai báo ở Prerequisites.*
