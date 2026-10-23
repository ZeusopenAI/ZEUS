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
| Sinh skill ngữ cảnh | `Status.md`, `TODO.md`, `Roadmap.md`, `AGENTS.md`, `docs/`, bản đồ repo, git HEAD | `$HERMES_HOME/skills/zeus-context/SKILL.md` |
| Trỏ Hermes tới snapshot (tuỳ chọn `--with-memory`) | — | 1 dòng trong `$HERMES_HOME/MEMORY.md` |

Phần nội dung của `zeus-context` do `scripts/gen-zeus-context.py` sinh, với các đặc tính:

- **Tất định**: cùng một commit → cùng một file. Không chèn timestamp, nên sync
  không tạo "thay đổi giả" và không restart gateway vô ích.
- **Không cắt cụt giữa chừng**: mỗi mục có ngân sách ký tự riêng, ưu tiên
  Status → TODO → AGENTS (quy tắc an toàn) → Roadmap; cắt ở ranh giới dòng và
  ghi rõ "đọc đầy đủ tại `<đường dẫn>`".
- **Cắt UTF-8 an toàn**: tiếng Việt không bị hỏng ký tự.
- **Có bản đồ repo + danh sách docs**: Hermes biết đọc file nào khi cần chi tiết.

Đặc tính chung của `hermes-sync.sh`:

- **Idempotent**: không đổi thì không ghi, không restart.
- **Có backup**: skill bị ghi đè/xoá được giữ ở `$HERMES_HOME/skill-backups/<timestamp>/`.
- **Không đụng memory của bạn**: chỉ thay đúng dòng có nhãn `ZEUS context snapshot (auto)`.
- **Mã thoát**: `0` = không đổi, `10` = đã cập nhật (caller nên restart gateway), `>10` = lỗi.

---

## 2. Kiểm tra bằng một lệnh

```bash
bash scripts/hermes-doctor.sh
```

Báo cáo gồm 6 nhóm: runtime, skill có khớp repo, `zeus-context` có đúng commit,
gateway có active, auto-sync timer có bật, và `.env` có model key (chỉ kiểm **tên**
biến, không in giá trị).

```
== Ngữ cảnh (zeus-context) ==
  ✗ snapshot ở commit 4aba149, repo ở 82b4c88 — Hermes đang đọc thông tin cũ
```

Mã thoát: `0` khỏe, `1` có drift, `2` chưa cài Hermes. Dùng `--quiet` khi cần
chỉ xem vấn đề (hợp với cron/monitoring).

---

## 3. Bốn cách chạy

### A. Codespace — mở là có, tự cập nhật mỗi lần mở

Đã cấu hình sẵn trong `.devcontainer/`:

- `postCreateCommand` → cài Hermes từ `agents/hermes` vào `~/.hermes/venv`
- `postStartCommand` → **mỗi lần mở Codespace** chạy lại sync

```bash
hermes --version
hermes            # TUI
/skills           # thấy edit-anh, zeus-context, qai-developer-manager…
/edit-anh         # menu 10 hiệu ứng ảnh
```

Kéo bản mới ngay mà không cần mở lại Codespace:

```bash
bash .devcontainer/setup-hermes.sh --sync-only
```

### B. VPS 24/7 — timer 15 phút

```bash
sudo bash deploy/vps/install-hermes-vps.sh          # cài lần đầu (nếu chưa)
sudo cp deploy/vps/hermes-repo-sync.service deploy/vps/hermes-repo-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-repo-sync.timer

systemctl list-timers hermes-repo-sync.timer        # kiểm
journalctl -u hermes-repo-sync.service -n 30 --no-pager
sudo /opt/zeus/deploy/vps/hermes-repo-sync.sh       # chạy tay ngay
```

Timer: lần đầu sau boot 3 phút, sau đó mỗi 15 phút, chạy bù nếu bỏ lỡ mốc.
Có thay đổi → tự `systemctl restart hermes-gateway` rồi kiểm `is-active`.

Unit chạy **root** (để restart được service) nhưng phần ghi file được hạ quyền
xuống user `hermes` bằng `runuser`, nên quyền sở hữu skill luôn đúng.

### C. Cập nhật NGAY khi push (GitHub Actions → VPS)

Workflow `.github/workflows/hermes-skill-sync.yml` chạy khi `main` đổi skill/docs.
Job `remote-sync` cập nhật VPS theo thứ tự ưu tiên:

1. **SSH** (chính xác nhất) — cần 4 secret:
   | Secret | Ví dụ |
   |---|---|
   | `VPS_HOST` | `203.0.113.10` |
   | `VPS_USER` | `hermes` |
   | `VPS_SSH_KEY` | private key (dán nguyên văn, gồm cả dòng BEGIN/END) |
   | `VPS_PORT` | `22` (bỏ trống = 22) |

2. **Webhook** (`HERMES_SYNC_WEBHOOK` + tuỳ chọn `HERMES_SYNC_TOKEN`) — nếu VPS
   có endpoint nhận tín hiệu.
3. Không có gì → chỉ ghi notice; VPS vẫn tự cập nhật theo timer.

Để SSH chạy được, trên VPS cần cho user `hermes` quyền chạy **đúng một script**:

```bash
sudo install -m 0440 -o root -g root deploy/vps/zeus-hermes-sync.sudoers \
     /etc/sudoers.d/zeus-hermes-sync
sudo visudo -c
sudo -u hermes sudo -n /opt/zeus/deploy/vps/hermes-repo-sync.sh --dry-run   # phải chạy được
```

