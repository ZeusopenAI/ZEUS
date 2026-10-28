# Hermes Web Automation — Hướng dẫn vận hành Agent Reach + Browser MCP

> **Mục tiêu:** Cho Hermes khả năng **đọc toàn Internet** (Agent Reach) và **điều khiển trình duyệt** (Browser MCP).
> **Đối tượng:** Người vận hành Hermes trên VPS hoặc laptop.

---

## 1. Tổng quan

Hermes mặc định chỉ có `web_search`, `web_extract`, `terminal`, `read_file`… Đủ cho việc cơ bản,
nhưng thiếu:

- Đọc Twitter/X, Reddit, Bilibili, Xiaohongshu, YouTube transcript…
- Giữ login để đọc nội dung private
- Click, điền form, upload, test E2E

Hai họ công cụ mới lấp đúng khoảng trống đó:

| Họ | Vai trò | Hermes gọi qua |
|----|---------|----------------|
| **Agent Reach** | Đọc 17+ nền tảng | `terminal` (CLI) |
| **Browser MCP** | Thao tác browser | `mcp_servers.*` (MCP tools) |

```
Chỉ ĐỌC  → Agent Reach (terminal)
Cần LÀM  → Browser MCP (mcp tools)
```

---

## 2. Cài đặt nhanh (VPS — 5 phút)

### 2.1 Một lệnh cài tất cả

```bash
cd /opt/zeus   # hoặc nơi clone ZEUS
bash scripts/hermes-web-tools-setup.sh --install
```

Script sẽ:

1. Cài `pipx` nếu thiếu, rồi `agent-reach` (từ GitHub main.zip)
2. Chạy `agent-reach install --env=auto` (tự cài Node/mcporter/gh/yt-dlp)
3. Cài `playwright-mcp` qua `npx` (không cần browser extension trên VPS)
4. Cấu hình `~/.hermes/config.yaml` thêm `mcp_servers.playwright`
5. Đồng bộ skill `hermes-web-automation` vào `~/.hermes/skills/`
6. In bảng `doctor` để bạn kiểm tra

### 2.2 Kiểm tra bất cứ lúc nào

```bash
bash scripts/hermes-web-tools-setup.sh --check
agent-reach doctor
hermes mcp catalog   # xem các MCP đã cài
```

Kết quả mong đợi trên VPS:

```
  ✅ agent-reach 1.6.0
  ✅ gh (authenticated)
  ✅ yt-dlp
  ✅ mcporter + Exa
  ✅ playwright-mcp (npx ok)
  ⬜ browser-mcp — desktop only (bỏ qua)
```

### 2.3 Cấu hình kênh cần login (tùy chọn)

Chỉ làm nếu Hermes cần đọc nội dung cần đăng nhập:

```bash
# GitHub private repos
gh auth login

# Twitter/X — export cookie bằng Cookie-Editor (Chrome)
agent-reach configure twitter-cookies "auth_token=xxx; ct0=yyy"

# Reddit
# Cách A: đăng nhập browser thật (desktop) → OpenCLI tự dùng
# Cách B: rdt-cli + cookie (VPS)
agent-reach configure proxy http://user:pass@proxy:port  # nếu bị chặn IP

# Xiaohongshu / Bilibili / Facebook — tương tự, xem doctor gợi ý
agent-reach doctor --json | python3 -m json.tool
```

> **An toàn:** Cookie lưu ở `~/.agent-reach/config.yaml` mode 600, không commit. Dùng **tài khoản phụ** cho X/Reddit.

---

## 3. Cài đặt Desktop (laptop có Chrome)

Nếu Hermes chạy trên laptop (cần giữ login, thao tác như người dùng):

### 3.1 BrowserMCP/mcp (khuyên dùng)

```bash
# 1. Cài server
npm install -g browser-mcp

# 2. Tải extension: https://github.com/BrowserMCP/mcp/releases
#    Chrome → chrome://extensions/ → Developer mode → Load unpacked → chọn thư mục extension

# 3. Bấm icon extension → Connect (port 12306)

# 4. Thêm vào ~/.hermes/config.yaml
```
```yaml
mcp_servers:
  browser-mcp:
    url: "http://127.0.0.1:12306/mcp"
    type: "streamableHttp"
```

### 3.2 hangwin/mcp-chrome (thay thế, có semantic search)

```bash
npm install -g mcp-chrome-bridge
# Tải extension từ https://github.com/hangwin/mcp-chrome/releases
# Load unpacked tương tự, rồi:
```
```yaml
mcp_servers:
  chrome-mcp:
    url: "http://127.0.0.1:12306/mcp"
```

### 3.3 Kiểm tra

```bash
hermes mcp install browser-mcp   # hoặc chọn trong `hermes mcp` picker
hermes chat
# rồi nói: "mở https://example.com và chụp màn hình"
```

---

## 4. Hermes dùng như thế nào

Hermes tự đọc skill `hermes-web-automation` qua `skills_list` / `skill_view`. Bạn chỉ cần nói việc bằng tiếng Việt tự nhiên:

### 4.1 Đọc (Agent Reach)

| Bạn nói | Hermes làm |
|---------|------------|
| “Đọc bài này: https://… rồi tóm tắt” | `curl https://r.jina.ai/URL` → tóm tắt |
| “Tìm 5 repo hot về AI agent trên GitHub” | `gh search repos …` |
| “Lấy transcript video YouTube này” | `yt-dlp --write-auto-sub …` |
| “Tìm Twitter/X về Hermes agent” | `mcporter → exa.web_search_exa` hoặc `twitter search` |
| “Kiểm tra Reddit r/LocalLLaMA về lỗi X” | `rdt search` / OpenCLI |

