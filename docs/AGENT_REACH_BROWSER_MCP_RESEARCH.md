# Agent Reach & Browser MCP — Nghiên cứu tích hợp cho Hermes

> **Cập nhật:** 2026-10-28 · **Tác giả:** Arena Agent (ZEUS) · **Phạm vi:** Panniantong/Agent-Reach + BrowserMCP/mcp + Chrome MCP + Playwright MCP  
> **Mục tiêu:** Cho Hermes “mắt để đọc Internet” và “tay để thao tác trình duyệt”.

---

## 0. TL;DR — Kết luận trước

| Công cụ | Vai trò | Dùng khi nào | Hermes gọi qua |
|---------|---------|--------------|----------------|
| **Agent Reach** (105k★, MIT, Python) | **ĐỌC** — gom nội dung từ 17+ nền tảng về CLI | Nghiên cứu, theo dõi MXH, debug cần context web | `terminal` → `agent-reach` + `gh`/`yt-dlp`/`mcporter` |
| **Browser MCP** (BrowserMCP/mcp 7.2k★, Apache 2.0) | **THAO TÁC** — điều khiển Chrome thật qua extension | Cần giữ login, thao tác như người dùng | `mcp_servers.browser-mcp` (HTTP 12306) |
| **Playwright MCP** (microsoft/playwright-mcp 38k★, Apache 2.0) | **THAO TÁC** — chạy browser riêng (headless) | VPS, CI, cần cô lập, không cần login sẵn | `mcp_servers.playwright` (stdio `npx`) |
| **Chrome DevTools MCP** (54k★) | **DEBUG** — DevTools + automation | Debug sâu, đo hiệu năng, network | `mcp_servers.chrome-devtools` (stdio `npx`) |
| **Chrome MCP** (hangwin/mcp-chrome 12.5k★, MIT) | **THAO TÁC** — extension 20+ tools, semantic search | Desktop, cần vector search tab | `mcp_servers.chrome-mcp` (HTTP bridge) |

**Quy tắc vàng:** Agent Reach = *đọc*, Browser MCP = *làm*. Hai nhóm **bổ trợ nhau**, không thay thế nhau.

```
Yêu cầu người dùng
        ↓
  Hermes phân loại intent
        ↓
┌───────────────┐     ┌──────────────────┐
│  Chỉ cần ĐỌC? │ yes │ Agent Reach      │ → Jina/Gh/yt-dlp/mcporter → trả Markdown
│  web, GitHub, │     │ (terminal)       │
│  YouTube, X,  │     └──────────────────┘
│  Reddit…      │
└───────┬───────┘
        │ no (cần click/form/login)
        ↓
┌───────────────┐     ┌──────────────────┐
│  Cần THAO TÁC │ →   │ Browser MCP      │ → Chrome thật hoặc Playwright
│  trình duyệt  │     │ (mcp_servers)    │ → click, fill, screenshot…
└───────────────┘     └──────────────────┘
```

---

## 1. Agent Reach — Phân tích chi tiết

### 1.1 Hồ sơ dự án

| Thuộc tính | Giá trị (28/10/2026) |
|------------|----------------------|
| Repo | `Panniantong/Agent-Reach` — https://github.com/Panniantong/Agent-Reach |
| Mô tả | *Give your AI agent eyes to see the entire internet. Read & search Twitter, Reddit, YouTube, GitHub, Bilibili, XiaoHongShu — one CLI, zero API fees.* |
| Stars / Forks | **105,414★** / 9,342 forks (tăng ~40k trong 3 tháng) |
| License | **MIT** |
| Ngôn ngữ | Python (CLI `agent-reach`), phụ thuộc Node.js `mcporter`, `gh`, `yt-dlp` |
| Phiên bản mới nhất | v1.6.0 (23/10/2026) — 444 commits |
| Cài đặt | `pipx install https://github.com/Panniantong/agent-reach/archive/main.zip && agent-reach install --env=auto` |
| Cập nhật | `agent-reach doctor` (health check), `agent-reach check-update` |

**Điểm đặc biệt:** Không phải crawler/API mới — là **lớp keo (glue layer)** cài, cấu hình, và định tuyến tới *công cụ upstream tốt nhất* cho từng nền tảng, rồi để agent gọi trực tiếp.

