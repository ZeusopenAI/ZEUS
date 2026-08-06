# Status — Quang Quý AI

Cập nhật: 2026-08-06 10:44 +07

## Tổng quan

Trạng thái: development runtime hoạt động; chưa production-ready.

## Đã xác minh

- `hermes-agent 0.18.0` được cài editable từ `agents/hermes` vào `~/hermes-env`.
- Python 3.13.13; `pip check` báo không có dependency bị hỏng.
- `python -m hermes_cli.main --version` và `hermes --version` chạy thành công ngoài repository.
- Hermes chạy trong tmux bằng đúng virtualenv, model `gpt-5.6-sol`, provider `openai-codex`.
- Boot script và supervisor hợp lệ; duplicate boot script đã được đưa ra khỏi thư mục chạy.
- Cold-start thực tế thành công: session bị xóa, boot script tạo lại session và Hermes vào prompt.
- Python `compileall` thành công; có một `SyntaxWarning` trong test string tại `agents/hermes/tests/agent/test_credits_tracker.py:625`.
- Source marker Hermes khớp HEAD remote `qquy28888-ops/hermes-agent/main`: `5e51b123f32b7f6a51fbd5759e89ba5146ce4003`.
- High-confidence credential scan trên production paths hiện tại: 0 finding.
- `.hermes/auth.json` và `config.yaml` có mode 600; `~/.hermes` có mode 700.

## Blocker

- Android package `com.termux.boot` chưa được cài; chưa thể chứng minh tự chạy sau reboot thật.
- `npm audit`: 12 vulnerabilities — 1 critical, 10 high, 1 low.
- Hermes test wrapper gặp `PermissionError` khi tạo subprocess test trên Android/Termux; cần CI Linux/VPS để xác nhận suite.
- GitHub CLI chưa đăng nhập; chưa kiểm tra/cấu hình branch protection và repository secrets qua authenticated API.
- Telegram, Claude, Gemini, Notion, Drive, Make và Hugging Face chưa được E2E test trong phiên audit này.
- Root CI chưa chạy full Hermes pytest, lint/typecheck, UI build hoặc OSV scan; workflow nằm trong `agents/hermes/.github/` không tự chạy ở repository cha.
- Fork `qquy28888-ops/hermes-agent` chậm hơn canonical upstream 6.045 commit tại thời điểm audit.

## Repository

- Canonical: `qquy28888-ops/quangquy-ai`, branch `main`, local khớp `origin/main` trước các thay đổi audit.
- Source history: `qquy28888-ops/hermes-agent`, branch `main`; canonical upstream của Hermes là `NousResearch/hermes-agent`.
- Strategy: một repository Quang Quy AI duy nhất; Hermes là subtree không squash tại `agents/hermes/`, với source SHA được ghi trong marker.
- Migration branch đã bảo toàn ancestry Hermes và thay updater snapshot bằng subtree updater; đang chờ push/PR.

## Mức sẵn sàng

| Khu vực | Trạng thái |
|---|---|
| Hermes CLI/TUI | Đạt cho development |
| tmux supervisor | Đạt cold-start |
| Android reboot | Blocked: thiếu Termux:Boot |
| Python dependencies | Đạt `pip check` |
| Python syntax | Đạt, 1 warning test |
| Node security | Không đạt: critical/high advisories |
| Secrets trong source hiện tại | Không thấy high-confidence finding |
| CI production | Chưa đủ full test/build |
| VPS deployment | Chưa triển khai |