### 4.2 Thao tác (Browser MCP)

| Bạn nói | Hermes làm (qua MCP tools) |
|---------|----------------------------|
| “Mở trang X, chụp màn hình” | `browser_navigate` → `browser_screenshot` |
| “Điền form này, bấm submit” | `browser_snapshot` → `browser_fill` → `browser_click` |
| “Lấy lịch sử tab đang mở” | `chrome_history`, `search_tabs_content` |
| “Test login flow trên staging” | `playwright` snapshot → fill → assert |

### 4.3 Kết hợp

```text
Bạn: “Nghiên cứu 3 đối thủ về AI video, rồi tạo báo cáo Markdown”

Hermes:
  1. Agent Reach: web_search + đọc 3 site + GitHub search
  2. Tổng hợp vào report.md
  3. (nếu cần) Browser MCP: mở từng site, screenshot làm bằng chứng
  4. Commit report.md → mở PR
```

---

## 5. Cấu hình MCP chi tiết (tham khảo)

### 5.1 VPS — chỉ Playwright (khuyên dùng)

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  playwright:
    command: "npx"
    args: ["-y", "@executeautomation/playwright-mcp-server"]
    # tuỳ chọn: giới hạn tools
    # tools:
    #   include: [browser_navigate, browser_snapshot, browser_click, browser_fill, browser_screenshot]
```

### 5.2 Desktop — BrowserMCP + Playwright

```yaml
mcp_servers:
  browser-mcp:
    url: "http://127.0.0.1:12306/mcp"
    type: "streamableHttp"
  playwright:
    command: "npx"
    args: ["-y", "@executeautomation/playwright-mcp-server"]
  chrome-devtools:
    command: "npx"
    args: ["-y", "chrome-devtools-mcp@latest"]
```

### 5.3 Lọc tools (an toàn)

Mặc định Hermes nạp **tất cả** tools của MCP server. Để hạn chế:

```bash
hermes mcp configure playwright
# Bỏ tick các tool nguy hiểm (ví dụ: delete, eval tuỳ ý)
```

---

## 6. Bảo mật

- **Cookie/token** chỉ ở `~/.agent-reach/config.yaml` và `~/.hermes/.env` (mode 600). Không commit.
- **Không dán cookie vào chat công khai** — chỉ qua `agent-reach configure` (hidden prompt) hoặc `--stdin`.
- **Tài khoản phụ** cho X/Reddit khi test automation.
- **Proxy** nếu chạy trên VPS IP bị chặn (X/Reddit chặn datacenter).
- **Extension MCP:** chỉ cài trên Chrome profile riêng, không lưu mật khẩu ngân hàng.
- **TOS:** chỉ đọc nội dung bạn có quyền, không vượt paywall, không spam.

---

## 7. Xử lý sự cố

| Triệu chứng | Cách khắc phục |
|-------------|---------------|
| `agent-reach doctor` báo `off` cho Reddit/Twitter | Thiếu cookie → `agent-reach configure …` |
| `agent-reach: command not found` | `pipx ensurepath && exec $SHELL` hoặc `~/.local/bin` chưa trong PATH |
| `playwright` timeout trên `hermes mcp install` | Bình thường — probe cần browser. Cài vẫn OK, chạy `hermes mcp configure playwright` sau. |
| BrowserMCP không kết nối (127.0.0.1:12306) | Kiểm extension đã “Connected” chưa, port có bị chiếm không |
| VPS bị 403 khi đọc X/Reddit | Thêm proxy: `agent-reach configure proxy …` |
| Hermes không thấy tools mới | `hermes chat` lại (restart session) hoặc `hermes mcp catalog` kiểm tra trạng thái |

---

## 8. File liên quan

| File | Vai trò |
|------|---------|
| `scripts/hermes-web-tools-setup.sh` | Cài + kiểm tra toàn bộ |
| `skills/hermes-web-automation/SKILL.md` | Skill Hermes (đọc chi tiết) |
| `docs/AGENT_REACH_BROWSER_MCP_RESEARCH.md` | Nghiên cứu đầy đủ |
| `agents/hermes/optional-mcps/browser-mcp/manifest.yaml` | Catalog BrowserMCP |
| `agents/hermes/optional-mcps/playwright-mcp/manifest.yaml` | Catalog Playwright MCP |
| `agents/hermes/optional-mcps/chrome-devtools-mcp/manifest.yaml` | Catalog Chrome DevTools MCP |

---

## 9. Cập nhật

```bash
# Agent Reach
agent-reach check-update
pipx upgrade agent-reach  # hoặc agent-reach update (tuỳ cách cài)

# Browser MCP
npm update -g browser-mcp
# Extension: tải bản mới từ Releases → Reload

# Playwright MCP
npx -y @executeautomation/playwright-mcp-server@latest --version
# hoặc hermes mcp install playwright (refresh manifest)

# Skill
bash scripts/hermes-sync.sh  # đồng bộ skill mới từ repo
```

---

*Xem thêm: `docs/AGENT_REACH_BROWSER_MCP_RESEARCH.md` để hiểu sâu kiến trúc và quyết định thiết kế.*
