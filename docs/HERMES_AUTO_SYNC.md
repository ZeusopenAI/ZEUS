# Hermes tự cập nhật từ repo (auto-sync)

Mục tiêu: **sửa skill/tài liệu trong repo một lần → Hermes ở mọi nơi (Codespace, VPS)
tự nhận bản mới nhất**, không phải copy tay từng file.

Nguyên tắc: repo là **nguồn sự thật duy nhất**. `~/.hermes` chỉ là bản sao đã đồng bộ,
nên có thể xoá và dựng lại bất cứ lúc nào.

---

## 1. Đồng bộ cái gì?

`scripts/hermes-sync.sh` làm 3 việc:

| Việc | Nguồn | Đích |
|---|---|---|
| Copy skill | `skills/*/` | `$HERMES_HOME/skills/<tên>/` |
| Sinh skill ngữ cảnh | `Status.md`, `TODO.md`, `Roadmap.md`, `AGENTS.md`, `docs/`, git HEAD | `$HERMES_HOME/skills/zeus-context/SKILL.md` |
| Trỏ Hermes tới snapshot (tuỳ chọn `--with-memory`) | — | 1 dòng trong `$HERMES_HOME/MEMORY.md` |

Đặc tính quan trọng:

- **Idempotent**: chạy lại không đổi gì thì không ghi, không restart.
- **Có backup**: skill bị ghi đè/xoá được giữ ở `$HERMES_HOME/skill-backups/<timestamp>/`.
- **Không đụng memory của bạn**: chỉ thay đúng dòng có nhãn `ZEUS context snapshot (auto)`;
  các entry khác trong `MEMORY.md` giữ nguyên.
- **Mã thoát**: `0` = không đổi, `10` = đã cập nhật (caller nên restart gateway), `>10` = lỗi.

---

## 2. Ba cách chạy

### A. Codespace (mở là có, tự cập nhật mỗi lần mở)

Đã cấu hình sẵn trong `.devcontainer/`:

- `postCreateCommand` → cài Hermes từ `agents/hermes` vào `~/.hermes/venv`
- `postStartCommand` → **mỗi lần mở Codespace** chạy lại sync

Dùng:

1. Trên GitHub: **Code → Codespaces → Create codespace on main**
2. Thêm key một lần: **Settings → Codespaces → Secrets** → `OPENROUTER_API_KEY`
   (hoặc điền tay `~/.hermes/.env`)
3. Trong terminal Codespace:

```bash
hermes --version
hermes            # mở TUI
/skills           # thấy edit-anh, zeus-context, qai-developer-manager…
/edit-anh         # menu 10 hiệu ứng ảnh
```

Muốn kéo bản mới ngay mà không cần mở lại Codespace:

```bash
bash .devcontainer/setup-hermes.sh --sync-only
```

### B. VPS 24/7 (timer 15 phút)

```bash
# 1. Cài lần đầu (đã có sẵn từ trước)
sudo bash deploy/vps/install-hermes-vps.sh

# 2. Bật timer tự cập nhật
sudo cp deploy/vps/hermes-repo-sync.service deploy/vps/hermes-repo-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-repo-sync.timer

# 3. Kiểm tra
systemctl list-timers hermes-repo-sync.timer
journalctl -u hermes-repo-sync.service -n 30 --no-pager

# 4. Chạy tay ngay
sudo -u hermes bash /opt/zeus/deploy/vps/hermes-repo-sync.sh
```

Timer: lần đầu sau boot 3 phút, sau đó **mỗi 15 phút**, chạy bù nếu bỏ lỡ mốc.
Khi có thay đổi, script tự `hermes gateway restart` để nạp skill mới.

### C. Trong phiên Arena (khi đang sửa repo)

```bash
bash scripts/hermes-sync.sh --dry-run     # xem sẽ làm gì
bash scripts/hermes-sync.sh               # áp dụng
bash scripts/hermes-sync.sh --with-memory # kèm 1 dòng trỏ trong MEMORY.md
```

