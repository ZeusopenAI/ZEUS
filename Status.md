# Status — Zeus / Quang Quý AI

Cập nhật: 2026-10-28

## Nhịp gần nhất (28/10/2026) — Hermes chuyển sang TÙY CHỌN

- **Sự cố "gọi Hermes làm chủ phiên chat" đã được xử lý tận gốc.** Ngày 23/10 giao thức
  Hermes Owner được dựng như một **cổng chặn cứng**: `AGENTS.md` ĐIỀU 0 bắt mọi phiên chạy
  `hermes-session-boot.sh`, và thiếu lệnh thì **dừng**. Workflow `hermes-owner-loop.yml`
  sau đó lỗi 2 lượt (run `40062072101`, `40062270254`) ở bước "Tách khối mệnh lệnh" do model
  trả marker lệch ⇒ `INBOX.md` chưa từng có nội dung ⇒ `boot` luôn trả 3 ⇒ mọi phiên chat bị
  chặn. Thêm vào đó `HERMES_OWNER_AUTO` không bật (các lượt schedule bị `skipped`), TTL 72h và
  sandbox Arena không có key/binary Hermes. Chi tiết: `docs/HERMES_SESSION_ERROR_RCA.md`.
- **Repo tham khảo `mexicat/pdoom-video` đã được học và thử nghiệm.** Ghi chú kiến trúc +
  đối chiếu ZEUS tại `docs/REFERENCE_PDOOM_VIDEO.md`; quy trình nâng chất lượng video AI tại
  `docs/REFERENCE_VIDEO_QUALITY_PIPELINE.md`. Prototype `prototypes/deterministic-render/` chạy
  thật: cùng `drawFrame(project,t)` cho preview Chrome và export headless → ffmpeg, 11 test xanh,
  CI riêng `deterministic-render-ci.yml`, contact sheet QA, `--scale 2` và `--samples 4`.
- **Toàn bộ luật đã đổi sang "có thể gọi Hermes, không bắt buộc".** Sửa đồng bộ:
  `AGENTS.md` (ĐIỀU 0), `.ai/CONSTITUTION.md`, `README.md`, `Status.md`, `memory/MEMORY.md`,
  `.ai/handoff/{INBOX.md,README.md,STATE.json,OUTBOX.md}`, `docs/HERMES_OWNER_PROTOCOL.md`,
  `skills/hermes-owner/SKILL.md`, `scripts/hermes_owner.py`, `scripts/hermes_owner_brief.py`,
  2 wrapper, `scripts/gen-zeus-context.py`, workflow `hermes-owner-loop.yml` và CI giao thức.
- **Engine:** `boot` mặc định luôn thoát 0, in "KHÔNG BẮT BUỘC, KHÔNG CHẶN PHIÊN" và JSON
  `blocking: false`. Mã 3/4/5/6 chỉ là tín hiệu trạng thái. Chế độ cũ chỉ tồn tại dưới
  `--strict` / `HERMES_OWNER_STRICT=1` do Operator bật rõ; AI không tự bật.
- **Workflow không còn là điểm lỗi duy nhất:** parser `extract` chịu marker lệch
  (`<<< ZEUS_DIRECTIVE >>>`, bọc `**…**`, chữ thường, code fence) + dự phòng theo tiêu đề;
  nếu vẫn không tách được thì workflow cảnh báo rồi bỏ qua thay vì đỏ, vì gợi ý là tùy chọn.
- **Chống hồi quy:** `scripts/tests/test_hermes_optional_rules.py` kiểm tra các file luật không
  còn câu kiểu "Hermes làm chủ / bắt buộc / dừng phiên", và `boot` wrapper thoát 0 khi thiếu gợi ý;
  CI `hermes-owner-protocol-ci.yml` chạy toàn bộ `test_hermes*.py`.

## Nhịp trước (23/10/2026) — đã thay thế bởi chính sách tùy chọn ở trên

- **CI toàn repo được pin SHA**: policy của repo chuyển sang chế độ “chỉ cho phép action do GitHub
  tạo / thuộc ZeusopenAI / verified Marketplace **và phải pin bằng commit SHA đầy đủ**”, khiến mọi
  workflow dùng `actions/checkout@v4`… chết ngay ở bước khởi động (`startup_failure` 0s). Đã pin
  toàn bộ `uses:` trong 14 workflow sang SHA 40 ký tự kèm comment phiên bản.
- **Hermes Owner Protocol — ban đầu là "chủ", nay là kênh TÙY CHỌN**: giao thức vẫn gồm
  `.ai/handoff/INBOX.md` (gợi ý có front matter + seal SHA-256, hạn 72h), `OUTBOX.md`
  (báo cáo tùy chọn), `STATE.json` (`policy: "optional"`), engine stdlib
  `scripts/hermes_owner.py` và workflow `hermes-owner-loop.yml` (dựng brief từ
  Status/TODO/Roadmap/OUTBOX/PR → gọi `hermes -z` qua OpenRouter, toolset `safe` → ghi nhánh
  `hermes-owner/state` + mở PR). Tự động khi `HERMES_OWNER_AUTO=on`, bấm tay luôn được.
  **Khác biệt cốt lõi:** gợi ý KHÔNG bắt buộc; thiếu/gợi ý hỏng/workflow lỗi KHÔNG chặn phiên.
  Test: `scripts/tests/test_hermes*.py`; CI riêng: `hermes-owner-protocol-ci.yml` (không gọi
  LLM). Đặc tả: `docs/HERMES_OWNER_PROTOCOL.md`; RCA: `docs/HERMES_SESSION_ERROR_RCA.md`.
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