Public key tương ứng thêm vào `~hermes/.ssh/authorized_keys`.

### D. Trong phiên Arena (khi đang sửa repo)

```bash
bash scripts/hermes-sync.sh --dry-run     # xem sẽ làm gì
bash scripts/hermes-sync.sh               # áp dụng
bash scripts/hermes-sync.sh --with-memory # kèm 1 dòng trỏ trong MEMORY.md
bash scripts/hermes-doctor.sh             # kiểm tra sau khi sync
```

---

## 4. Chốt an toàn trên VPS

`hermes-repo-sync.sh` dùng `git reset --hard`, nên trước khi chạy nó **từ chối**
làm việc nếu bản checkout không sạch:

| Tình huống | Hành vi |
|---|---|
| Đang ở nhánh khác `REPO_BRANCH` | Dừng, `exit 3`, in cách xử lý |
| Có thay đổi chưa commit (không tính file untracked) | Dừng, `exit 3`, liệt kê file |
| Muốn bỏ qua (chủ ý) | `--force` |

Điều này tránh việc chạy nhầm trên máy đang có người sửa code làm mất thay đổi.

---

## 5. GitHub Actions kiểm gì?

Job `validate`:

1. `python3 scripts/validate-skills.py --strict` — chặn skill thiếu `name`,
   `description` > 1024 ký tự, trùng tên, link nội bộ hỏng.
2. Chạy sync thật vào thư mục tạm.
3. **Chạy sync lần 2** — nếu vẫn báo "có thay đổi" thì fail (bắt lỗi sinh file
   ngẫu nhiên, làm gateway restart vô ích mỗi lần).
4. Upload artifact `hermes-skills-<sha>` để tải về cài tay.

Không job nào gọi LLM → **không tốn credit OpenRouter**.

---

## 6. Kiểm tra sau khi sync

```bash
# Hermes nhìn thấy gì?
python3 - <<'PY'
import sys, json
sys.path.insert(0, "/opt/zeus/agents/hermes")
from tools.skills_tool import skills_list
print(json.dumps(json.loads(skills_list()), ensure_ascii=False, indent=2))
PY

# So bản trên đĩa với repo
diff -r /opt/zeus/skills ~/.hermes/skills | head

# Tổng kiểm
bash scripts/hermes-doctor.sh
```

---

## 7. Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| `/skills` không thấy skill mới | Gateway chưa restart | `hermes gateway restart` |
| Doctor báo "snapshot ở commit cũ" | Chưa sync sau khi pull | `bash scripts/hermes-sync.sh --with-memory` |
| `hermes-sync.sh` trả `2` | Tham số sai | Chỉ dùng: `--dry-run --skills-only --context-only --with-memory --prune` |
| `hermes-repo-sync.sh` trả `3` | Nhánh sai / có thay đổi chưa commit | Commit/stash, hoặc `--force` nếu chủ ý |
| Timer chạy nhưng không cập nhật | `git` trong `/opt/zeus` bị sửa tay | Script sẽ từ chối (exit 3) — xem log; `--force` để ghi đè |
| Actions SSH fail (255) | Thiếu key/known_hosts/sudoers | Kiểm `VPS_SSH_KEY`, `sudo -n ... --dry-run` trên VPS |
| Gateway chết sau restart | Key/cấu hình hỏng | `journalctl -u hermes-gateway -n 100`; rollback skill từ `skill-backups/` |
| Muốn quay lại bản cũ | — | `cp -a ~/.hermes/skill-backups/<ts>/<skill> ~/.hermes/skills/` + restart |

---

## 8. Bảo mật

- Sync **không bao giờ** đọc/ghi `.env`; secret chỉ do bạn điền (`chmod 600`).
- Không copy `.git`, `node_modules`, `__pycache__` — chỉ nội dung skill.
- Escalation tối thiểu: sudoers chỉ cho đúng 1 script, không cho shell.
- Unit VPS: `ProtectSystem=full`, `ProtectHome=read-only`, chỉ ghi trong
  `/opt/zeus` và `/home/hermes/.hermes`.
- Webhook (nếu dùng) là **tín hiệu**, không phải đường điều khiển: không nhận
  prompt, không nhận lệnh shell.

---

## 9. File liên quan

| File | Vai trò |
|---|---|
| `scripts/hermes-sync.sh` | Đồng bộ skill + gọi sinh `zeus-context` |
| `scripts/gen-zeus-context.py` | Sinh nội dung snapshot ngữ cảnh (tất định, có ngân sách) |
| `scripts/hermes-doctor.sh` | Kiểm tra drift: skill, snapshot, gateway, timer, key |
| `scripts/validate-skills.py` | Kiểm frontmatter skill (không cần PyYAML) |
| `.devcontainer/devcontainer.json` | Codespace tự cài + tự sync |
| `.devcontainer/setup-hermes.sh` | Cài Hermes + nạp secret + sync |
| `deploy/vps/hermes-repo-sync.sh` | Kéo repo + sync + restart gateway (có chốt an toàn) |
| `deploy/vps/hermes-repo-sync.{service,timer}` | systemd chạy mỗi 15 phút |
| `deploy/vps/zeus-hermes-sync.sudoers` | Cho phép SSH từ Actions chạy đúng 1 script |
| `.github/workflows/hermes-skill-sync.yml` | CI validate + cập nhật VPS ngay khi push |