---

## 3. GitHub Actions làm gì?

`.github/workflows/hermes-skill-sync.yml` chạy khi `main` đổi `skills/**`, `docs/**`,
`Status.md`, `TODO.md`, `Roadmap.md`, `AGENTS.md`:

1. **Validate** toàn bộ `SKILL.md` (`scripts/validate-skills.py --strict`)
   — chặn skill thiếu `name`, `description` quá 1024 ký tự, trùng tên, link hỏng.
2. **Chạy thử sync** vào thư mục tạm để chắc script không vỡ.
3. **Upload artifact** `hermes-skills-<sha>` — tải về cài tay khi cần.
4. **Gọi webhook VPS** nếu đã đặt secret `HERMES_SYNC_WEBHOOK`
   (không có secret thì bỏ qua — VPS vẫn tự cập nhật theo timer).

Không job nào gọi LLM → **không tốn credit OpenRouter**.

---

## 4. Kiểm tra sau khi sync

```bash
# Hermes nhìn thấy gì?
python3 - <<'PY'
import os, sys, json
sys.path.insert(0, "/opt/zeus/agents/hermes")
from tools.skills_tool import skills_list
print(json.dumps(json.loads(skills_list()), ensure_ascii=False, indent=2))
PY

# So bản trên đĩa với repo
diff -r /opt/zeus/skills ~/.hermes/skills | head

# Xem snapshot ngữ cảnh Hermes đang có
head -30 ~/.hermes/skills/zeus-context/SKILL.md
```

---

## 5. Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| `/skills` không thấy skill mới | Gateway chưa restart | `hermes gateway restart` |
| `hermes-sync.sh` trả `2` | Tham số sai | Chỉ dùng: `--dry-run --skills-only --context-only --with-memory --prune` |
| `prompts.md` báo thiếu | Copy thiếu file phụ | `--prune` rồi sync lại; kiểm `skill-backups/` |
| Timer chạy nhưng không cập nhật | `git` trong `/opt/zeus` bị sửa tay | `sudo -u hermes bash deploy/vps/hermes-repo-sync.sh` xem log; script dùng `reset --hard` nên sẽ ghi đè sửa tay |
| Gateway chết sau restart | Cấu hình/key hỏng | `journalctl -u hermes-gateway -n 100`; rollback skill từ `skill-backups/` |
| Muốn quay lại bản cũ | — | `cp -a ~/.hermes/skill-backups/<ts>/<skill> ~/.hermes/skills/` + restart |

---

## 6. Bảo mật

- Sync **không bao giờ** đọc/ghi `.env`; secret chỉ do bạn điền (`chmod 600`).
- Không copy `.git`, `node_modules`, `__pycache__` — chỉ nội dung skill.
- Webhook (nếu dùng) là **tín hiệu**, không phải đường điều khiển: nó không nhận
  prompt hay lệnh shell, chỉ kích hoạt đúng script sync có sẵn.
- Trên VPS, unit `hermes-repo-sync.service` chạy `User=hermes`, `ProtectSystem=full`,
  `ProtectHome=read-only`, chỉ ghi trong `/opt/zeus` và `/home/hermes/.hermes`.

---

## 7. File liên quan

| File | Vai trò |
|---|---|
| `scripts/hermes-sync.sh` | Đồng bộ skill + sinh `zeus-context` |
| `scripts/validate-skills.py` | Kiểm frontmatter skill (không cần PyYAML) |
| `.devcontainer/devcontainer.json` | Codespace tự cài + tự sync |
| `.devcontainer/setup-hermes.sh` | Cài Hermes + nạp secret + sync |
| `deploy/vps/hermes-repo-sync.sh` | Kéo repo + sync + restart gateway |
| `deploy/vps/hermes-repo-sync.{service,timer}` | systemd chạy mỗi 15 phút |
| `.github/workflows/hermes-skill-sync.yml` | CI validate + báo VPS |
