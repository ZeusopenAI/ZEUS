# Deployment — Zeus / Quang Quý AI

Cập nhật: 2026-09-17

## 1. Các phương thức chạy & Triển khai

Zeus hỗ trợ nhiều hình thức chạy linh hoạt tùy theo nhu cầu và thiết bị:

### A. Chạy tác vụ nhanh qua GitHub Actions (Khuyến nghị cho tác vụ lẻ)
- Không cần máy tính cá nhân bật 24/7.
- Chỉ cần điện thoại: vào GitHub Actions → **Hermes task runner (OpenRouter)** → Bấm **Run workflow**.
- Tự động chạy tạo ảnh, viết code, xuất file về Artifacts hoặc mở PR.

### B. Chạy trên Termux / Android
```text
Repository:  ~/ZEUS
Hermes:      ~/ZEUS/agents/hermes
Virtualenv:  ~/hermes-env
Boot script: ~/.termux/boot/01-hermes
Supervisor:  ~/bin/start-hermes-background.sh
Session:     hermes
```

Vận hành cơ bản trên Termux:
```bash
# Xem giao diện Hermes
tmux attach -t hermes

# Rời tmux mà không dừng Hermes (nhấn Ctrl-b rồi nhấn d)

# Khởi động supervisor nền
~/bin/start-hermes-background.sh
```

### C. Chạy Telegram Webhook Proxy trên Cloudflare
```bash
cd worker/telegram-proxy
npx wrangler secret put WEBHOOK_SECRET
npx wrangler secret put UPSTREAM_URL
npx wrangler deploy
```

### D. Chạy GPU trên Google Colab
Mở Google Colab và thực thi:
```python
!curl -s https://raw.githubusercontent.com/ZeusopenAI/ZEUS/main/colab/bootstrap.py | python3
```

### E. Chạy FlowKit AI Filmmaker (`flowkit/`)
FlowKit chạy độc lập với Hermes. Cần Python 3.10+, FFmpeg/ffprobe, Chrome và một Google Flow tab đã đăng nhập:

```bash
cd flowkit
./setup.sh
export FLOW_PROJECT_ID="<UUID dự án đã tạo trong Google Flow>"
source venv/bin/activate
python -m agent.main
```

Nạp `flowkit/extension/` bằng Chrome Developer mode → **Load unpacked**, giữ tab Google Flow mở, rồi kiểm tra `http://127.0.0.1:8100/health`. Có thể chạy dashboard riêng bằng `cd flowkit/dashboard && npm ci && npm run dev`. Xem [docs/FLOWKIT_INTEGRATION.md](docs/FLOWKIT_INTEGRATION.md) trước khi cấu hình. Không đưa API key hoặc cookie vào repository.

## 2. Quy trình Cập nhật & Đồng bộ Mã Nguồn

```text
nhánh làm việc (arena/...) → test & xác minh → đồng bộ sang ZeusopenAI/ZEUS:main
```

- Sử dụng script `scripts/sync-to-zeusopenai.sh` để đẩy cập nhật lên repo chính `ZeusopenAI/ZEUS`.
- Kiểm tra toàn bộ secret trước khi đẩy: không bao giờ lưu API key trong mã nguồn hoặc commit.

## 3. Rollback & Khôi phục sự cố

- **Mã nguồn:** Checkout lại commit hoặc tag an toàn trước đó.
- **Biến môi trường:** Giữ file backup `~/.hermes/.env` phân quyền mode 600.
- **Sự cố rò rỉ Credential:** Thu hồi (Revoke) ngay tại nhà cung cấp (OpenRouter, Google AI Studio, Telegram BotFather), cập nhật lại secret mới, không chỉ xóa commit trong Git.
