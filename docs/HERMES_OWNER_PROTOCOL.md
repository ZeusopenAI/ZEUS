# Hermes Owner Protocol — kênh cố vấn TÙY CHỌN

> Trạng thái: **chính sách cập nhật 2026-10-28** · Engine: `scripts/hermes_owner.py` ·
> Tên "Owner" / "mệnh lệnh" / "chủ" là **tên lịch sử**, giữ lại để không gãy file, workflow và
> nhánh `hermes-owner/state`. Hermes **không còn là chủ phiên chat** và **không bắt buộc**.
> Phân tích sự cố: [`HERMES_SESSION_ERROR_RCA.md`](HERMES_SESSION_ERROR_RCA.md) ·
> Luật gốc: [`../AGENTS.md`](../AGENTS.md) ĐIỀU 0.

## 0. Chính sách hiện hành — đọc cái này trước

| Câu hỏi | Trả lời |
|---|---|
| AI có **phải** gọi Hermes không? | **Không.** Gọi hay không đều đúng luật. |
| AI có **được** gọi Hermes không? | **Có.** `bash scripts/hermes-session-boot.sh` (tùy chọn). |
| Không có gợi ý / hết hạn / seal sai / workflow lỗi thì sao? | **Tiếp tục làm việc bình thường.** Không dừng, không báo lỗi cho người dùng như một lỗi chặn. |
| Gợi ý có bắt buộc phải làm không? | **Không.** Yêu cầu trực tiếp của Operator / người dùng luôn thắng. |
| Báo cáo cuối phiên có bắt buộc không? | **Không.** `hermes-session-closeout.sh` là tùy chọn. |
| Có cách bật lại chế độ "dừng khi thiếu lệnh" không? | Có, **chỉ khi Operator nói rõ**: `boot --strict` hoặc `HERMES_OWNER_STRICT=1`. AI không tự bật. |

Lý do thay đổi: ngày 23/10/2026 giao thức được thiết kế như một **cổng chặn cứng**
(ĐIỀU 0 cũ). Workflow `hermes-owner-loop.yml` sau đó lỗi 2 lượt ở bước tách marker, nên
`INBOX.md` không bao giờ có nội dung; boot trả mã 3 và **mọi phiên chat bị chặn**. Xem
[`HERMES_SESSION_ERROR_RCA.md`](HERMES_SESSION_ERROR_RCA.md).

## 1. Bối cảnh kỹ thuật (những sự thật không đổi)

- Arena **không** cho cài hook/skill tự chạy khi mở phiên; không có API "gọi Hermes" từ Arena.
- Phiên Arena là **ephemeral**: hết phiên là mất, không giữ process. Hermes không chạy thường
  trực *bên trong* phiên Arena.
- Sandbox Arena **không có** API key provider, không có binary `hermes`, mạng bị allowlist.
- Ba kênh duy nhất để Hermes tham gia: **`AGENTS.md`** (agent đọc khi mở repo), **script trong
  repo**, và **GitHub Actions** (nơi Hermes thật sự thức dậy).
- Vì vậy Hermes chỉ có thể truyền gợi ý qua **repo làm hộp thư**. Một kênh như vậy vốn không
  nên là điều kiện tiên quyết của một phiên chat — đó là sai lầm thiết kế đã sửa.

| Kênh | Cơ chế | Vai trò hiện nay |
|---|---|---|
| `AGENTS.md` | Agent đọc khi mở repo | Nói rõ Hermes là **tùy chọn**, không chặn phiên |
| Script trong repo | `bash scripts/hermes-session-boot.sh` | Hỏi thăm gợi ý (tùy chọn), mặc định luôn thoát 0 |
| GitHub Actions | `hermes-owner-loop.yml` | Nơi Hermes ban hành gợi ý, **có lỗi cũng không sao** |

## 2. Kiến trúc