```
Agent Reach = Installer + Router + Doctor + Skill
         ↓             ↓           ↓        ↓
     cài gh,mcporter  chọn tool  kiểm tra  đăng SKILL.md
     yt-dlp,feedparser phù hợp   30s probe  cho Claude/Cursor
```

### 1.2 Kiến trúc

```text
User: “đọc tweet này” / “tìm Reddit về lỗi X”
         ↓
Agent (Claude Code / Hermes) đọc SKILL.md → biết tool nào dùng
         ↓
┌─────────────────────────────────────────────────────┐
│              Agent Reach CLI (Python)               │
│  install  ·  configure  ·  doctor  ·  skill         │
│  ~/.agent-reach/config.yaml (mode 600)              │
└──────────┬──────────────────────────────────────────┘
           ↓ gọi trực tiếp (không proxy)
┌──────────┼──────────┬──────────┬──────────┬─────────┐
│ Jina      │ Exa via  │ gh CLI   │ yt-dlp   │ feed   │
│ Reader    │ mcporter │ GitHub   │ YouTube  │ parser │
│ (web)     │ (search) │          │ Bili     │ (RSS)  │
├──────────┼──────────┼──────────┼──────────┼─────────┤
│ xreach    │ rdt-cli  │ bili-cli │ OpenCLI  │ miku   │
│ (Twitter) │ (Reddit) │ (Bili)   │ (XHS/FB/ │ (WeChat│
│           │          │          │  IG/Douyin)│  )     │
└──────────┴──────────┴──────────┴──────────┴─────────┘
```

### 1.3 Ma trận nền tảng (v1.6)

| Nền tảng | Không cần setup | Cần setup (cookie/login) | Backend chính |
|----------|----------------|--------------------------|---------------|
| 🌐 Web bất kỳ | ✅ Markdown qua Jina Reader | — | `curl https://r.jina.ai/URL` |
| 📺 YouTube | ✅ search + transcript | — | `yt-dlp` |
| 📡 RSS/Atom | ✅ bất kỳ feed | — | `feedparser` |
| 🔍 Web Search | — | auto (Exa miễn phí qua MCP) | `mcporter → exa.web_search_exa` |
| 📦 GitHub | ✅ public repo/search | private/I/PR → `gh auth login` | `gh CLI` |
| 🐦 Twitter/X | single tweet | search/timeline → cookie `auth_token;ct0` | `twitter-cli (xreach)` → fallback OpenCLI |
| 📕 Reddit | — (anon bị chặn 2026) | OpenCLI session hoặc `rdt-cli` + cookie | `OpenCLI` / `rdt-cli` |
| 📺 Bilibili | ✅ search + detail (bili-cli) | subtitle → OpenCLI | `bili-cli` (yt-dlp bị 412) |
| 📱 Xiaohongshu | — | OpenCLI (desktop) hoặc Cookie-Editor + mcp | `OpenCLI` / `xiaohongshu-mcp` |
| 📘 Facebook | — | OpenCLI browser session | `OpenCLI` |
| 📷 Instagram | — | OpenCLI / Graph API | `OpenCLI` |
| 💼 LinkedIn | public via Jina | full profile → mcp-server-linkedin | `mcp-server-linkedin` |
| 💻 V2EX | ✅ hot/detail/replies | — | HTTP API |
| 🎵 Douyin/WeChat/Boss | — | cookie/MCP | `mcporter`/`miku_ai` |

**Lưu ý 2026:** Reddit anon endpoints bị chặn hoàn toàn; Twitter chỉ chấp nhận cookie export thủ công (không auto-extract cho X).

### 1.4 Lệnh cốt lõi

