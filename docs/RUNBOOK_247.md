# Runbook 24/7 — Hermes Gateway luôn trực

Cập nhật: 2026-10-14. Mục tiêu: Hermes nhận yêu cầu qua Telegram **mọi lúc**, không
phụ thuộc điện thoại hay một máy tính đang mở.

Hai con đường (không loại trừ nhau, chạy song song được):

| Con đường | Vai trò | Trạng thái |
| --- | --- | --- |
| **A. VPS Ubuntu** | production 24/7 thật | Bộ cài sẵn trong repo, chỉ còn bước mua VPS + điền token |
| **B. Termux/Android** | dự phòng + development (đang chạy) | Còn thiếu duy nhất: cài Termux:Boot + reboot thật |

Nguyên tắc xuyên suốt (xem `docs/TELEGRAM_WIRING.md`): **một bot token chỉ có MỘT
consumer**. Đã chốt phương án A — Hermes là bộ não (polling), Cloudflare Worker
`worker/telegram-proxy/` chỉ là proxy mỏng nếu cần URL công khai. Không bao giờ
chạy 2 tiến trình cùng `getUpdates` một token (lỗi 409 "lúc được lúc không").

---

## Con đường A — VPS Ubuntu (production)

### A1. Chuẩn bị (một lần)

1. Mua VPS Ubuntu 22.04/24.04 (cấu hình tối thiểu 1 vCPU / 1 GB RAM / 10 GB disk).
2. Trỏ DNS hoặc dùng IP trực tiếp; mở SSH (22). **Không cần mở cổng nào khác** —
   gateway dùng polling (chiều đi ra), không cần inbound web.
3. Tạo bot Telegram riêng cho production từ @BotFather nếu bot hiện tại đang gắn
   với Termux/Cloudflare (tránh hai consumer cùng token).

### A2. Cài tự động

```bash
ssh root@<IP_VPS>
git clone https://github.com/ZeusopenAI/ZEUS.git /opt/zeus && cd /opt/zeus
sudo bash deploy/vps/install-hermes-vps.sh            # thêm --dry-run để xem trước
```

Script làm gì: cài gói hệ thống → tạo user `hermes` (nologin) → clone/updates ZEUS
tại `/opt/zeus` → virtualenv `/opt/zeus/hermes-env` → `pip install agents/hermes` →
tạo `/home/hermes/.hermes` (700) + `.env` (600, chỉ khung tên biến) → chạy
`hermes gateway install --system --start-now` (hermes tự sinh systemd unit, enable
boot-start, restart tự động khi crash).

Chạy lại script bất cứ lúc nào để cập nhật mã nguồn (idempotent, không đè `.env`).

### A3. Điền secret (thủ công — không script hoá, không commit)

```bash
sudo nano /home/hermes/.hermes/.env
```

| Biến | Bắt buộc | Ghi chú |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | ✅ | Token BotFather của bot production |
| `TELEGRAM_ALLOWED_USERS` | ✅ | User ID số được phép dùng bot (phòng bot lạ) |
| `OPENROUTER_API_KEY` hoặc `GEMINI_API_KEY` | ✅ (một trong các model key) | Key model; lấy từ provider, không lưu nơi khác |

Sau đó: `sudo systemctl restart hermes-gateway`

### A4. Kiểm chứng "đã 24/7" — gate trước khi gọi là xong

```bash
sudo bash /opt/zeus/deploy/vps/healthcheck.sh     # kỳ vọng: HEALTHY (exit 0)
```

Gate hoàn thành = cả 4 mốc đều có bằng chứng lưu lại:

1. `healthcheck.sh` ra **HEALTHY**.
2. **Round-trip Telegram**: nhắn tin cho bot → bot trả lời trong 1 phút.
3. **Reboot drill**: `sudo reboot` → đăng nhập lại → healthcheck vẫn HEALTHY
   **không cần can thiệp tay** (chứng minh systemd đã enable boot-start).
