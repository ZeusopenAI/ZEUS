# Status — Zeus / Quang Quý AI

Cập nhật: 2026-10-23

## Nhịp gần nhất (23/10/2026)

- **Đường ống "repo → Hermes" khép kín**: `scripts/hermes-sync.sh` đẩy skill + sinh skill
  `zeus-context` (Status/TODO/Roadmap/AGENTS/bản đồ repo/docs/git HEAD) vào runtime Hermes;
  `scripts/gen-zeus-context.py` sinh nội dung tất định, có ngân sách ký tự, không cắt cụt.
- **Ba kênh cập nhật**: Codespace tự sync mỗi lần mở (`.devcontainer/`), VPS tự sync mỗi 15 phút
  (`deploy/vps/hermes-repo-sync.{service,timer}`), và GitHub Actions cập nhật ngay khi push
  qua SSH/webhook (`.github/workflows/hermes-skill-sync.yml`).
- **Kiểm tra drift**: `scripts/hermes-doctor.sh` so skill trên máy với repo, kiểm commit của
  `zeus-context`, trạng thái gateway/timer và sự hiện diện của model key (chỉ đọc tên biến).
- **Chốt an toàn**: script VPS từ chối chạy khi sai nhánh hoặc có thay đổi chưa commit
  (`exit 3`, cần `--force` nếu chủ ý) — tránh `git reset --hard` nuốt mất việc đang làm.
- CI `hermes-skill-sync.yml` validate frontmatter (`--strict`) và chạy sync 2 lần để bắt
  lỗi không idempotent; không gọi LLM nên không tốn credit.
- **Vercel (chia đôi)**: `site/vercel.json` (static) và `flowkit/dashboard/vercel.json`
  (Vite + `api/[...path].ts` proxy về backend) đã sẵn sàng; dashboard hỗ trợ
  `VITE_WS_BASE` để realtime trỏ thẳng VPS. Hermes vẫn ở VPS vì cần process 24/7,
  `state.db` và long-polling — serverless không đáp ứng. Xem `docs/VERCEL_DEPLOY.md`.
- **Token GitHub cho Hermes**: `scripts/hermes-github-setup.sh` nhận token qua stdin
  (không qua argv, không lưu history), kiểm quyền thật, ghi `~/.hermes/.env` mode 600 và
  cấu hình `gh` làm credential helper; `--test-write` chứng minh quyền ghi bằng cách tạo/xoá
  nhánh test. `scripts/hermes-github-check.sh` chẩn đoán chỉ-đọc (token, scopes, quyền repo,
  git, thiết lập Actions). Kèm skill `hermes-github-access` + `docs/HERMES_GITHUB_TOKEN.md`.
- **Năng lực media cho Hermes**: `scripts/hermes-power-setup.sh` cài + kiểm tra một lượt
  (ffmpeg apt hoặc bản pip, Pillow, git/gh, token, parser đọc bài, media);
  `scripts/media-batch.py` xử lý ảnh/video hàng loạt (resize/crop/nén/watermark của chính
  mình, preset TikTok/Square/YouTube, trim, thumbnail, frames); `scripts/read-article.py`
  đọc bài web thành Markdown (stdlib, bỏ menu/quảng cáo). Kèm skill `hermes-media-tools`
  và `docs/HERMES_FULL_CAPABILITY.md`.

## Nhịp trước (14/10/2026)

## Nhịp gần nhất (14/10/2026)

- Dứt điểm 4 PR mở: **#9 (website `site/`) và #8 (FlowKit `flowkit/`) đã merge vào main**; #6 và #7 đóng vì nội dung đã bị main vượt qua (comment kiểm chứng trên từng PR).
- Hermes chạy thật trên Linux: cài từ `agents/hermes`, `hermes --version` OK, bộ test nhanh memory/gateway/skills **154/154 pass**.
- Bộ 24/7 sẵn sàng: `deploy/vps/` (install đã chạy thật — unit systemd chuẩn `User=hermes`, `Restart=always`, enable boot-start; healthcheck; backup đã chạy thật) + runbook `docs/RUNBOOK_247.md`.
- CI runtime mới `.github/workflows/hermes-runtime-ci.yml` cài Hermes và chạy test trên Python 3.11/3.12 mỗi khi `agents/hermes/**` hoặc `deploy/**` thay đổi.

## Tổng quan

ZEUS tiếp tục theo hướng module độc lập, cloud-first và vận hành được từ điện thoại. Hermes là runtime điều phối; FlowKit là ứng dụng AI filmmaking riêng trong `flowkit/`, không buộc chung dependency với Hermes; landing page thương hiệu là site tĩnh trong `site/` (deploy GitHub Pages thủ công qua workflow).

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