```bash
# Cài đặt (one-liner cho agent)
pipx install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto          # tự dò Node/mcporter/gh/yt-dlp
agent-reach doctor                      # kiểm tra 30s, báo ok/warn/off/error
agent-reach doctor --json               # dạng JSON cho agent parse

# Cấu hình kênh (cookie/proxy)
agent-reach configure twitter-cookies "auth_token=xxx; ct0=yyy"
agent-reach configure xhs-cookies "a1=...; web_session=..."
agent-reach configure proxy http://user:pass@ip:port
agent-reach configure --from-browser chrome   # chỉ Bilibili/Xueqiu, auto-extract

# Quản lý skill
agent-reach skill --install             # chép SKILL.md vào ~/.agents/skills, ~/.claude/skills...
agent-reach check-update && agent-reach update

# Gọi trực tiếp (agent dùng sau khi cài)
curl -s "https://r.jina.ai/https://example.com/article"   # đọc web
gh search repos "agent framework" --limit 10
yt-dlp --write-auto-sub --skip-download "https://youtube.com/watch?v=..."
mcporter call 'exa.web_search_exa(query:"AI agent browser", numResults:5)'
```

### 1.5 Thiết kế triết lý (đáng học cho Hermes)

1. **Glue, not wrapper** — không bọc lại API, gọi thẳng upstream tool → agent ít lệ thuộc, dễ debug.
2. **Doctor pattern** — probe đồng thời, timeout 30s, báo `active_backend` rõ ràng. Hermes nên học: `hermes-web-tools-setup.sh --check`.
3. **Skill-driven routing** — `SKILL.md` dạy agent *khi nào dùng tool gì* (intent → platform), không cần code.
4. **Local-first + zero fees** — Jina/yt-dlp/feedparser/gh miễn phí; chỉ proxy tùy chọn ~$1/tháng nếu chạy trên server.
5. **An toàn cookie** — lưu `~/.agent-reach/config.yaml` mode 600, không commit, khuyến cáo dùng tài khoản phụ cho X.

### 1.6 Rủi ro & giới hạn

| Rủi ro | Mức | Giảm thiểu |
|--------|-----|------------|
| Cookie X/FB bị phát hiện → ban acc | Cao | Dùng acc phụ, không spam, proxy |
| DOM thay đổi → selector hỏng | Trung bình | Cập nhật `agent-reach update` thường xuyên |
| Reddit/X chặn IP datacenter | Cao (VPS) | Dùng proxy dân cư, hoặc chạy desktop |
| Bilibili 412 với yt-dlp | Đã khắc phục | Dùng `bili-cli` (Agent Reach đã đổi) |
| Skill phình to khi nhiều kênh | Thấp | Chỉ cài kênh cần thiết |

---

## 2. Browser MCP — Phân tích chi tiết

### 2.1 Toàn cảnh hệ sinh thái

Browser MCP không phải một repo duy nhất — là **họ công cụ MCP cho trình duyệt**, chia 2 nhánh lớn:

```
Browser MCP Ecosystem (10/2026)
├── Extension-based (dùng Chrome thật, giữ login)
│   ├── BrowserMCP/mcp (7,237★, Apache 2.0) ← GỐC, monorepo pnpm
│   └── hangwin/mcp-chrome (12,512★, MIT)    ← 20+ tools, vector search
├── Playwright-based (chạy browser riêng)
│   ├── microsoft/playwright-mcp (38,754★, Apache 2.0) ← khuyến nghị cho VPS
│   └── executeautomation/mcp-playwright (5,6k★)
└── DevTools-based (debug sâu)
    └── ChromeDevTools/chrome-devtools-mcp (54,350★, MIT)
```

### 2.2 So sánh nhanh 4 lựa chọn chính

| Tiêu chí | BrowserMCP/mcp | hangwin/mcp-chrome | microsoft/playwright-mcp | chrome-devtools-mcp |
|----------|---------------|--------------------|--------------------------|---------------------|
| **Repo** | `BrowserMCP/mcp` | `hangwin/mcp-chrome` | `microsoft/playwright-mcp` | `ChromeDevTools/chrome-devtools-mcp` |
| **Stars** | 7,237 | 12,512 | 38,754 | 54,350 |
| **License** | Apache 2.0 | MIT | Apache 2.0 | MIT |
| **Cách chạy** | Extension + `mcp` binary (HTTP 12306) | Extension + `mcp-chrome-bridge` (HTTP/SSE) | `npx chrome-devtools-mcp` (stdio) | `npx chrome-devtools-mcp` |
| **Browser** | Chrome thật của user | Chrome thật | Chromium/Firefox/WebKit riêng | Chrome (Puppeteer) |
| **Giữ login** | ✅ auto | ✅ auto | ❌ phải login lại | ❌ |
| **Isolation** | Thấp (dùng profile thật) | Thấp | Cao (clean profile) | Cao |
| **Phù hợp** | Desktop, thao tác acc thật | Desktop, cần semantic search | **VPS/CI**, automation | Debug, perf |
| **Tools** | ~15 (navigate, click, type, screenshot, upload…) | **20+** + vector DB + WASM SIMD | ~25 (snapshot, click, fill, drag, pdf…) | DevTools + automation |
| **Incognito** | ✅ (mới 10/2026) | ❌ | ✅ (browserContext) | ✅ |
| **Cài đặt** | `npm i -g browser-mcp` + load extension | `npm i -g mcp-chrome-bridge` + load extension | `npx @modelcontextprotocol/server-playwright` | `npx chrome-devtools-mcp` |

