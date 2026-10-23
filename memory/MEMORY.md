# ZEUS / QUANG QUÝ AI — CORE MEMORY (SINGLE SOURCE OF TRUTH)

## 1. Hồ sơ Operator
* **Nguyễn Quang Quý (1992, TP.HCM)** — Marketing Manager (8+ năm kinh nghiệm, Thiện Thành Limousine, LUNI Fashion), sáng lập **Quang Quý AI** (MIMI Project v1.0) & **Zeus / ZeusopenAI**.
* **Mục tiêu:** Tự động hóa 98%, can thiệp con người 2%. Stack: Next.js, Tailwind, TypeScript, Make.com, Telegram, Gemini API, Hermes.

## 2. Kiến thức & Kỹ năng Đã Lưu Trữ
* **Hệ thống Bộ nhớ thứ hai (Second Brain):** Ingest hội thoại đa nguồn (ChatGPT, Claude, Gemini) qua `scripts/second-brain-import.mjs`.
* **FlowKit AI Filmmaker (`flowkit/`, `memory/flowkit-ai-filmmaking.md`):** Ứng dụng độc lập gồm FastAPI/SQLite agent, Chrome MV3 bridge tới Google Flow, dashboard React, workflow skills và FFmpeg pipeline. Hướng dẫn chạy tại `docs/FLOWKIT_INTEGRATION.md`.
* **Telegram Webhook Edge Proxy (`worker/telegram-proxy/`):** Proxy mỏng giải quyết triệt để lỗi xung đột 409 khi kết nối bot Telegram 24/7.
* **Hermes OpenRouter Actions (`.github/workflows/hermes-openrouter.yml`):** Runner tạo ảnh và thực thi agent qua GitHub Actions miễn phí.
* **Hermes Owner Protocol (2026-10-23):** Hermes là chủ repo; mọi phiên agent chạy `bash scripts/hermes-session-boot.sh` (ĐIỀU 0 trong `AGENTS.md`) để nhận mệnh lệnh có seal, hết hạn/không có lệnh thì dừng; kết phiên ghi `OUTBOX.md`; workflow `hermes-owner-loop.yml` ban hành lệnh mới qua OpenRouter. Đặc tả: `docs/HERMES_OWNER_PROTOCOL.md`.
