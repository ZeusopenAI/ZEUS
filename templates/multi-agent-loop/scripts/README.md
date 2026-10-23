# /scripts — hai công cụ tuỳ chọn

Template có hai tầng, dùng được độc lập:

| Tầng | File | Dùng khi nào |
|---|---|---|
| **Contract dữ liệu + bộ kiểm** | `spec/checks.py` (+ `spec/rules.md`, `spec/schema.json`) | Mặc định. Verifier chạy trên `input/` + `output/` + `log/`. |
| **Máy trạng thái phiên** | `scripts/loop_state.py`, `scripts/verify_gate.py` | Khi cần ghi lại vòng planner→executor→verifier→human như một state machine có pha, attempt, accept/reject. |

`loop_state.py` và `verify_gate.py` cũng cưỡng chế đúng 5 luật (executor không tự chấm,
evidence cũ bị loại theo `started_at`, null cần reason, 0 cần evidence), nhưng ở mức *phiên làm việc*
thay vì mức *dữ liệu*. Hai tầng không xung đột: `verify_gate.py` sinh evidence cho từng attempt,
`checks.py` kiểm toàn bộ dữ liệu.

```bash
python3 scripts/loop_state.py init --dir .loop --slug ten-viec \
  --planner planner --executor executor --verifier verifier --human human
python3 scripts/loop_state.py status --dir .loop
```
