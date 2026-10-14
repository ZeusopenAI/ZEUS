# Status — Zeus / Quang Quý AI

Cập nhật: 2026-10-03

## Tổng quan

ZEUS tiếp tục theo hướng module độc lập, cloud-first và vận hành được từ điện thoại. Hermes là runtime điều phối; FlowKit là ứng dụng AI filmmaking riêng trong `flowkit/`, không buộc chung dependency với Hermes.

## Các thành phần

### 1. Hermes Agent Runtime (`agents/hermes/`)
- Runtime Hermes tích hợp sẵn, hỗ trợ các mô hình AI và công cụ automation.
- Quy trình kiểm tra Hermes nằm trong các workflow và tài liệu `docs/HERMES_*`.

### 2. GitHub Actions Runner (`.github/workflows/hermes-openrouter.yml`)
- Chạy tác vụ một lần qua OpenRouter, tải artifacts hoặc mở Pull Request.
- `arena-auto-pr.yml` tự tạo/cập nhật PR cho nhánh Arena.

### 3. Bộ nhớ thứ hai (Second Brain)
- Import ChatGPT, Claude.ai và Google Gemini vào Markdown qua `scripts/second-brain-import.mjs`.
- Chạy bằng Node.js ≥ 22 và lọc secrets trong dữ liệu import.

### 4. Telegram Webhook Proxy (`worker/telegram-proxy/`)
- Cloudflare Worker proxy webhook Telegram tới Hermes Gateway.
- Hướng dẫn và runbook: `docs/TELEGRAM_WIRING.md`.

### 5. FlowKit AI Filmmaker (`flowkit/`)
- Tích hợp snapshot mã nguồn `ZeusopenAI/flowkit` (commit `d7977fd51b87d4da2a25a05b896f5cdac064e030`) vào ZEUS; giữ nguyên MIT license.
- Bao gồm FastAPI/SQLite agent, Chrome MV3 extension, React dashboard, workflow skills và tests.
- Đã loại bỏ giá trị API-key-shaped hard-coded không được dùng khỏi snapshot; nếu giá trị upstream từng là credential thật, cần thu hồi/rotate tại Google Cloud. Xem `docs/FLOWKIT_INTEGRATION.md`.
- Kiểm thử local: 365/365 Python unit tests, extension regression test và dashboard production build đều đạt. Dashboard build còn cảnh báo chunk JavaScript lớn hơn 500 kB; build vẫn thành công.
- CI mới: `.github/workflows/flowkit-ci.yml` (secret-pattern scan, Python 3.10/3.13 tests, extension test và dashboard build).

### 6. Google Colab & Media Automation (`colab/`, `docs/COLAB_COMFYUI.md`)
- `colab/bootstrap.py` trỏ về repo `ZeusopenAI/ZEUS`.
- Tài liệu hướng dẫn chạy ComfyUI và tác vụ media trên Colab.

## Repository & Chiến lược

- **Canonical Repository:** `ZeusopenAI/ZEUS` (`main` sau khi pull request được duyệt/merge).
- **FlowKit source-of-truth trong thay đổi này:** `flowkit/`; snapshot provenance tại `flowkit/.quang-quy-source-commit`.
- **Triết lý:** Cá nhân hóa, cloud-first, modular; các ứng dụng độc lập giữ dependency và quy trình riêng.
