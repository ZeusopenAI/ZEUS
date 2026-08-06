# Deployment — Quang Quý AI

Cập nhật: 2026-08-06

## 1. Android/Termux runtime

### Đường dẫn chuẩn

```text
Repository:  ~/quangquy-ai
Hermes:      ~/quangquy-ai/agents/hermes
Virtualenv:  ~/hermes-env
Boot script: ~/.termux/boot/01-hermes
Supervisor:  ~/bin/start-hermes-background.sh
Session:     hermes
Boot log:    ~/.hermes/logs/hermes-boot.log
Runtime log: ~/.hermes/logs/hermes-background.log
```

### Cài đặt Android bắt buộc

1. Cài Termux:Boot từ cùng nguồn với ứng dụng Termux.
2. Mở Termux:Boot ít nhất một lần.
3. Cho phép chạy nền/auto-start nếu ROM yêu cầu.
4. Tắt battery optimization cho Termux và Termux:Boot.
5. Reboot thiết bị.

Không thể hoàn tất các bước UI Android bằng shell không có quyền cài package. Tại thời điểm audit, package `com.termux.boot` chưa được cài.

### Kiểm tra sau reboot

```bash
pm list packages com.termux.boot
tmux has-session -t hermes
tmux list-panes -t hermes -F 'pid=#{pane_pid} cmd=#{pane_current_command} dead=#{pane_dead}'
python -m hermes_cli.main --version
tail -n 20 ~/.hermes/logs/hermes-boot.log
tail -n 50 ~/.hermes/logs/hermes-background.log
```

Dấu hiệu đạt:

- `package:com.termux.boot` xuất hiện.
- Boot log có `boot_id` mới và dòng supervisor thành công.
- tmux session `hermes` tồn tại đúng một lần.
- Process con sử dụng `~/hermes-env/bin/python -m hermes_cli.main`.

### Vận hành

```bash
# Xem giao diện
 tmux attach -t hermes

# Rời tmux mà không dừng Hermes
# Nhấn Ctrl-b, sau đó d

# Xem trạng thái
 tmux ls

# Khởi động idempotent
 ~/bin/start-hermes-background.sh
```

## 2. VPS production target

Termux không phải nền tảng production HA. VPS nên có:

- Ubuntu LTS, user riêng không phải root.
- Python/venv được pin và cài từ revision đã review.
- Service manager với restart policy và startup dependency mạng.
- Firewall deny-by-default; chỉ mở ingress cần thiết.
- Log rotation, disk alert, uptime/health check.
- Secrets được inject khi chạy, không chép vào repository hoặc image.
- Backup encrypted và restore test.

## 3. Release flow

```text
feature branch → pull request → secret scan + tests + build
→ staging → approval → production → health check → rollback nếu lỗi
```

Runtime nằm tại history-preserving subtree `agents/hermes/` trong repository Quang Quy AI duy nhất. Mỗi lần nâng Hermes phải chạy `scripts/update-hermes-subtree.sh` trên nhánh riêng, review source diff, chạy full tests/build ở CI và staging; không update trực tiếp trên production hoặc `main`.

## 4. Rollback

- Code: deploy lại revision đã biết tốt.
- Config: giữ backup mã hóa trước mỗi thay đổi.
- Database/session: backup theo version và kiểm thử restore.
- Credential incident: revoke/rotate trước, sau đó rollback code; xóa khỏi Git không làm credential cũ an toàn trở lại.