```text
        ┌──────────── GitHub Actions (TÙY CHỌN) ───────────────────────┐
        │  hermes-owner-loop.yml                                       │
        │  1. đọc OUTBOX + Status/TODO/Roadmap → brief                 │
        │  2. hermes -z "…" -m gemini-2.5-flash --provider openrouter │
        │  3. tách khối <<<ZEUS_DIRECTIVE>>> (chịu marker lệch)        │
        │  4. ghi INBOX.md + STATE.json + archive/ (seal SHA-256)      │
        │  5. push nhánh hermes-owner/state + mở PR về main            │
        │  ⚠ Lỗi bất kỳ bước nào → CHỈ cảnh báo, không chặn phiên      │
        └──────────────────┬───────────────────▲───────────────────────┘
                           │ gợi ý            │ báo cáo (tùy chọn)
                           ▼                  │
   ┌──────────── Phiên agent Arena / Codespaces / Cursor ──────────────┐
   │ YÊU CẦU CỦA NGƯỜI DÙNG = ƯU TIÊN CAO NHẤT                        │
   │ (tùy chọn) hermes-session-boot.sh → có gợi ý thì đọc thêm          │
   │            không có / hết hạn / seal sai → TIẾP TỤC bình thường    │
   │ (tùy chọn) hermes-session-closeout.sh → append OUTBOX.md           │
   └──────────────────────────┬───────────────────────────────────────┘
                              ▼
                 arena-auto-pr.yml → PR → merge → main
```

Bốn mảnh ghép (đều là hạ tầng tùy chọn, không phải cổng kiểm soát):

| Thành phần | Vai trò |
|---|---|
| `.ai/handoff/` | Hộp thư: `INBOX.md`, `OUTBOX.md`, `STATE.json`, `archive/` |
| `scripts/hermes_owner.py` | Engine: `boot`, `issue`, `closeout`, `status`, `extract`, `selftest` |
| `scripts/hermes-session-boot.sh` / `-closeout.sh` | Lối vào một dòng (tùy chọn) cho agent |
| `.github/workflows/hermes-owner-loop.yml` | Nơi Hermes ban hành gợi ý |

## 3. Dùng khi muốn (≈ 3 phút)

1. **Không cần làm gì** cho phiên chat chạy được. Đây là mặc định mới.
2. Nếu muốn Hermes góp ý, kiểm tra secret `OPENROUTER_API_KEY` trong
   *Settings → Secrets and variables → Actions* (không có cũng không sao).
3. Actions → **Hermes owner loop** → *Run workflow*. `operator_note`, `model`
   (`google/gemini-2.5-flash`), `ttl_hours` (`72`), `dry_run` (xem trước không ghi file).
4. Sau ~2 phút có PR **🧭 Mệnh lệnh Hermes #N** và nhánh `hermes-owner/state`. Gợi ý chỉ là
   tham khảo — **không merge cũng không sao**, không merge không chặn ai cả.
5. Trong phiên agent, nếu muốn đọc: `bash scripts/hermes-session-boot.sh`.

Muốn tự động (vẫn tùy chọn, tốn credit): tạo biến repo `HERMES_OWNER_AUTO = on`
(*Settings → Secrets and variables → Actions → Variables*). Khi đó workflow tự chạy mỗi 6 giờ
và mỗi khi `OUTBOX.md` merge vào `main`. Biến không bật ⇒ các lượt `schedule` bị `skipped` —
**đó là trạng thái bình thường**, không phải lỗi. Bấm tay luôn chạy được.

## 4. Vòng đời một phiên (tất cả đều tùy chọn)

```bash
# 1) Hỏi thăm Hermes — CÓ THỂ BỎ QUA HOÀN TOÀN
bash scripts/hermes-session-boot.sh       # thoát 0 dù không có gợi ý

# 2) Làm theo yêu cầu trực tiếp của người dùng; gợi ý (nếu có) chỉ là tham khảo

# 3) Báo cáo cho Hermes — TÙY CHỌN
bash scripts/hermes-session-closeout.sh \
  --status DONE \
  --summary "Đã sửa lỗi X; thêm test Y" \
  --tests "python3 -m pytest -q: 12 passed"
```

`closeout` nối báo cáo vào đầu `OUTBOX.md`, cập nhật `STATE.json` (không commit trừ khi thêm
`--commit`). Thiếu báo cáo **không** làm hỏng phiên sau và **không** bị coi là không tuân thủ.
Chế độ `--strict` (xem mục 7) chỉ dùng khi Operator yêu cầu rõ ràng.

