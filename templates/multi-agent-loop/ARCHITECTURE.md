# ARCHITECTURE — template repo cho nhiều bot

Tài liệu này trả lời: **một repo được tổ chức thế nào để nhiều bot (khác hãng, khác model, khác phiên)
làm việc cùng mà không tự khen nhau, không mất tiến độ, không bịa số.**

Không phải framework. Không có server, không có DB, không có thư viện ngoài. Chỉ có: **thư mục có
luật ghi**, **schema cố định**, **một bộ kiểm chạy được bằng máy**, và **CI làm trọng tài**.

---

## 1. Kiến trúc một loop

```
                    ┌───────────────────────────────┐
   HUMAN ──────────▶│  spec/  (rules.md · schema.json · checks.py)  │◀── PLANNER
   (trọng tài)      │  LUẬT + HỢP ĐỒNG DỮ LIỆU + BỘ KIỂM             │    (kiến trúc sư)
        │           └───────────────┬───────────────┘
        │                           │ đọc luật/schema
        │                           ▼
        │           ┌───────────────────────────────┐
        │           │  input/   (dữ liệu gốc, chỉ đọc) │
        │           └───────────────┬───────────────┘
        │                           │
        │                           ▼
        │           ┌───────────────────────────────┐
        │           │  output/  ← EXECUTOR ghi        │
        │           │  log/     ← EXECUTOR ghi        │
        │           └───────────────┬───────────────┘
        │                           │ đọc output + input + log
        │                           ▼
        │           ┌───────────────────────────────┐
        └──────────▶│  verify/  ← VERIFIER ghi        │
                    │  (báo cáo checks.py, có hash)   │
                    └───────────────┬───────────────┘
                                    │ chỉ đọc kết quả đã kiểm
                                    ▼
                    ┌───────────────────────────────┐
                    │  reports/ ← HUMAN ghi           │
                    │  (báo cáo ngày + "Ngày mai")    │
                    └───────────────────────────────┘

    state/state.json  ── State Keeper: ngày UTC, quota, done/remaining, "xong" là gì
```

Điểm mấu chốt: **mũi tên là quyền**. Vai nào ghi được vào đâu là do cấu trúc thư mục quy định, và
`checks.py ownership` kiểm lại bằng `git diff` — không dựa vào lời hứa của agent.

## 2. Hợp đồng thư mục

| Thư mục | Vai ghi | Vai đọc | Sản phẩm |
|---|---|---|---|
| `spec/` | Planner | tất cả | `rules.md`, `schema.json`, `checks.py` |
| `state/` | State Keeper (chỉ qua script) | tất cả | `state.json` |
| `input/` | người (dữ liệu gốc) | Executor, Verifier | dữ liệu thô, chỉ đọc |
| `output/` | **Executor** | Verifier, Human | record theo schema |
| `log/` | **Executor** | Verifier | JSONL append-only, có `started_at`/`finished_at` |
| `verify/` | **Verifier** | Human | báo cáo `checks-<UTC>.json` + hash output |
| `reports/` | **Human** | người | `YYYY-MM-DD.md`, kết thúc bằng "Ngày mai" |
| `examples/` | Planner | scaffolder, test | record mẫu, dùng để tự kiểm chứng |

Quy tắc: **không vai nào ghi được vào ô của vai khác**. Vi phạm bị `checks.py ownership --role X`
bắt ở CI, và bị người review thấy ngay trong `git diff`.

## 3. Ba hợp đồng dữ liệu

### 3.1 Record (mỗi dòng trong `output/*.jsonl`)

```jsonc
{
  "id": "r-0001",                       // bắt buộc, không trùng
  "created_at": "2026-10-23T08:00:01Z", // UTC bắt buộc
  "source": "input/raw.jsonl#L1",       // trỏ về dòng gốc
  "status": "ok" | "partial" | "skipped",
  "reason": "…",                        // bắt buộc khi status ≠ ok
  "content": "…",                       // nếu loại việc sinh nội dung
  "evidence": "log/run-0001.jsonl#L1",  // chứng minh record này được xử lý thật
  "metrics": { "<tên>": <metric> }
}
```

