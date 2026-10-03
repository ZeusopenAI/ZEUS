# ZEUS — Hệ Thống AI Automation Cá Nhân (ZeusopenAI)

> **"GỌI BẤT KỲ AI NÀO KHI CẦN NGAY TRÊN BÀN PHÍM ĐIỆN THOẠI & TRÌNH DUYỆT"**

Dự án AI Automation cá nhân và trợ lý đa năng cho thương hiệu cá nhân **Nguyễn Quang Quý**. Tối ưu cho vận hành gọn nhẹ (Phone/Cloud-first), các module độc lập và dễ bảo trì.

---

## 🎯 Mục Tiêu & Triết Lý

- **Cá nhân hóa & Linh hoạt:** Các module tách biệt, vận hành độc lập; không buộc chung dependency hoặc runtime.
- **Cloud-First & Mobile-First:** Điều khiển và chạy tác vụ từ điện thoại (Telegram / GitHub Actions / Google Colab / trình duyệt).
- **Phối hợp Đa Model (Multi-Model Routing):**
  - **Hermes Agent (Local / Cloud):** Điều phối, chạy tool, lập trình và thực thi tác vụ.
  - **ChatGPT / OpenRouter:** Chiến lược, kế hoạch, copywriting, tạo ảnh.
  - **Claude:** Kiến trúc chuyên sâu, refactoring mã nguồn.
  - **Gemini:** Nghiên cứu tài liệu, media, xử lý Colab/Python.
- **Bộ nhớ thứ hai (Second Brain):** Gom lịch sử trao đổi từ nhiều trợ lý AI về kho Markdown thống nhất, có lọc secrets.

---

## 📂 Cấu Trúc Kho Mã Nguồn

```text
.
├── .github/workflows/          # Tự động hóa GitHub Actions
│   ├── hermes-openrouter.yml   # Chạy Hermes Agent + tạo ảnh bằng OpenRouter
│   ├── arena-auto-pr.yml       # Tự động mở PR khi có cập nhật code từ Arena
│   ├── flowkit-ci.yml          # Kiểm thử backend, extension và dashboard FlowKit
│   └── validate-hermes-integration.yml # Kiểm tra snapshot Hermes
├── agents/
│   └── hermes/                 # Runtime Hermes AI Agent
├── colab/
│   └── bootstrap.py            # Script khởi động tự động trên Google Colab
├── docs/                       # Tài liệu hướng dẫn & vận hành
│   ├── FLOWKIT_INTEGRATION.md  # Hướng dẫn chạy FlowKit trong ZEUS
│   ├── HERMES_ACTIONS.md       # Hướng dẫn chạy Hermes qua GitHub Actions
│   ├── TELEGRAM_WIRING.md      # Runbook kết nối Telegram Webhook
│   ├── second-brain.md         # Hướng dẫn gom bộ nhớ ChatGPT/Claude/Gemini
│   ├── COLAB_COMFYUI.md        # Hướng dẫn ComfyUI / Stable Diffusion trên Colab
│   ├── CLOUD_ARCHITECTURE.md  # Kiến trúc vận hành Cloud-First
│   └── SecretManagement.md    # Quy tắc quản lý biến môi trường và khóa API
├── flowkit/                    # Ứng dụng làm phim AI độc lập
│   ├── agent/                  # Backend FastAPI + SQLite và pipeline video
│   ├── extension/              # Chrome MV3 bridge tới Google Flow
│   ├── dashboard/              # Dashboard React/Vite
│   ├── skills/                 # Workflow skills cho FlowKit
│   └── tests/                  # Kiểm thử backend và extension
├── scripts/                    # Bộ công cụ & script tiện ích
│   ├── second-brain-import.mjs # Import lịch sử chat (Node.js >= 22)
│   ├── second-brain/           # Chuẩn hóa hội thoại
│   ├── hermes-gemini-hotfix.sh # Sửa lỗi xác thực Gemini native
│   ├── hermes-gemini-auth-recover.sh # Khôi phục key Gemini an toàn
│   └── sync-to-zeusopenai.sh   # Đồng bộ mã nguồn sang ZeusopenAI/ZEUS
├── skills/                     # Kỹ năng tùy chỉnh cho Agent
│   ├── qai-developer-manager/  # Kỹ năng kỹ sư trưởng quản lý code & CI
│   ├── hermes-project-analyst-code-manager/ # Phân tích & chẩn đoán Hermes
│   ├── flowkit-ai-filmmaker/   # Hướng dẫn vận hành AI filmmaking
│   └── second-brain/           # Kỹ năng tra cứu bộ nhớ dùng chung
└── worker/
    └── telegram-proxy/         # Cloudflare Worker proxy cho Telegram Webhook
```