## 5. Tham chiếu lệnh

### Boot (tùy chọn)

```bash
bash scripts/hermes-session-boot.sh                 # hỏi thăm (mặc định luôn thoát 0)
bash scripts/hermes-session-boot.sh --offline       # không dùng mạng
bash scripts/hermes-session-boot.sh --json          # kèm JSON: blocking: false khi thiếu gợi ý
bash scripts/hermes-session-boot.sh --materialize   # ghi bản remote vào working tree
bash scripts/hermes-session-boot.sh --live          # gọi Hermes trực tiếp nếu có binary + key
bash scripts/hermes-session-boot.sh --strict        # CHỈ khi Operator bật chế độ cũ
HERMES_OWNER_STRICT=1 bash scripts/hermes-session-boot.sh   # tương đương --strict
```

Thứ tự tìm gợi ý: **working tree → `origin/hermes-owner/state` → (tùy chọn) gọi trực tiếp**.
Không tìm thấy ⇒ in "KHÔNG BẮT BUỘC, KHÔNG CHẶN PHIÊN" và thoát 0.

### Issue (workflow dùng; người cũng dùng được để thử)

```bash
python3 scripts/hermes_owner.py issue \
  --body-file /tmp/directive.md \
  --title "Gợi ý #7 — vá lỗi sync" \
  --ttl-hours 72 \
  --model google/gemini-2.5-flash \
  --source-run "https://github.com/…/runs/123"
```

`issue` tính số thứ tự, bọc seal, ghi `INBOX.md` + `archive/INBOX-<id>.md`, đẩy gợi ý cũ vào
`STATE.history`. Dù có gợi ý, nội dung vẫn chỉ là **tham khảo**.

### Status / extract / selftest

```bash
python3 scripts/hermes_owner.py status             # luôn thoát 0
python3 scripts/hermes_owner.py status --strict    # trả 3/4/5/6 nếu gợi ý không dùng được
python3 scripts/hermes_owner.py extract --input raw.txt --output directive.md
python3 scripts/hermes_owner.py selftest
python3 -m unittest discover -s scripts/tests -p 'test_hermes*.py' -v
```

`extract` chịu các biến thể marker hay gặp (`<<< ZEUS_DIRECTIVE >>>`, `**<<<…>>>**`, chữ thường,
gạch dưới, code fence) và có đường dự phòng lấy theo tiêu đề `# MỆNH LỆNH` khi có mục bắt buộc.
Đây là lỗi thật từng làm workflow đỏ 2 lượt — đã có test khoá lại.

### Closeout (tùy chọn)

```bash
bash scripts/hermes-session-closeout.sh --status BLOCKED \
  --summary "Không có quyền ghi vào repo X" \
  --blocker "Cần Operator cấp quyền" \
  --questions "Có nên chuyển sang nhánh khác không?"
```

`--status`: `DONE` | `PARTIAL` | `BLOCKED`. Thêm `--commit` để commit thay đổi vào git.

## 6. Định dạng dữ liệu

### `INBOX.md`

```markdown
---
protocol: "hermes-owner-v1"
schema: 1
id: "hermes-20261023T0912Z-4f2a"
number: 3
issuer: "hermes"
title: "Gợi ý #3 — vá lỗi boot"
issued_at: "2026-10-23T09:12:00Z"
valid_until: "2026-10-26T09:12:00Z"
seal: "sha256:9f2c…"
model: "google/gemini-2.5-flash"
source_run: "https://github.com/ZeusopenAI/ZEUS/actions/runs/123"
---

# MỆNH LỆNH #3 — …
```

**Seal** = `sha256` của thân gợi ý (sau `---` thứ hai, chuẩn hoá `strip()` + `\n`). Sửa một ký tự
⇒ seal lệch ⇒ `boot --strict` trả **5**; `boot` mặc định vẫn thoát 0 và chỉ bỏ qua nội dung đó.
Seal là *chống sửa tay*, không phải chữ ký mật mã.

Tiêu đề `# MỆNH LỆNH …` và trường `issuer: "hermes"` là **tên lịch sử / nhãn máy đọc**, không
phải tuyên bố quyền lực.