### 2.3 BrowserMCP/mcp (gốc) — chi tiết

- **Monorepo:** `apps/extension` (Chrome MV3) + `packages/mcp` (server)
- **Cập nhật 10/2026:** cho phép `upload --path` & `screenshot --path` dùng bất kỳ file trên máy; hỗ trợ incognito tabs.
- **Config Hermes (HTTP):**
  ```yaml
  mcp_servers:
    browser-mcp:
      url: "http://127.0.0.1:12306/mcp"
      type: "streamableHttp"
  ```
- **Config stdio (fallback):**
  ```yaml
  mcp_servers:
    browser-mcp-stdio:
      command: "npx"
      args: ["-y", "browser-mcp@latest"]
  ```

### 2.4 hangwin/mcp-chrome — chi tiết

- **Điểm mạnh:** 20+ tools, **semantic search** qua tab content (vector DB + WASM SIMD 4-8x), cross-tab, network monitor, bookmark/history.
- **Tools nổi bật:**
  ```text
  get_windows_and_tabs, chrome_navigate, chrome_switch_tab, chrome_close_tabs
  chrome_screenshot (element targeting, full-page)
  chrome_network_capture_start/stop, chrome_network_debugger_start/stop
  chrome_get_web_content, chrome_get_interactive_elements, search_tabs_content
  chrome_click_element, chrome_fill_or_select, chrome_keyboard
  chrome_history, chrome_bookmark_search/add/delete
  ```
- **Config:**
  ```json
  {
    "mcpServers": {
      "chrome-mcp-server": { "type": "streamableHttp", "url": "http://127.0.0.1:12306/mcp" }
    }
  }
  ```
- **Cài:** tải extension từ Releases → `npm i -g mcp-chrome-bridge` → load unpacked → connect.

### 2.5 microsoft/playwright-mcp — chi tiết

- **Điểm mạnh:** 143 device presets (iPhone, Pixel, Galaxy…), auto-install browser, accessibility snapshot (không cần screenshot), test code generation, API testing.
- **Config Hermes (stdio — khuyến nghị):**
  ```yaml
  mcp_servers:
    playwright:
      command: "npx"
      args: ["-y", "@executeautomation/playwright-mcp-server"]
  ```
  Hoặc HTTP mode: `npx @executeautomation/playwright-mcp-server --port 8931` → `url: http://localhost:8931/mcp`
- **Phù hợp VPS:** không cần Chrome sẵn, tự tải Chromium, chạy headless, cô lập tốt.

### 2.6 Chrome DevTools MCP

- **Điểm mạnh:** Cho agent quyền DevTools đầy đủ — network, console (source-mapped), performance, debugging đáng tin cậy qua Puppeteer.
- **Config:**
  ```yaml
  mcp_servers:
    chrome-devtools:
      command: "npx"
      args: ["-y", "chrome-devtools-mcp@latest"]
  ```
- **Dùng khi:** cần debug sâu, phân tích hiệu năng, kiểm tra web đang phát triển.

---

## 3. Đối chiếu: Agent Reach vs Browser MCP

