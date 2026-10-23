# Hermes Owner Protocol — Hermes làm chủ, agent làm thợ

> Trạng thái: đang dùng (2026-10-23) · Engine: `scripts/hermes_owner.py` · Chủ: Hermes (OpenRouter qua GitHub Actions)

## 1. Vấn đề cần giải

Operator muốn: **mỗi lần mở chế độ agent trên Arena, Hermes tự động được gọi vào làm chủ**.

Sự thật kỹ thuật phải nói rõ:

- Arena **không** cho cài hook/skill tự chạy khi mở phiên. Không có API nào để "gọi Hermes"
  từ phía Arena.
- Phiên Arena là **ephemeral**: hết phiên là mất, không giữ process. Vì vậy Hermes **không thể**
  chạy thường trực *bên trong* phiên Arena.
- Sandbox Arena **không có** API key provider (đã kiểm chứng: không có `OPENROUTER_API_KEY`,
  không có binary `hermes`, không có `~/.hermes`).

Ba kênh tự động thật sự tồn tại:

| Kênh | Cơ chế | Độ tin cậy |
|---|---|---|
| `AGENTS.md` | Agent đọc khi mở repo; ĐIỀU 0 buộc chạy boot | Cao (mọi agent đều đọc `AGENTS.md`) |
| Script trong repo | `bash scripts/hermes-session-boot.sh` | Tuyệt đối (chạy là chạy) |
| GitHub Actions | Nơi Hermes thật sự thức dậy và ban hành lệnh | Tuyệt đối |

Giao thức này nối ba kênh đó thành một vòng kín, dùng **repo làm hộp thư**.

## 2. Kiến trúc

```text
        ┌──────────────────────── GitHub Actions ────────────────────────┐
        │  hermes-owner-loop.yml                                        │
        │  1. đọc OUTBOX.md + PR + Status/TODO/Roadmap → brief          │
        │  2. hermes -z "<brief>" -m gemini-2.5-flash --provider ...    │
        │  3. tách khối <<<ZEUS_DIRECTIVE>>> …                          │
        │  4. ghi INBOX.md + STATE.json + archive/ (có seal SHA-256)     │
        │  5. push nhánh hermes-owner/state + mở PR về main             │
        └───────────────┬───────────────────────────────▲───────────────┘
                        │ mệnh lệnh                     │ báo cáo
                        ▼                               │
   ┌──────────── Phiên agent Arena / Codespaces ────────┴──────────┐
   │ BƯỚC 0: hermes-session-boot.sh   → đọc & kiểm tra seal, hạn   │
   │         ├─ hợp lệ  → in MỆNH LỆNH, agent làm đúng lệnh        │
   │         └─ không   → DỪNG (exit 3/4/5/6), báo Operator        │
   │ KẾT:    hermes-session-closeout.sh → append OUTBOX.md         │
   └───────────────────────────────────────────────────────────────┘
                        │ commit trên nhánh arena/**
                        ▼
                 arena-auto-pr.yml → PR → merge → main
```

Bốn mảnh ghép:

| Thành phần | Vai trò |
|---|---|
| `.ai/handoff/` | Hộp thư: `INBOX.md`, `OUTBOX.md`, `STATE.json`, `archive/` |
| `scripts/hermes_owner.py` | Engine: `boot`, `issue`, `closeout`, `status`, `extract`, `selftest` |
| `scripts/hermes-session-boot.sh` / `-closeout.sh` | Lối vào một dòng cho agent |
| `.github/workflows/hermes-owner-loop.yml` | Nơi Hermes thức dậy ban hành lệnh |

## 3. Dùng một lần đầu (≈ 3 phút)

1. **Kiểm tra secret** `OPENROUTER_API_KEY` đã có trong
   *Settings → Secrets and variables → Actions* (workflow `hermes-openrouter.yml` đã dùng key này).