4. **Crash drill**: `sudo systemctl kill --signal=KILL hermes-gateway` → trong
   vài giây systemd tự kéo service lên lại (`systemctl status` ra `active (running)`
   với số restart tăng) — chứng minh auto-restart.

Bốn mốc này ánh xạ 1-1 tiêu chí gate của Roadmap Giai đoạn 3 (staging soak, rollback
diễn tập, health check cho kênh quan trọng).

### A5. Backup + khôi phục

```bash
# backup hàng ngày 03:00, giữ 7 bản (crontab -e của user hermes)
0 3 * * * /opt/zeus/deploy/vps/backup-hermes.sh >> /home/hermes/.hermes/backup.log 2>&1
```

- Nên đặt `HERMES_BACKUP_AGE_PUBKEY` để bản backup được **mã hoá age**.
- **Bắt buộc** copy bản backup ra ngoài VPS (rclone lên Drive/S3/scp về máy khác).
  Backup nằm cùng máy VPS không tính là backup.
- Khôi phục: dừng service → giải nén bản backup đè lên `.hermes` mới (giữ owner
  `hermes:hermes`, mode 700/600) → start service → healthcheck → round-trip test.
  Diễn tập khôi phục ít nhất 1 lần trước khi tin vào backup.

### A6. Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Xử lý |
| --- | --- | --- |
| Bot "lúc được lúc không" | 2 tiến trình cùng getUpdates một token (VD: còn Termux đang chạy song song) | Tắt consumer còn lại; xem `docs/TELEGRAM_WIRING.md` mục 409 |
| Service `active` nhưng bot im | `TELEGRAM_BOT_TOKEN` sai/rỗng, hoặc bị Telegram ban | `journalctl -u hermes-gateway -n 100`; kiểm tra `.env` |
| `hermes doctor` báo advisory | Cảnh báo bảo mật của Hermes | Đọc ID advisory, `hermes doctor --ack <ID>` chỉ khi đã đánh giá |
| Hết RAM (OOM) | VPS 512MB quá nghèo | Nâng lên ≥1 GB hoặc thêm swap 1 GB |

---

## Con đường B — Termux/Android (dự phòng đang chạy)

Nền tảng đã đạt cold-start (xóa session → boot script tự dựng lại — đã xác minh
06/08). Còn **duy nhất** chuỗi hành động vật lý sau trên điện thoại:

1. Cài **Termux:Boot** từ cùng nguồn F-Droid/GitHub với app Termux chính (KHÔNG
   trộn nguồn Play Store và F-Droid).
2. **Mở app Termux:Boot một lần** (Android yêu cầu mở mới cho phép chạy boot script).
3. Tắt tối ưu pin cho cả Termux và Termux:Boot (Settings → Battery → Unrestricted).
4. Đảm bảo `~/.termux/boot/01-hermes` tồn tại (`chmod +x`) với nội dung:

```bash
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
sleep 30
exec ~/bin/start-hermes-background.sh
```

5. **Reboot thật** → sau khi máy lên lại, kiểm tra 3 bằng chứng:
   - `cat ~/.hermes/logs/hermes-boot.log` có timestamp mới sau reboot;
   - `tmux ls` thấy session `hermes`;
   - nhắn Telegram → bot trả lời (round-trip).

Đạt đủ 3 bằng chứng =Gate Giai đoạn 0 đóng chính thức.

---

## checklist secret 24/7 (không phụ thuộc con đường)

- Token/key **chỉ** nằm trong `.env` mode 600 trên máy chạy (VPS/Termux), không
  bao giờ nằm trong Git, Notion, chat, ảnh chụp màn hình.
- Mỗi dịch vụ một key riêng, scope nhỏ nhất (bot production ≠ bot dev).
- Khi rò rỉ: rotate ngay tại provider, xoá `.env` cũ, viết lại `.env` mới.
- `worker/telegram-proxy/` nếu deploy: secret nằm trong Wrangler secrets
  (`wrangler secret put`), không nằm trong `wrangler.toml`.
