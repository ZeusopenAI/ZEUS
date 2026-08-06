# Architecture — Quang Quý AI

Cập nhật: 2026-08-06

## 1. Vai trò hệ thống

Hermes Agent là AI Manager và orchestration runtime. Nó không thay thế GitHub, Notion, Drive hoặc Make; nó điều phối các hệ thống đó qua provider, skill, plugin, CLI hoặc API có scope rõ ràng.

## 2. Kiến trúc logic

```text
Người dùng
  ├─ Telegram (kênh vận hành chính)
  ├─ CLI/TUI Termux (quản trị và dự phòng)
  └─ Web/Desktop (tùy chọn)
          │
          ▼
Hermes Gateway / Session Router
          │
          ▼
Hermes AI Manager
  ├─ Model routing
  │    ├─ OpenAI Codex / ChatGPT (đang hoạt động)
  │    ├─ Claude / Anthropic (kế hoạch)
  │    └─ Gemini (kế hoạch)
  ├─ Skills và tools
  │    ├─ GitHub (`git`, `gh`)
  │    ├─ Notion
  │    ├─ Google Workspace / Drive
  │    ├─ Hugging Face
  │    └─ Terminal/file/browser
  ├─ Plugins/adapters
  │    ├─ Telegram
  │    └─ Make webhook/API
  ├─ Memory, sessions, cron và kanban
  └─ Approval/policy boundary
          │
          ▼
Dịch vụ ngoài: GitHub · Notion · Drive · Make · Hugging Face
```

## 3. Kiến trúc triển khai

### Hiện tại — Android/Termux

```text
Android boot
  → Termux:Boot (chưa cài)
  → ~/.termux/boot/01-hermes
  → wake lock + delay 30s
  → ~/bin/start-hermes-background.sh
  → tmux session `hermes`
  → ~/hermes-env/bin/python -m hermes_cli.main
  → restart sau 15s nếu process thoát
```

Termux phù hợp cho development, quản trị di động và fallback. Android có thể dừng ứng dụng do battery policy; vì vậy không được coi là production HA.

### Mục tiêu — VPS

- VPS chạy Hermes Gateway 24/7 dưới service manager.
- Android là thiết bị điều khiển qua Telegram/SSH/VPN, không phải single point of failure.
- GitHub là source of truth và CI/CD control plane.
- Runtime state, secrets và backup tách khỏi Git repository.

## 4. Ranh giới dữ liệu

- GitHub: code, tài liệu kỹ thuật, workflow, placeholder config.
- `HERMES_HOME`: config runtime, OAuth state, session/memory và log; permission riêng tư.
- Secret manager/GitHub Secrets: production credentials.
- Notion: knowledge/project pages, không lưu API key.
- Drive: tài liệu lớn, media và backup encrypted.
- Make: connection vault và scenario-level credentials.

## 5. Nguyên tắc tích hợp

1. Mở rộng ở edge: ưu tiên config → skill/CLI → plugin/MCP; tránh thêm core tool.
2. Least privilege: mỗi integration có credential riêng và scope nhỏ nhất.
3. Human-in-the-loop: deploy production, gửi dữ liệu, đăng công khai, xóa hoặc phát sinh chi phí cần approval.
4. Idempotency: webhook/job có idempotency key và giới hạn retry.
5. Observability: correlation ID, structured log, health check và budget alert.
6. Cache safety: không đổi system prompt/toolsets giữa một conversation đang chạy.

## 6. Repository layout đích

```text
quangquy-ai/
  apps/                  # sản phẩm/landing page
  services/              # API và service riêng của Quang Quý
  integrations/          # adapter riêng (khi phát sinh)
  automations/          # Make/n8n specs và webhook contracts, không chứa secret
  config/hermes/         # overlay/config không chứa secret
  deploy/                # VPS/container manifests
  vendor/hermes-agent/   # submodule pin technical fork bằng SHA đã duyệt
  docs/                 # runbook, audit, ADR
  scripts/              # update/validate/deploy scripts
  .github/workflows/    # CI/CD đã pin SHA
```

Hiện tại `agents/hermes/` là snapshot copy, không phải history-preserving merge. Mục tiêu là giữ ranh giới repository bằng submodule/version pin. Nếu bắt buộc monorepo, dùng subtree không squash. Không tạo fork tùy biến sâu nếu có thể giải bằng skill/plugin/config; điều này giữ đường cập nhật upstream đơn giản.
