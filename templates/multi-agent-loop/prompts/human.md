# PROMPT — Human (người quyết định)

Người là mắt xích duy nhất có quyền `accept` / `reject`. Không agent nào được thay vai này.

---

## Trước khi bấm accept, kiểm 4 dòng trong `status` / `STATE.json`

1. **Verification result** = `pass`, và `fresh_evidence` ≥ số bước trong plan.
2. **`ignored_stale_evidence`** — nếu > 0, xem lại: có lệnh nào bị bỏ vì chạy trước `submit` không.
3. **Metric `null`** — đọc `reason`. Chưa đo được là chấp nhận được; **giả vờ đã đo** thì không.
4. **Metric `0`** — mở `evidence` tương ứng, xác nhận lệnh thật sự đã chạy và exit 0.

## Quy tắc

- `accept` khi: verification pass **và** bạn hiểu thay đổi **và** rủi ro nằm trong mức chấp nhận.
- `reject` bắt buộc có `--note` nêu lý do cụ thể — lý do đó là đầu vào cho plan kế tiếp.
- Không accept chỉ vì "agent nói đã xong". Không accept khi verifier là chính executor.
- Nếu plan ban đầu sai (không phải executor làm sai), reject và sửa plan — đừng bắt executor
  gánh lỗi thiết kế.

```bash
python3 scripts/loop_state.py status --dir .loop        # xem toàn cảnh
python3 scripts/loop_state.py decide --dir .loop --by operator --accept --note "đã review diff + CI xanh"
python3 scripts/loop_state.py decide --dir .loop --by operator --reject --note "thiếu test cho case rỗng"
```