2. **Bấm chạy chủ**: Actions → **Hermes owner loop** → *Run workflow*.
   - `operator_note`: việc bạn muốn ưu tiên (có thể để trống)
   - `model`: giữ `google/gemini-2.5-flash` cho rẻ
   - `ttl_hours`: `72` (mệnh lệnh sống 3 ngày)
3. Sau ~2 phút: có PR **🧭 Mệnh lệnh Hermes #1** và nhánh `hermes-owner/state`.
4. Từ đó mọi phiên agent chạy `bash scripts/hermes-session-boot.sh` sẽ nhận đúng lệnh đó.

Muốn **hoàn toàn tự động** (không cần bấm):

- Tạo biến repo `HERMES_OWNER_AUTO = on`
  (*Settings → Secrets and variables → Actions → Variables → New repository variable*).
- Khi đó workflow tự chạy **mỗi 6 giờ** và **mỗi khi `OUTBOX.md` được merge vào `main`**
  (tức là ngay sau khi một phiên agent báo cáo xong).
- Tắt: xoá biến hoặc đổi giá trị khác `on`. Bấm tay vẫn luôn chạy được.

## 4. Vòng đời một phiên

```bash
# 1) BƯỚC 0 — bắt buộc
bash scripts/hermes-session-boot.sh

# 2) làm đúng mệnh lệnh, không mở rộng phạm vi

# 3) kết phiên — bắt buộc
bash scripts/hermes-session-closeout.sh \
  --status DONE \
  --summary "Đã sửa lỗi X; thêm test Y" \
  --tests "python3 -m pytest -q: 12 passed"
```

`closeout` nối báo cáo vào đầu `OUTBOX.md`, cập nhật `STATE.json` (không commit trừ khi
thêm `--commit`). Arena tự lưu file; khi PR được merge, workflow owner loop nhìn thấy báo cáo
và ban hành lệnh kế tiếp.

## 5. Tham chiếu lệnh

### Boot

```bash
bash scripts/hermes-session-boot.sh                 # chuẩn (đọc repo → nhánh trạng thái)
bash scripts/hermes-session-boot.sh --offline       # không dùng mạng
bash scripts/hermes-session-boot.sh --json          # kèm JSON máy đọc
bash scripts/hermes-session-boot.sh --materialize   # ghi bản remote vào working tree
bash scripts/hermes-session-boot.sh --live          # gọi Hermes trực tiếp nếu có binary + key
```

Thứ tự tìm mệnh lệnh: **working tree → `origin/hermes-owner/state` → (tuỳ chọn) gọi Hermes trực tiếp**.

### Issue (workflow dùng; người cũng dùng được để thử)

```bash
python3 scripts/hermes_owner.py issue \
  --body-file /tmp/directive.md \
  --title "Mệnh lệnh #7 — vá lỗi sync" \
  --ttl-hours 72 \
  --model google/gemini-2.5-flash \
  --source-run "https://github.com/…/runs/123"
```

`issue` tính số thứ tự, bọc seal, ghi `INBOX.md` + `archive/INBOX-<id>.md`,
đẩy mệnh lệnh cũ vào `STATE.history`.

### Status

```bash
python3 scripts/hermes_owner.py status           # 0 kể cả khi lệnh hỏng
python3 scripts/hermes_owner.py status --strict  # trả 3/4/5/6 nếu lệnh không dùng được
```

### Closeout

```bash
bash scripts/hermes-session-closeout.sh --status BLOCKED \
  --summary "Không có quyền ghi vào repo X" \
  --blocker "Cần Operator cấp quyền" \
  --questions "Có nên chuyển sang nhánh khác không?"
```

`--status`: `DONE` | `PARTIAL` | `BLOCKED`. Thêm `--commit` để commit thay đổi vào git.

### Extract / selftest

```bash
python3 scripts/hermes_owner.py extract --input raw.txt --output directive.md
python3 scripts/hermes_owner.py selftest
```

## 6. Định dạng dữ liệu

