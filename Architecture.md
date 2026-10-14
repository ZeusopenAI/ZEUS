# Architecture — Zeus / Quang Quý AI

Cập nhật: 2026-10-03

## 1. Vai trò hệ thống

ZEUS là hệ thống AI Automation cá nhân cho thương hiệu **Nguyễn Quang Quý**. Hermes Agent điều phối Telegram và các tác vụ automation; những ứng dụng độc lập như FlowKit được duy trì theo module riêng, không buộc chung runtime hoặc dependencies với Hermes. GitHub Actions, Cloudflare Workers, Google Colab và Google Drive hỗ trợ vận hành từ điện thoại.

## 2. Kiến trúc logic

```text
Người dùng (Điện thoại / Trình duyệt)
  ├─ Telegram ──► Cloudflare Worker ──► Hermes Agent (`agents/hermes/`)
  ├─ GitHub Actions ─────────────────► Hermes task runner
  ├─ FlowKit (`flowkit/`) ───────────► App làm phim AI độc lập
  │    ├─ FastAPI + SQLite agent
  │    ├─ Chrome MV3 bridge ─────────► Google Flow (tab đã đăng nhập)
  │    └─ React dashboard
  └─ Google Colab (ComfyUI / GPU tác vụ media)
```

Hermes tiếp tục xử lý multi-model routing, Second Brain, tools và đồng bộ output. FlowKit dùng pipeline và cấu hình riêng, phù hợp cho sản xuất video AI; không cần cài hay khởi động Hermes để chạy FlowKit.

## 3. Kiến trúc triển khai

```text
+-----------------------+      +---------------------------+
|    GitHub Actions     |      |    Cloudflare Worker      |
|  (Hermes task runner) |      | (Telegram Webhook Proxy)  |
+-----------------------+      +---------------------------+
            |                                |
            |                                v
            +-------------------------> Hermes Gateway

Google Flow tab đã đăng nhập ◄──► Chrome MV3 extension
                                         │ WebSocket
                                         ▼
                                  FlowKit FastAPI agent
                                    │             │
                                    │             └── SQLite / FFmpeg
                                    ▼
                                  React dashboard
```

1. **GitHub Actions:** Chạy các tác vụ một lần theo workflow.
2. **Cloudflare Worker:** Proxy Telegram Webhook, không lưu key; chuyển tiếp về Hermes Gateway.
3. **FlowKit (`flowkit/`):** App độc lập gồm FastAPI/SQLite agent, browser bridge và dashboard. Google Flow cần tab Chrome đã đăng nhập.
4. **Google Colab:** GPU tạm thời cho ComfyUI và tác vụ media nặng.
5. **Second Brain:** Module độc lập trích xuất lịch sử các AI bên ngoài về Markdown.

## 4. Ranh giới dữ liệu & Bảo mật

- **GitHub Repository (`ZeusopenAI/ZEUS`):** Lưu mã nguồn, workflow, tài liệu và script; không lưu secret hay file `.env`.
- **GitHub Secrets:** Lưu credentials phục vụ Actions.
- **`~/.hermes/` (local runtime):** Lưu config cục bộ, session, memory imports và logs với quyền truy cập hạn chế.
- **Cloudflare Worker Secrets:** Lưu `WEBHOOK_SECRET` và `UPSTREAM_URL`.
- **FlowKit:** Nạp thông tin nhạy cảm qua biến môi trường hoặc cấu hình runtime local; không commit key, cookie hay token. Xem [docs/FLOWKIT_INTEGRATION.md](docs/FLOWKIT_INTEGRATION.md).

## 5. Cấu trúc thư mục

```text
ZEUS/
  .github/workflows/    # Workflows tự động hóa Actions
  agents/hermes/        # Runtime Hermes AI Agent
  colab/                # Script khởi động trên Google Colab
  docs/                 # Runbook, tài liệu kiến trúc và hướng dẫn
  flowkit/              # App AI filmmaking: agent, extension, dashboard, skills, tests
  scripts/              # Công cụ second-brain, hotfix và đồng bộ
  skills/               # Kỹ năng tùy chỉnh cho Agent
  worker/               # Cloudflare Worker proxy cho Telegram
```