| Chiều | Agent Reach | Browser MCP |
|-------|-------------|-------------|
| **Định vị** | Tầng *khả năng Internet* (installer + router) | Tầng *tự động hóa trình duyệt* |
| **Năng lực cốt lõi** | **ĐỌC** — lấy nội dung (web, MXH, video) | **THAO TÁC** — click, gõ, upload, điều hướng |
| **Nền tảng** | 17+ (X, Reddit, YouTube, Bilibili, XHS, GitHub…) | Bất kỳ web nào (qua browser) |
| **Yêu cầu login** | Cookie export hoặc browser session | Extension dùng session sẵn (hoặc login lại với Playwright) |
| **Chi phí** | Miễn phí (proxy tùy chọn) | Miễn phí (local Chrome) hoặc cloud browser |
| **Độ phức tạp** | `pipx install` + `doctor` | Extension load + MCP config |
| **Khi nào dùng** | Nghiên cứu, tổng hợp, giám sát MXH | Điền form, đăng bài, test E2E, thao tác cần login |
| **Quan hệ** | **Bổ trợ** — Reach đọc, Browser thao tác | Cùng nhau phủ “đọc + làm” |

> **Ví dụ kết hợp:** Hermes dùng Agent Reach để *tìm* 10 bài Reddit về lỗi → đọc nội dung → rồi dùng Browser MCP để *đăng* câu trả lời lên forum nội bộ.

---

## 4. Kiến trúc tích hợp cho Hermes

### 4.1 Tổng quan

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes Agent (gateway)                   │
│  ~/.hermes/config.yaml                                      │
│  ├── terminal (local/docker/ssh)                            │
│  │     └── agent-reach, gh, yt-dlp, mcporter  (CLI)         │
│  └── mcp_servers                                            │
│        ├── playwright  (stdio, VPS)                          │
│        ├── browser-mcp (http, desktop)                       │
│        └── chrome-devtools (stdio, debug)                    │
│  ~/.hermes/skills/hermes-web-automation/  (skill mới)       │
└─────────────────────────────────────────────────────────────┘
           │                    │
           ↓                    ↓
     Internet (đọc)      Browser (thao tác)
```

### 4.2 Phân loại theo môi trường triển khai

| Môi trường | Agent Reach | Browser MCP khuyến nghị | Lý do |
|------------|-------------|-------------------------|-------|
| **VPS Ubuntu (prod Hermes)** | ✅ (CLI) | `playwright-mcp` (headless) | Không có Chrome desktop, cần cô lập |
| **Codespace / Dev Container** | ✅ | `playwright-mcp` | Tương tự VPS |
| **Laptop/desktop (Hermes local)** | ✅ | `BrowserMCP/mcp` hoặc `mcp-chrome` | Giữ login, thao tác acc thật |
| **Termux/Android** | ⚠️ hạn chế (không Chrome) | ❌ | Dùng Agent Reach web/GitHub/YouTube thôi |

### 4.3 Luồng “doctor” học từ Agent Reach

Hermes sẽ có `scripts/hermes-web-tools-setup.sh --check`:

```
$ bash scripts/hermes-web-tools-setup.sh --check

[Hermes Web Tools] Kiểm tra nhanh
  ✅ agent-reach 1.6.0
  ✅ gh 2.55.0 (đã login)
  ✅ yt-dlp 2024.10.22
  ✅ mcporter 0.3.1 (Exa ready)
  ✅ Jina Reader (no key)
  ⚠️  Twitter/X — chưa có cookie (chạy: agent-reach configure twitter-cookies "...")
  ✅ playwright-mcp 1.0.10 (npx ok)
  ⬜ browser-mcp — chỉ cho desktop (bỏ qua trên VPS)
  6/7 kênh sẵn sàng