---

## 🚀 Các Tính Năng Nổi Bật

### 1. Chạy Hermes Agent trên GitHub Actions (`hermes-openrouter.yml`)
- Chạy tác vụ AI theo yêu cầu, không cần máy tính bật 24/7.
- Hỗ trợ tạo ảnh và sinh code/văn bản qua OpenRouter.
- Kết quả tự động tải về qua Artifacts hoặc mở Pull Request.

### 2. Bộ Nhớ Thứ Hai (Second Brain Importer)
- Nhập lịch sử chat từ ChatGPT (`conversations.json`), Claude.ai và Google Gemini Takeout thành ghi chú Markdown.
- Chạy bằng Node.js ≥ 22:
  ```bash
  node scripts/second-brain-import.mjs import chatgpt --from ~/Downloads/conversations.json
  node scripts/second-brain-import.mjs import claude-ai --from ~/Downloads/claude-export/
  node scripts/second-brain-import.mjs import gemini --from ~/Downloads/Takeout/Gemini/
  node scripts/second-brain-import.mjs ingest --from ~/Downloads/ai-inbox/
  ```

### 3. Telegram Webhook Proxy (`worker/telegram-proxy/`)
- Cloudflare Worker proxy mỏng, không lưu token bot hay key mô hình tại edge.
- Chuyển tiếp webhook về Hermes Gateway, tránh nhiều consumer tranh chấp cập nhật Telegram.

### 4. FlowKit — AI Filmmaking (`flowkit/`)
- Tích hợp ứng dụng FlowKit đầy đủ vào ZEUS: Python/FastAPI agent, Chrome MV3 extension, dashboard React, workflow skills và bộ kiểm thử.
- Chạy riêng trong thư mục con, không buộc dependency của FlowKit vào Hermes:
  ```bash
  cd flowkit
  ./setup.sh
  export FLOW_PROJECT_ID="<UUID dự án đã tạo trong Google Flow>"
  source venv/bin/activate
  python -m agent.main
  ```
- Cần đăng nhập Google Flow trong Chrome, giữ tab mở và nạp `flowkit/extension/` bằng Developer mode → Load unpacked.
- Hướng dẫn đầy đủ: [docs/FLOWKIT_INTEGRATION.md](docs/FLOWKIT_INTEGRATION.md).

### 5. Tác Vụ Nặng trên Google Colab (`colab/`)
- Mở Colab trên điện thoại và chạy `colab/bootstrap.py` để thực thi ComfyUI hoặc tác vụ media.

---

## 🔒 Quy Tắc Bảo Mật Bắt Buộc

1. **Không commit API key, token, mật khẩu, cookie hoặc file `.env` lên GitHub.**
2. Nạp credentials qua GitHub Secrets, Cloudflare Worker Secrets hoặc biến môi trường được bảo vệ.
3. Dùng `second-brain-import` để lọc secrets trước khi lưu dữ liệu lịch sử chat.
4. Mọi tác vụ nhạy cảm (xóa dữ liệu, triển khai production) cần sự xác nhận của người quản trị.

---

## 📖 Tài Liệu Chi Tiết

- [Kiến trúc hệ thống](Architecture.md)
- [Trạng thái hiện tại](Status.md)
- [Kế hoạch & Nhiệm vụ](TODO.md)
- [Lộ trình phát triển](Roadmap.md)
- [Vận hành & Triển khai](Deployment.md)
- [Tác vụ Agent](AGENTS.md)
- [Hướng dẫn FlowKit](docs/FLOWKIT_INTEGRATION.md)
- [Chạy Hermes Actions](docs/HERMES_ACTIONS.md)
- [Kết nối Telegram Bot](docs/TELEGRAM_WIRING.md)
- [Bộ nhớ thứ hai](docs/second-brain.md)
- [ComfyUI Colab](docs/COLAB_COMFYUI.md)
