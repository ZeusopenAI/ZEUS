# ZEUS / QUANG QUÝ AI — CORE MEMORY (SINGLE SOURCE OF TRUTH)

## 1. Hồ sơ Operator
* **Nguyễn Quang Quý (1992, TP.HCM)** — Marketing Manager (8+ năm kinh nghiệm, Thiện Thành Limousine, LUNI Fashion), sáng lập **Quang Quý AI** (MIMI Project v1.0) & **Zeus / ZeusopenAI**.
* **Mục tiêu:** Tự động hóa 98%, can thiệp con người 2%. Stack: Next.js, Tailwind, TypeScript, Make.com, Telegram, Gemini API, Hermes.

## 2. Kiến thức & Kỹ năng Đã Lưu Trữ
* **Hệ thống Bộ nhớ thứ hai (Second Brain):** Ingest hội thoại đa nguồn (ChatGPT, Claude, Gemini) qua `scripts/second-brain-import.mjs`.
* **FlowKit AI Filmmaker (`flowkit/`, `memory/flowkit-ai-filmmaking.md`):** Ứng dụng độc lập gồm FastAPI/SQLite agent, Chrome MV3 bridge tới Google Flow, dashboard React, workflow skills và FFmpeg pipeline. Hướng dẫn chạy tại `docs/FLOWKIT_INTEGRATION.md`.
* **Telegram Webhook Edge Proxy (`worker/telegram-proxy/`):** Proxy mỏng giải quyết triệt để lỗi xung đột 409 khi kết nối bot Telegram 24/7.
* **Hermes OpenRouter Actions (`.github/workflows/hermes-openrouter.yml`):** Runner tạo ảnh và thực thi agent qua GitHub Actions miễn phí.
* **Hermes Owner Protocol — CHÍNH SÁCH MỚI 2026-10-28 (ghi đè ghi chú 23/10):** Hermes **không còn là chủ** mà là kênh cố vấn **TÙY CHỌN**. AI **có thể gọi hoặc không gọi** `bash scripts/hermes-session-boot.sh`; `boot` mặc định luôn thoát 0 (in "KHÔNG BẮT BUỘC, KHÔNG CHẶN PHIÊN"), mã 3/4/5/6 chỉ là tín hiệu. Không có gợi ý / hết hạn / seal sai / workflow lỗi / thiếu key ⇒ **tiếp tục làm theo yêu cầu trực tiếp của Operator**. Báo cáo `OUTBOX.md` và workflow `hermes-owner-loop.yml` đều tùy chọn. Chế độ cũ chỉ khi Operator bật `--strict` / `HERMES_OWNER_STRICT=1`. Lý do: workflow lỗi tách marker 2 lượt (24/10) làm `INBOX.md` trống, luật ĐIỀU 0 cũ biến đó thành lỗi chặn mọi phiên chat. Luật gốc: `AGENTS.md` ĐIỀU 0 · RCA: `docs/HERMES_SESSION_ERROR_RCA.md` · Đặc tả: `docs/HERMES_OWNER_PROTOCOL.md`.