```

---

## 5. Bảo mật & vận hành

### 5.1 Nguyên tắc chung (theo ZEUS Security rules)

- **Không commit secret:** cookie, token, `~/.agent-reach/config.yaml`, `~/.hermes/.env` → `.gitignore`.
- **Lưu secret:** VPS env vars, GitHub Secrets, hoặc `~/.hermes/.env` mode 600.
- **Tài khoản thử nghiệm:** Dùng acc phụ cho X/Reddit khi test cookie; không dùng acc chính.
- **Proxy:** Khi chạy trên VPS/datacenter IP, X/Reddit dễ chặn → cấu hình `agent-reach configure proxy`.

### 5.2 Rủi ro đặc thù

| Rủi ro | Giảm thiểu |
|--------|------------|
| Ban acc do automation | Rate limit, random delay, dùng acc phụ, không spam |
| Cookie lộ qua log | Redact trong `scripts/hermes-web-tools-setup.sh`, không in ra PR |
| Extension MCP chiếm quyền browser | Chỉ cài trên profile riêng, không lưu mật khẩu quan trọng |
| Playwright tải browser nặng (~400MB) | Chỉ cài khi cần, VPS đủ disk |

### 5.3 Tuân thủ TOS

- Agent Reach dùng **phiên đăng nhập sẵn có** của user (cookie), không vượt paywall/hack.
- Chỉ đọc nội dung user có quyền truy cập; không scrape vượt rate limit.
- Đăng bài/dùng Browser MCP phải có sự đồng ý, không spam.

---

## 6. Lộ trình tích hợp (đề xuất)

### Giai đoạn 1 — Nền tảng (ngay, P1)
- [x] Nghiên cứu, viết `docs/AGENT_REACH_BROWSER_MCP_RESEARCH.md` (file này)
- [ ] Thêm skill `hermes-web-automation` (SKILL.md + script cài)
- [ ] Thêm 3 manifest `optional-mcps/{browser-mcp,playwright-mcp,chrome-devtools-mcp}`
- [ ] Script `scripts/hermes-web-tools-setup.sh` (install + doctor)

### Giai đoạn 2 — Chạy thử trên VPS (P2)
- [ ] Cài Agent Reach trên VPS Hermes: `pipx install` + `gh auth` + `mcporter`
- [ ] Cài `playwright-mcp` stdio, test: “mở example.com, chụp màn hình”
- [ ] Hermes cron thử: mỗi sáng search GitHub trending + tóm tắt

### Giai đoạn 3 — Desktop power (P3, tùy chọn)
- [ ] Cài BrowserMCP extension trên laptop, test thao tác giữ login
- [ ] Hermes local kết nối qua `http://127.0.0.1:12306/mcp`

### Giai đoạn 4 — Tự động hóa (P4)
- [ ] Workflow định kỳ: Agent Reach giám sát Reddit/Twitter keyword → báo Telegram
- [ ] FlowKit kết hợp: nghiên cứu bằng Agent Reach → tạo video

---

## 7. Tài liệu tham khảo

| Dự án | Repo | Stars | License |
|-------|------|-------|---------|
| Agent Reach | https://github.com/Panniantong/Agent-Reach | 105k | MIT |
| BrowserMCP/mcp | https://github.com/BrowserMCP/mcp | 7.2k | Apache 2.0 |
| hangwin/mcp-chrome | https://github.com/hangwin/mcp-chrome | 12.5k | MIT |
| microsoft/playwright-mcp | https://github.com/microsoft/playwright-mcp | 38.7k | Apache 2.0 |
| ChromeDevTools MCP | https://github.com/ChromeDevTools/chrome-devtools-mcp | 54k | MIT |
| executeautomation/mcp-playwright | https://github.com/executeautomation/mcp-playwright | 5.6k | MIT |
| Hermes MCP docs | https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp | — | — |

---

## 8. Phụ lục — Lệnh nhanh cho Hermes

### Agent Reach (qua `terminal`)
```bash
agent-reach doctor --json | python3 -m json.tool
curl -s "https://r.jina.ai/https://docs.hermes-agent.nousresearch.com/docs/user-guide/features/mcp"
gh search repos "browser automation mcp" --limit 5
yt-dlp --write-auto-sub --skip-download -o "/tmp/%(id)s" "https://www.youtube.com/watch?v=..."
mcporter call 'exa.web_search_exa(query:"Agent Reach vs Firecrawl", numResults:5)'
```

### Browser MCP (qua `mcp_servers` tools, sau khi `hermes mcp install`)
```text
# Hermes sẽ thấy tools như:
browser_navigate(url="https://example.com")
browser_snapshot()  # accessibility tree
browser_click(ref="e12")
browser_fill(ref="e34", value="hello")
browser_screenshot(path="/tmp/page.png")
browser_evaluate(script="document.title")
```

---

*File này được sinh tự động bởi Arena Agent — nguồn truth là GitHub API + README upstream. Cập nhật định kỳ: `scripts/hermes-web-tools-setup.sh --check` + `agent-reach check-update`.*
