# CONTRACT — Multi-Agent Loop v1

Tài liệu chuẩn. `MUST` / `MUST NOT` theo nghĩa RFC 2119: vi phạm là lỗi, không phải gợi ý.
Mọi điều dưới đây được `scripts/loop_state.py` cưỡng chế; phần nào chưa cưỡng chế được sẽ ghi rõ.

## 0. Định nghĩa

- **Loop** — một thư mục chứa `STATE.json`, `journal.jsonl`, `evidence/`.
- **Attempt** — một lần executor giao kết quả. Mỗi attempt có `n`, `submitted_at`, `metrics`,
  `verification`.
- **Evidence** — bản ghi do `verify_gate.py run` sinh ra: lệnh, `exit_code`, thời điểm bắt đầu/kết
  thúc, hash stdout.

## 1. Năm vai

| Vai | Bắt buộc | Quyền | Cấm |
|---|---|---|---|
| Planner | có | `plan` | sửa code; chấm điểm |
| Executor | có | `submit` | `verify`, `decide` |
| Verifier | có | `verify` | `submit` cùng attempt; đọc báo cáo executor làm bằng chứng |
| State | file | ghi nguyên tử + journal | nằm trong prompt, trong context, trong RAM |
| Human | có | `decide` | bị thay bằng agent tự duyệt |

`MUST`: `executor ≠ verifier` (hai danh tính khác nhau). Planner được phép trùng human.

## 2. Năm luật bất biến

### 2.1 State trên file

`MUST` mọi chuyển pha ghi vào `STATE.json` bằng ghi nguyên tử (tmp + rename) và thêm **đúng một**
dòng vào `journal.jsonl`.

`MUST NOT` giữ trạng thái quyết định trong prompt, trong lịch sử chat, hoặc trong biến của một process
sống. Phiên agent chết ⇒ state vẫn đọc được từ đĩa.

`MUST NOT` sửa tay `STATE.json`. Mọi thay đổi đi qua CLI để journal khớp state.

### 2.2 Executor không tự chấm

`MUST` người gọi `verify` mang vai `verifier`.
`MUST NOT` người vừa `submit` được `verify` chính attempt đó — kể cả khi họ đổi tên vai.
`MUST NOT` `decide` được gọi bởi bất kỳ ai ngoài `human`.

### 2.3 Verification chạy lại từ đầu

`MUST` `verify` chỉ dùng evidence có `started_at >= attempt.submitted_at`.
`MUST NOT` dùng lại evidence của attempt trước, log cũ, hay "kết quả lần trước vẫn đúng".
`MUST` `verify_gate.py run` **luôn thực thi** lệnh; không có cờ tái sử dụng log.
`MUST` kết quả cuối do evidence quyết định: `pass` chỉ khi **mọi** evidence mới có `exit_code == 0`.

Ghi chú: evidence do chính executor sinh ra (để chứng minh metric) luôn có `started_at` trước
`submit`, nên bị loại khỏi bước verify theo đúng luật trên — không cần cờ đặc biệt, không thể
"quên" tái sử dụng.

### 2.4 `null` + `reason` khi chưa đo được

`MUST` metric chưa đo là `{"value": null, "reason": "<vì sao>"}`.
`MUST NOT` bỏ trống khóa `value` để ám chỉ "không có".
`MUST NOT` `null` mà không có `reason`.
`MUST NOT` thay `null` bằng `0` hay bằng ước lượng không nguồn.

### 2.5 Không ghi 0 giả

`MUST` mọi giá trị số có `measured_by`.
`MUST` giá trị `0` có thêm `evidence` trỏ tới một lệnh đã chạy thật trong attempt đó.
`MUST NOT` dùng `0` như giá trị mặc định khi chưa chạy gì.

## 3. Máy trạng thái

```
        init
         │
         ▼
     planned ──plan(planner)──▶ planned
         │
    submit(executor)
         ▼
     submitted
         │
   verify(verifier)
    ┌────┴─────┐
    ▼          ▼
verified_pass  verified_fail
    │              │
decide(human)  submit(executor) ──▶ submitted (attempt mới)
    │
    ├── accept ──▶ accepted
    └── reject ──▶ rejected ──submit──▶ submitted (attempt mới)
```

| Hành động | Vai | Pha trước | Pha sau | Điều kiện |
|---|---|---|---|---|
| `init` | planner | — | `planned` | executor ≠ verifier |
| `plan` | planner | `planned` | `planned` | mỗi bước có `→ lệnh kiểm chứng` |
| `submit` | executor | `planned`, `verified_fail`, `rejected` | `submitted` | đã có plan |
| `verify` | verifier | `submitted` | `verified_pass` / `verified_fail` | ≥1 evidence mới |
| `decide --accept` | human | `verified_pass` | `accepted` | — |
| `decide --reject` | human | `verified_pass`, `verified_fail` | `rejected` | có `--note` |

Mọi chuyển pha trái bảng ⇒ lỗi (exit 3), không "cố gắng hiểu ý".

## 4. Định dạng state

Xem `state.schema.json`. Tóm tắt:

```json
{
  "schema": "multi-agent-loop/1",
  "task":   { "slug": "...", "goal": "...", "created_at": "...", "created_by": "..." },
  "roles":  { "planner": "...", "executor": "...", "verifier": "...", "human": "..." },
  "phase":  "planned | submitted | verified_pass | verified_fail | accepted | rejected",
  "plan":   { "steps": [ { "id": 1, "text": "...", "check": "..." } ], "planned_by": "..." },
  "attempts": [ { "n": 1, "submitted_at": "...", "metrics": { }, "verification": { } } ],
  "decisions": [ { "at": "...", "by": "...", "action": "accept", "note": "..." } ]
}
```

## 5. Mã thoát

| Mã | Nghĩa |
|---|---|
| 0 | OK |
| 2 | lỗi dùng (thiếu tham số, thiếu file, state đã tồn tại) |
| 3 | sai thứ tự pha |
| 4 | vi phạm nguyên tắc (tự chấm, 0 giả, null thiếu reason, evidence cũ) |
| 5 | state hỏng / sai schema |

## 6. Điều contract này KHÔNG bảo đảm

- Không chặn được executor giả mạo evidence nếu nó có quyền ghi file.
- Không bảo đảm plan *đúng* — chỉ bảo đảm plan *có kiểm chứng cho từng bước*.
- Không thay thế review của người: `accept` vẫn là quyết định của con người.
- `journal.jsonl` append-only theo quy ước; muốn bất biến thật phải đẩy ra nơi chỉ-ghi.
