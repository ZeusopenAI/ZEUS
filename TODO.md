# TODO — Zeus / Quang Quý AI

Cập nhật: 2026-09-17

## P0 — Đã hoàn thành (Core & Automation)

- [x] Tinh gọn repository, loại bỏ monorepo/openclaw cồng kềnh, chuyển hướng quản lý sang mô hình cá nhân gọn nhẹ `ZeusopenAI/ZEUS`.
- [x] Tích hợp workflow GitHub Actions chạy Hermes Agent qua OpenRouter (`.github/workflows/hermes-openrouter.yml`).
- [x] Tích hợp workflow tự động mở PR khi code được đẩy từ Arena (`.github/workflows/arena-auto-pr.yml`).
- [x] Xây dựng công cụ độc lập Second Brain Importer (`scripts/second-brain-import.mjs` + `scripts/second-brain/`) kèm bộ test 20/20 PASS.
- [x] Triển khai Cloudflare Worker Proxy cho Telegram Webhook (`worker/telegram-proxy/`) và viết runbook xử lý lỗi xung đột 409 (`docs/TELEGRAM_WIRING.md`).
- [x] Xây dựng kỹ năng `qai-developer-manager` và `second-brain` trong `skills/`.
- [x] Viết script đồng bộ code sang `ZeusopenAI/ZEUS` (`scripts/sync-to-zeusopenai.sh`).

## P1 — Vận hành & Cấu hình dịch vụ ngoài

- [ ] Đồng bộ toàn bộ branch này sang `ZeusopenAI/ZEUS` bằng `scripts/sync-to-zeusopenai.sh`.
- [ ] Thêm secret `OPENROUTER_API_KEY` vào GitHub Repository Secrets của `ZeusopenAI/ZEUS` để chạy Actions.
- [ ] Deploy Cloudflare Worker `zeus-telegram-proxy` và nạp `WEBHOOK_SECRET` + `UPSTREAM_URL`.
- [ ] Cấu hình bot Telegram mới từ @BotFather và nối vào Hermes Gateway.
- [ ] Nhập file lịch sử chat gần nhất từ ChatGPT / Claude / Gemini vào Second Brain (`node scripts/second-brain-import.mjs ingest --from ...`).

## P2 — Mở rộng & Tự động hóa nâng cao

- [x] Nghiên cứu Agent Reach (105k★, MIT) & Browser MCP (BrowserMCP 7.2k★, Playwright 38k★, Chrome-MCP 12.5k★) trên GitHub, cập nhật vào repo cho Hermes: `docs/AGENT_REACH_BROWSER_MCP_RESEARCH.md`, `docs/HERMES_WEB_AUTOMATION.md`, skill `hermes-web-automation`, script `scripts/hermes-web-tools-setup.sh`, 3 manifest `optional-mcps/{browser-mcp,playwright-mcp,chrome-devtools-mcp}` (28/10/2026).
- [ ] Cài thử Agent Reach + Playwright MCP trên VPS Hermes: `bash scripts/hermes-web-tools-setup.sh --install` → `agent-reach doctor` → test “mở example.com, chụp màn hình” qua Hermes.
- [ ] Lập lịch tải export định kỳ từ Google Takeout / ChatGPT để nạp tự động vào Second Brain.
- [ ] Thiết lập quy tắc điều phối đa model (Multi-Model Routing) trong prompt hệ thống của Hermes.
- [x] Chuẩn bị bộ 24/7 cho Hermes Gateway: `deploy/vps/install-hermes-vps.sh` (cài tự động, đã chạy thật trên Linux: unit `hermes-gateway.service` sinh chuẩn — `User=hermes`, `Restart=always`, enable boot-start, `systemd-analyze verify` pass), `deploy/vps/healthcheck.sh`, `deploy/vps/backup-hermes.sh` (đã chạy thật), runbook `docs/RUNBOOK_247.md` (14/10/2026).
- [x] Chạy Hermes + test suite trên Linux: `pip install agents/hermes` OK, `hermes --version` OK, bộ test nhanh memory/gateway/skills **154/154 pass** (pytest + pytest-asyncio); CI `.github/workflows/hermes-runtime-ci.yml` chạy lại tự động trên Python 3.11/3.12 (14/10/2026).
- [ ] Triển khai lên VPS Ubuntu thật: mua VPS → chạy `deploy/vps/install-hermes-vps.sh` → điền `.env` → vượt 4 gate kiểm chứng trong `docs/RUNBOOK_247.md` (healthcheck HEALTHY, round-trip Telegram, reboot drill, crash drill).
- [ ] Cài Termux:Boot + reboot thật trên Android (con đường dự phòng, 3 bằng chứng trong `docs/RUNBOOK_247.md` phần B).
- [ ] Tích hợp Google Colab notebook với Google Drive để lưu ảnh/video sinh ra từ ComfyUI.
- [ ] Theo dõi chi phí model qua dashboard OpenRouter và thiết lập giới hạn ngân sách hàng tháng.

## P3 — Website thương hiệu cá nhân (`site/`)

- [x] Code lại landing page từ Google Sites thành site tĩnh trong `site/` (HTML/CSS/JS thuần, không build step) — xem `docs/QUANGQUY_WEBSITE.md`.
- [x] Mở rộng nội dung: 6 dịch vụ kèm KPI, timeline 14 ngày, bảng trước/sau, 3 gói giá, 8 FAQ, demo chatbot tương tác.
- [x] Thêm SEO đầy đủ (canonical, OG image 1200×630, JSON-LD Person + Service + FAQPage), favicon, robots.txt, sitemap.xml.
- [ ] Chốt nội dung cuối: tên miền thật, email, giá 3 gói (danh sách trong `site/content.md` mục 16).
- [ ] Bật GitHub Pages (Settings → Pages → Source: GitHub Actions) rồi chạy workflow `deploy-quangquy-site.yml` — cần Quý xác nhận vì là deploy public.
- [ ] (Tuỳ chọn) Nối form tư vấn vào webhook nhận lead tự động qua `CONFIG.formEndpoint`.
- [x] Viết smoke test jsdom (`scripts/site-smoke-test.mjs`) + CI `site-check.yml` cho `site/**`; test đã phát hiện và sửa 2 lỗi UX ở demo chatbot.

## Quy tắc hoàn thành

Một mục chỉ được đánh dấu xong khi có kết quả thực tế hoặc lệnh kiểm tra chứng minh. Tuyệt đối không commit credential, không tự động hóa hành động phát sinh chi phí mà không có xác nhận của người quản trị.