### 3.2 Metric (mọi con số)

```jsonc
{"value": 24, "measured_by": "executor:gemini-flash", "evidence": "log/run.jsonl#L2"}  // đã đo
{"value": null, "reason": "chưa có môi trường đo"}                                     // chưa đo
```

- `null` **phải** có `reason`.
- `0` **phải** có `measured_by` + `evidence` trỏ tới dòng log có thật.
- Trường số cấp record (`score`, `violation_count`, …) cũng bị luật này, qua `--zero-guard-fields`.

### 3.3 Log (append-only, chứng minh "có chạy thật")

```jsonc
{"at": "…", "started_at": "…", "finished_at": "…", "records": 3, "by": "executor"}
```

`throughput` đọc chính file này để phát hiện tốc độ phi lý (643 record trong 0,23 giây).

## 4. CI — tầng độc lập thật sự

```yaml
# .github/workflows/verify.yml  (mỗi loop có một bản)
pull_request →  checks.py ownership  →  checks.py run  →  unit test  →  artifact báo cáo
```

Vì sao CI là trọng tài chứ không phải "verifier là một con bot khác":
- Runner là máy sạch, executor **không** ghi được vào log của runner.
- Kết quả verify được upload làm artifact — không xoá được sau khi chạy.
- Verifier là *một process*, không phải *một lời khai*. `checks.py` quyết định, không phải model.

Nếu muốn thêm một bot verifier nữa (khác hãng), bot đó chỉ cần: chạy `checks.py` và **không** giữ
quyền ghi `output/`. Không cần tin bot đó — chỉ cần nó chạy đúng lệnh.

## 5. Sinh một loop mới (3 cách dùng)

```bash
python3 scripts/new_loop.py list
python3 scripts/new_loop.py create --preset batch-extract --dir ../loc-danh-ba \
  --slug loc-danh-ba --goal "Trích xuất tên/công ty/email" --owner quangquy
```

Scaffolder **tự kiểm chứng**: chạy `checks.py` trên `examples/` trong bản tạm; nếu không `pass`
thì xoá thư mục và báo lỗi — không giao loop hỏng.

Ba cách triển khai:

| Cách | Khi nào | Lệnh |
|---|---|---|
| **Repo riêng cho một việc** | việc chạy dài ngày, có người ngoài xem | `create --dir ../repo-moi` rồi `git init` trong đó |
| **Một thư mục trong repo có sẵn** | việc phụ, cùng đội | `create --dir loops/loc-danh-ba` |
| **Nhiều loop song song** | nhiều loại việc, mỗi loại một quota | `loops/<việc>/` — mỗi loop có `spec/`, `state/` riêng |

Với nhiều loop: **không dùng chung `state/`**. Mỗi loop một quota, một ngày hệ thống, một bộ luật.
Muốn tổng hợp thì viết thêm một loop thứ N+1 chỉ đọc `verify/*.json` của các loop khác.

## 6. Preset có sẵn

| Preset | Loại việc | Luật riêng đáng chú ý |
|---|---|---|
| `batch-extract` | trích xuất hàng loạt | trường null phải có `reason_fields`; `extraction_coverage` bắt buộc mỗi record |
| `bulk-grading` | chấm hàng loạt | `judge_model` ≠ executor; `score = 0` phải có evidence; `score = null` phải có reason |
| `data-validation` | kiểm dữ liệu | `violations` phải cụ thể; `violation_count = 0` phải có evidence |

Thêm preset mới: tạo `presets/<tên>/` gồm `preset.json`, `schema.json`, `example-output.jsonl`,
(tuỳ chọn) `rules.append.md`. `new_loop.py` sẽ tự dùng — không cần sửa code.