### `INBOX.md`

```markdown
---
protocol: "hermes-owner-v1"
schema: 1
id: "hermes-20261023T0912Z-4f2a"
number: 3
issuer: "hermes"
title: "Mệnh lệnh #3 — vá lỗi boot"
issued_at: "2026-10-23T09:12:00Z"
valid_until: "2026-10-26T09:12:00Z"
seal: "sha256:9f2c…"
model: "google/gemini-2.5-flash"
source_run: "https://github.com/ZeusopenAI/ZEUS/actions/runs/123"
---

# MỆNH LỆNH #3 — …
```

**Seal** = `sha256` của thân mệnh lệnh (phần sau `---` thứ hai, chuẩn hoá: `strip()` + `\n`).
Sửa một ký tự ⇒ seal lệch ⇒ `boot` trả **5** ⇒ phiên dừng. Đây là *chống sửa tay*, không phải
chữ ký mật mã (ai đọc code cũng tính lại được) — mục tiêu là phát hiện chỉnh sửa ngoài luồng.

### `OUTBOX.md`

Mỗi báo cáo là một khối:

```markdown
<!-- report:start -->
## arena-20261023T1402Z-9c1e — DONE

- **Mệnh lệnh:** hermes-20261023T0912Z-4f2a — Mệnh lệnh #3 — vá lỗi boot
- **Thời điểm:** …
- **Nhánh:** arena/3c188fa1-zeus
- **HEAD:** 6bc5e54
- **Tóm tắt:** …
- **Đã kiểm chứng:** …
- **Câu hỏi cho chủ:** …
- **Blocker:** …

<details><summary>Trạng thái git</summary>
…
</details>
<!-- report:end -->
```

Mới nhất ở trên; append-only.

### `STATE.json`

```json
{
  "protocol": "hermes-owner-v1",
  "schema": 1,
  "active_directive": { "id": "…", "number": 3, "issuer": "hermes", "title": "…",
                        "issued_at": "…", "valid_until": "…", "seal": "sha256:…",
                        "file": ".ai/handoff/INBOX.md" },
  "history": [ { "id": "…", "superseded_at": "…" } ],
  "last_report": { "id": "…", "status": "DONE", "at": "…" },
  "updated_at": "…",
  "updated_by": "hermes(issue)"
}
```

## 7. Mã thoát — chính sách dừng

Operator đã chốt: **không có mệnh lệnh hợp lệ thì phiên dừng**, không tự quyết.

| Mã | Nghĩa | Hành vi agent |
|---|---|---|
| `0` | Có lệnh hợp lệ | Làm đúng lệnh |
| `2` | Lỗi dùng / thiếu file | Dừng, báo lỗi |
| `3` | Chưa có lệnh nào | Dừng, báo Operator chạy workflow |
| `4` | Lệnh hết hạn | Dừng, báo Operator gia hạn |
| `5` | Seal lệch | Dừng, báo `INBOX.md` bị sửa tay |
| `6` | Sai người ban hành / lệch `STATE.json` | Dừng, báo kiểm tra `.ai/handoff/` |

Ngoại lệ duy nhất: Operator nói rõ **“bỏ qua Hermes phiên này”**; khi đó vẫn phải ghi báo cáo
cuối phiên và nêu lý do.

## 8. Chi phí

- GitHub Actions trên repo public: **miễn phí**.
- Mỗi lượt owner loop = **1 lần gọi LLM** với brief ~5–8k token + tối đa 6 vòng tool
  (`hermes config set agent.max_turns 6`), toolset `safe` (không shell, không ghi file) để
  giảm rủi ro và token.
- Mặc định **chỉ chạy khi bấm tay**. Bật `HERMES_OWNER_AUTO` sẽ tốn credit đều đặn —
  ước tính thô: một lượt vài cent với `gemini-2.5-flash`, 4 lượt/ngày nếu bật schedule.
