# TODO — Quang Quý AI

Cập nhật: 2026-08-06

## P0 — phải hoàn tất trước khi gọi là chạy nền 24/7

- [x] Xác minh `hermes_cli` được cài editable trong `~/hermes-env`.
- [x] Xác minh `python -m hermes_cli.main` và console script `hermes` chạy ngoài repository mà không cần `PYTHONPATH`.
- [x] Chuẩn hóa tmux supervisor `~/bin/start-hermes-background.sh` với restart delay 15 giây.
- [x] Chuẩn hóa `~/.termux/boot/01-hermes`, wake lock và delay 30 giây.
- [x] Loại boot script trùng khỏi thư mục được Termux:Boot thực thi.
- [x] Kiểm thử cold-start: xóa session rồi tạo lại thành công bằng boot script.
- [ ] Cài ứng dụng Android Termux:Boot từ cùng nguồn với Termux, mở ứng dụng một lần và bỏ tối ưu pin cho Termux/Termux:Boot.
- [ ] Reboot Android thật; kiểm tra `~/.hermes/logs/hermes-boot.log`, tmux session `hermes` và process `python -m hermes_cli.main`.
- [ ] Xử lý 12 cảnh báo `npm audit` (1 critical, 10 high, 1 low) trên nhánh riêng; chạy build/test trước khi merge.
- [ ] Chạy test suite Hermes trong Linux CI/VPS; test harness subprocess hiện gặp `PermissionError` trên Android/Termux.
- [ ] Nâng root CI để chạy full Hermes pytest, lint/typecheck, UI build, lockfile check và OSV scan; workflow lồng trong `agents/hermes/.github/` không tự chạy.

## P1 — tích hợp vận hành

- [ ] Đăng nhập `gh auth login`; bật branch protection và required CI trên `main`.
- [ ] Tạo backup tag và migration branch; thay snapshot Hermes bằng submodule/version pin (hoặc subtree không squash nếu bắt buộc monorepo).
- [ ] Đồng bộ technical fork với `NousResearch/hermes-agent` theo batch có review/test; dọn branch refs sau khi xác minh không còn active work.
- [ ] Tạo đúng bộ icon 32/128/256 cho Tauri installer và thêm/check `Cargo.lock` theo policy build application.
- [ ] Tạo Telegram bot, lưu token ngoài Git, cấu hình Hermes Gateway và kiểm thử hai chiều.
- [ ] Cấu hình Claude/Anthropic và Gemini dưới dạng model provider/fallback; không đưa key vào `config.yaml`.
- [ ] Cấu hình Notion integration, chỉ share các page cần thiết.
- [ ] Cấu hình Google Workspace OAuth cho Drive/Docs với scope tối thiểu.
- [ ] Kết nối Make bằng webhook có chữ ký hoặc token riêng, giới hạn từng scenario.
- [ ] Cấu hình Hugging Face token loại read-only; chỉ cấp write khi có workflow xuất bản model cụ thể.
- [ ] Thiết lập health check, cảnh báo lỗi và backup có kiểm thử khôi phục.

## P2 — production

- [ ] Chuyển tiến trình 24/7 sang VPS Ubuntu; giữ Android/Termux làm control plane dự phòng.
- [ ] Chạy Hermes Gateway dưới service manager, auto-restart và log rotation.
- [ ] Thêm staging trước production; deploy qua pull request và approval.
- [ ] Chọn secret manager cho production; lập lịch rotation và quy trình thu hồi.
- [ ] Theo dõi chi phí model/API, giới hạn ngân sách và rate limit.

## Quy tắc hoàn thành

Một mục chỉ được đánh dấu xong khi có lệnh kiểm tra, log hoặc CI run chứng minh. Không commit credential, không deploy thẳng từ `main`, không tự động hóa hành động phát sinh chi phí hoặc công khai dữ liệu nếu chưa có approval.