## 7. Bảng tra: lỗi gì, ai sửa

| Mã thoát `checks.py` | Nghĩa | Ai sửa |
|---|---|---|
| `0` | mọi check bắt buộc pass | — |
| `2` | lỗi dùng / thiếu tham số | người chạy |
| `3` | không có record nào để kiểm | Executor (chưa ghi gì) |
| `4` | có check fail | **Executor** sửa output rồi chạy lại |
| `5` | báo cáo cũ / bị ghi đè | **Verifier** chạy lại từ đầu |

Fail nằm ở `spec/` (luật sai, schema sai) thì người sửa là **Planner**, không phải Executor.
Đây là lỗi thiết kế, không phải lỗi thi hành — ghi rõ trong `reports/` để không bắt executor chịu oan.

## 8. Năm luật nằm ở đâu

| Luật | File | Cơ chế |
|---|---|---|
| State trên file, không trong prompt | `state/state.json`, `log/` | `system_day` UTC; phiên mới đọc là biết đang ở đâu |
| Executor không tự chấm | `spec/checks.py` → `ownership` | `git diff` cho thấy executor đụng `spec/`, `verify/`, `reports/` ⇒ fail |
| Verification chạy lại từ đầu | `spec/checks.py` → `run` + `freshness` | từ chối ghi đè báo cáo; `output_snapshot` phát hiện báo cáo lạc hậu |
| `null` + reason | `spec/checks.py` → `null_reason` | metric null thiếu reason ⇒ fail |
| Không ghi 0 giả | `spec/checks.py` → `fake_zero` | 0 thiếu `measured_by`/`evidence`, hoặc evidence trỏ log không tồn tại ⇒ fail |

## 9. Giới hạn của kiến trúc này

- **Không chống gian lận có quyền ghi file.** Executor có thể tạo `log/*.jsonl` giả. Chặn thật cần:
  log do runner sinh, hoặc ký log bằng key CI mà executor không giữ. Template để mở, ghi rõ ở đây.
- **Không thay con người quyết định.** `reports/` không tự chốt trạng thái; Human vẫn là người
  `accept`.
- **Chỉ hợp việc máy kiểm được.** Việc sáng tạo, thẩm mỹ, chiến lược: `checks.py` sẽ trả
  `not_measured` — đúng như nó phải thế — và bạn đừng ép nó thành điểm số.
- **Không phải orchestrator.** Không có scheduler. Ai gọi từng bước là việc của bạn (cron, workflow,
  hay chính tay bạn).

## 10. CI là code, cũng phải bị kiểm

`tests/test_ci_workflow.py` kiểm chính các workflow: không heredoc, mọi khối `run:` qua `bash -n`,
mọi `uses:` pin SHA, và **file mà workflow nhắc tới phải tồn tại**.

Lý do tồn tại: một step CI đã từng xanh trong khi chưa chạy dòng `checks.py` nào — heredoc
`cat > f <<'EOF'` lồng trong YAML bị shell nuốt phần sau. Đó đúng là lỗi mà template này
sinh ra để chặn: *báo cáo xanh không chứng minh việc đã làm*. Cùng họ với 0 giả.

Vì vậy fixture cho CI nằm trong repo (`examples/demo-output.jsonl`, `examples/demo-log.jsonl`),
không sinh bằng heredoc trong workflow.

## 11. `scripts/check_state.py`

Kiểm `state/state.json`: `system_day` đúng dạng và không ở tương lai, `timezone` là `UTC`,
đủ 4 vai, executor ≠ verifier, mọi `null` có `reason`, mọi `0` có `measured_by` + `evidence`,
`task.done_criteria` không rỗng. Exit `0` sạch · `2` lỗi dùng · `4` state vi phạm.

Scaffolder chạy nó trên state vừa sinh; CI chạy nó trên loop sinh ra cho cả 3 preset.