- `boot`, `closeout`, `status`, `selftest` **không gọi LLM** → không tốn credit.
  Một phiên agent không có lệnh hợp lệ sẽ dừng mà không tốn gì.

## 9. Bảo mật

- `INBOX.md`, `OUTBOX.md` được commit công khai → **không đặt bí mật** vào mệnh lệnh/báo cáo.
- Workflow chỉ dùng secret có sẵn (`OPENROUTER_API_KEY`, `GITHUB_TOKEN`) và không in giá trị.
- Hermes ra lệnh với toolset `safe` (web/vision/image_gen) — **không có shell**, không sửa được
  repo trong lượt ra lệnh.
- Quyền ghi chỉ vào nhánh `hermes-owner/state`; `main` chỉ nhận qua PR do Operator merge.
- `.ai/handoff/.cache/` (nhật ký boot, directive đang dùng) bị gitignore.

## 10. Xử lý sự cố

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| `boot` trả 3 | Chưa từng chạy workflow | Chạy **Hermes owner loop** |
| `boot` trả 4 | Lệnh quá 72h | Chạy lại workflow (lệnh mới thay lệnh cũ) |
| `boot` trả 5 | `INBOX.md` bị sửa tay | Ban hành lại lệnh; **đừng** sửa seal |
| `boot` trả 6 | `STATE.json` lệch `INBOX.md` | `git checkout origin/hermes-owner/state -- .ai/handoff/` |
| Workflow lỗi “không có khối ZEUS_DIRECTIVE” | Model không theo định dạng | Chạy lại; nếu lặp lại, đổi `model` sang `anthropic/claude-sonnet-4` |
| Workflow `startup_failure`, annotation “action … is not allowed … must be pinned to a full-length commit SHA” | Policy của repo bắt buộc pin action bằng SHA đầy đủ | Dùng `uses: owner/action@<40 ký tự sha>  # vN`; toàn bộ `.github/workflows/` trong repo đã được pin |
| Workflow lỗi 403 khi tạo PR | Thiếu quyền | Settings → Actions → General → *Read and write permissions* |
| `push` nhánh trạng thái bị từ chối | Branch protection | Cho phép `hermes-owner/state` hoặc dùng ruleset riêng |
| Muốn xem agent đã làm gì | — | `python3 scripts/hermes_owner.py status` + `OUTBOX.md` |

## 11. Giới hạn — nói thẳng

1. **Không có hook của Arena.** "Tự động" ở đây nghĩa là: agent đọc `AGENTS.md` (chuẩn ngành)
   và chạy boot. Nếu một agent lạ không đọc `AGENTS.md`, nó có thể bỏ qua ĐIỀU 0 — khi đó
   `closeout` sẽ thiếu báo cáo và Hermes biết phiên đó không tuân thủ.
2. **Sandbox Arena không có key.** Không thể gọi Hermes *trực tiếp* trong phiên Arena.
   `--live` chỉ dùng được trên máy/VPS/Codespaces có key và binary.
3. **Lệnh có hạn.** Cố ý: lệnh cũ không được phép điều khiển phiên mới. Muốn chạy lâu hơn,
   chủ phải gia hạn bằng lệnh mới.
4. **Chất lượng lệnh = chất lượng brief.** Brief lấy từ `Status/TODO/Roadmap/OUTBOX/PR` —
   nếu các file đó lạc hậu, lệnh sẽ lạc hậu. Báo cáo cuối phiên là cách giữ brief đúng.

## 12. Liên quan

- `AGENTS.md` — ĐIỀU 0 (luật gốc cho mọi agent)
- `.ai/handoff/README.md` — hộp thư
- `skills/hermes-owner/SKILL.md` — skill cho chính Hermes khi ban hành lệnh
- `docs/HERMES_ACTIONS.md` — chạy Hermes thủ công trên Actions
- `docs/ARENA_VS_HERMES.md` — so sánh Arena Agent vs Hermes