### `OUTBOX.md`

Mỗi báo cáo là một khối giữa `<!-- report:start -->` và `<!-- report:end -->`, mới nhất ở trên,
append-only. Có các mục: Mệnh lệnh, Thời điểm, Nhánh, HEAD, Tóm tắt, Đã kiểm chứng,
Câu hỏi cho chủ, Blocker, trạng thái git. **Báo cáo là tùy chọn.**

### `STATE.json`

```json
{
  "protocol": "hermes-owner-v1",
  "policy": "optional",
  "schema": 1,
  "active_directive": { "id": "…", "number": 3, "issuer": "hermes", "title": "…", "valid_until": "…" },
  "history": [],
  "last_report": { "id": "…", "status": "DONE", "at": "…" },
  "updated_at": "…",
  "updated_by": "hermes(issue)"
}
```

`policy: "optional"` là trường máy đọc khẳng định chính sách hiện hành.

## 7. Mã tín hiệu — KHÔNG còn chính sách dừng

| Mã | Nghĩa | `boot` mặc định | `boot --strict` (Operator bật) |
|---|---|---|---|
| `0` | Có gợi ý hợp lệ (hoặc không có gợi ý) | In gợi ý / thông báo, thoát 0 | Thoát 0 |
| `2` | Lỗi dùng / thiếu file | Báo lỗi cục bộ, không chặn yêu cầu người dùng | Thoát 2 |
| `3` | Chưa có gợi ý | Thoát 0, `blocking: false` | Thoát 3, "DỪNG PHIÊN" |
| `4` | Gợi ý hết hạn | Thoát 0, bỏ qua gợi ý cũ | Thoát 4 |
| `5` | Seal lệch | Thoát 0, không dùng nội dung đó | Thoát 5 |
| `6` | Sai người ban hành / lệch `STATE.json` | Thoát 0, không dùng nội dung đó | Thoát 6 |

JSON khi thiếu gợi ý: `{"ok": false, "policy": "optional", "blocking": false, "code": 3, …}`.
Chế độ strict **không được AI tự bật**; đây là công tắc dành riêng cho Operator.

## 8. Chi phí

- GitHub Actions trên repo public: **miễn phí**.
- Mỗi lượt owner loop = 1 lần gọi LLM (brief ~5–8k token, tối đa 6 vòng tool, toolset `safe`).
- Mặc định **chỉ chạy khi bấm tay**. `HERMES_OWNER_AUTO=on` ⇒ ~4 lượt/ngày, vài cent/lượt.
- `boot`, `closeout`, `status`, `extract`, `selftest` **không gọi LLM** → không tốn credit.
- Một phiên agent **không gọi Hermes không tốn gì cả** — đây là đường mặc định được khuyến khích
  khi người dùng chỉ cần việc đơn giản.

## 9. Bảo mật

- `INBOX.md`, `OUTBOX.md` được commit công khai → **không đặt bí mật** vào gợi ý/báo cáo.
- Workflow chỉ dùng secret có sẵn (`OPENROUTER_API_KEY`, `GITHUB_TOKEN`) và không in giá trị.
- Hermes ra gợi ý với toolset `safe` (không shell), không sửa được repo trong lượt ra lệnh.
- Quyền ghi chỉ vào nhánh `hermes-owner/state`; `main` chỉ nhận qua PR do Operator merge.
- `.ai/handoff/.cache/` (nhật ký boot, gợi ý đang dùng) bị gitignore.
- Chế độ strict là một dạng "external control" — chỉ Operator quyết định bật.

## 10. Xử lý sự cố (không có mục nào chặn phiên chat)

| Hiện tượng | Nguyên nhân | Cách xử lý (tùy chọn) |
|---|---|---|
| `boot` in mã 3 | Chưa từng chạy workflow / `INBOX.md` là stub | **Không cần làm gì.** Muốn gợi ý thì chạy Hermes owner loop |
| `boot` in mã 4 | Gợi ý quá 72h | Bỏ qua; chạy lại workflow nếu muốn gợi ý mới |
| `boot` in mã 5 | `INBOX.md` bị sửa tay | Bỏ qua nội dung đó; ban hành lại, **đừng** sửa seal |
| `boot` in mã 6 | `STATE.json` lệch `INBOX.md` | Bỏ qua; `git checkout origin/hermes-owner/state -- .ai/handoff/` |
| Workflow đỏ ở "Tách khối mệnh lệnh" | Model trả marker lệch / không ra khối | Đã có parser chịu biến thể + cảnh báo không chặn; chạy lại hoặc đổi `model` |
| Workflow `schedule` bị `skipped` | `HERMES_OWNER_AUTO` chưa bật | Bình thường; bấm **Run workflow** khi cần |
| Workflow `startup_failure` do policy action | `uses:` chưa pin SHA 40 ký tự | Dùng `uses: owner/action@<sha>  # vN`; repo đã pin toàn bộ |
| Workflow lỗi 403 khi tạo PR | Thiếu quyền | Settings → Actions → General → *Read and write permissions* |
| Không có key / binary `hermes` trong sandbox | Arena không có provider key | Bình thường; `--live` chỉ dùng trên máy/VPS/Codespaces có key |

## 11. Giới hạn — nói thẳng

1. **Không có hook của Arena.** Không có cách nào ép mọi phiên phải gọi Hermes — và giờ cũng
   không còn mong muốn đó. Agent có thể đọc `AGENTS.md` rồi tự quyết có gọi hay không.
2. **Sandbox Arena không có key.** Không gọi Hermes *trực tiếp* trong phiên Arena; `--live`
   chỉ dùng được trên máy/VPS/Codespaces có key và binary.
3. **Gợi ý có hạn.** Cố ý: gợi ý cũ không điều khiển phiên mới. Hết hạn chỉ làm mất gợi ý,
   không làm mất khả năng làm việc.
4. **Chất lượng gợi ý = chất lượng brief.** Brief lấy từ `Status/TODO/Roadmap/OUTBOX/PR`;
   nếu các file cũ thì gợi ý cũ. Báo cáo cuối phiên (tùy chọn) giúp brief tốt hơn.
5. **Tên "owner" gây hiểu nhầm.** Đổi tên file/workflow/nhánh sẽ gãy automation và dữ liệu cũ,
   nên giữ nguyên tên kỹ thuật nhưng đổi hoàn toàn ngữ nghĩa trong tất cả tài liệu luật.
6. **Chế độ strict vẫn tồn tại.** Nếu Operator bật, lỗi cũ (chặn phiên) có thể tái diễn —
   đây là lựa chọn có ý thức, không phải mặc định.

## 12. Lịch sử thay đổi

| Ngày | Thay đổi |
|---|---|
| 23/10/2026 | PR #12 đưa Hermes làm "chủ": ĐIỀU 0 bắt buộc boot, thiếu lệnh ⇒ dừng phiên |
| 24/10/2026 | 2 run `hermes-owner-loop` (40062072101, 40062270254) lỗi tách marker ⇒ không có `INBOX.md` |
| 26/10/2026 | PR #15 ghi nhận "mọi phiên agent bị chặn ở ĐIỀU 0" và sửa parser (chưa merge vào main lúc đó) |
| **28/10/2026** | **Đổi toàn bộ luật sang TÙY CHỌN**: `AGENTS.md`, hiến pháp, README, Status, memory, hộp thư, skill, đặc tả, engine, wrapper, prompt, workflow, CI. Thêm RCA + test chặn hồi quy |

## 13. Liên quan

- `../AGENTS.md` — ĐIỀU 0 (luật gốc, phiên bản tùy chọn)
- `HERMES_SESSION_ERROR_RCA.md` — phân tích sự cố "gọi Hermes làm chủ phiên chat"
- [`../.ai/handoff/README.md`](../.ai/handoff/README.md) — hộp thư (tùy chọn)
- [`../skills/hermes-owner/SKILL.md`](../skills/hermes-owner/SKILL.md) — skill cho Hermes khi đưa gợi ý
- [`HERMES_ACTIONS.md`](HERMES_ACTIONS.md) — chạy Hermes thủ công trên Actions
- [`ARENA_VS_HERMES.md`](ARENA_VS_HERMES.md) — so sánh Arena Agent vs Hermes
