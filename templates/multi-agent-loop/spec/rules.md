# SPEC / RULES — v1

Luật chơi của vòng vận hành. File này là **ngôn ngữ tự nhiên + ràng buộc máy kiểm được**.
Bot nào cũng đọc được; đổi bot không phải viết lại pipeline.

`MUST` / `MUST NOT` theo nghĩa RFC 2119.

---

## 1. Năm vai và cửa I/O riêng

| Vai | Được ghi | Được đọc | Tuyệt đối không |
|---|---|---|---|
| **Planner** | `spec/` | `state/`, `reports/`, `input/` | ghi `output/`, `verify/`; tự sửa kết quả |
| **Executor** | `output/`, `log/` | `spec/`, `state/`, `input/` | ghi `verify/`, `reports/`; chấm điểm; sửa `spec/` |
| **Verifier** | `verify/` | `spec/`, `input/`, `output/`, `log/`, `state/` | ghi `output/`; đọc `reports/` để kết luận |
| **State Keeper** | `state/` (chỉ qua `scripts/loop_state.py`) | — | là "trí nhớ trong prompt" |
| **Human** | `reports/`, quyết định accept/reject | tất cả | bị thay bằng agent tự duyệt |

`MUST` mỗi vai chỉ ghi trong cửa của mình. CI kiểm bằng `checks.py ownership`.
`MUST NOT` Executor và Verifier là cùng một danh tính (cùng model + cùng phiên + cùng người chạy).

## 2. Trạng thái nằm trên đĩa

`MUST` mọi quyết định (đã làm gì, còn bao nhiêu, hạn mức, cái gì là "xong") nằm trong
`state/state.json` + `log/*.jsonl`.

`MUST NOT` để trạng thái chỉ tồn tại trong prompt, lịch sử chat, hay bộ nhớ phiên.
Phiên mới mở ra: đọc state là biết đang ở đâu, không cần "nhớ".

`MUST` mỗi lần chuyển trạng thái ghi 1 dòng JSON vào `log/journal.jsonl` (append-only).

## 3. Chỉ số: `null` + reason, không có 0 giả

Mọi số trong `output/` và trong `state/` tuân theo một trong hai dạng:

```jsonc
// Đã đo
{"value": 24, "measured_by": "executor:gemini-flash", "evidence": "log/run-2026-10-23.jsonl#L2"}

// Chưa đo được
{"value": null, "reason": "chưa có môi trường đo tải thật"}
```

| Tình huống | Ghi |
|---|---|
| Đo được | `value` + `measured_by` (+ `evidence` nếu value = 0) |
| Chưa đo được | `value: null` + `reason` |
| Chắc chắn bằng 0 **và** có log chứng minh | `value: 0` + `measured_by` + `evidence` |
| Không biết | `null` + reason. **Không** 0, **không** ước lượng, **không** bỏ trống |

`MUST NOT` ghi `0` khi chưa chạy gì. `0` không có `evidence` là vi phạm nặng nhất trong spec này —
nó làm sai mọi phép trung bình, tỷ lệ, xếp hạng phía sau.

## 4. Nghiệm thu độc lập, chạy lại từ đầu

`MUST` Verifier chạy `spec/checks.py` trên **dữ liệu gốc** (`input/`) và **output hiện tại**,
trong phiên mới, và sinh báo cáo mới vào `verify/`.

`MUST NOT` Verifier dùng `reports/` (báo cáo của Executor) làm bằng chứng.
`MUST NOT` tái sử dụng báo cáo verify cũ. Mốc so sánh: `started_at` của evidence phải sau
thời điểm output được tạo (`output/.manifest.json`).

`MUST` kết luận do máy quyết: `pass` chỉ khi mọi check bắt buộc trả `pass`.

## 5. Thời gian

`MUST` mọi timestamp là UTC, dạng `YYYY-MM-DDTHH:MM:SSZ`.
`MUST` mọi báo cáo ghi rõ **"Ngày của hệ thống"** = ngày UTC tại thời điểm chạy.
`MUST NOT` dùng ngày địa phương để tính hạn mức — lệch múi giờ làm sai quota qua đêm.
`MUST` `state/state.json` có `system_day` cập nhật theo UTC, và quota reset theo UTC.

## 6. Ba bẫy phải kiểm riêng

### 6.1 Múi giờ / ranh giới ngày
Check `utc_format`: mọi timestamp kết thúc bằng `Z` hoặc offset `+00:00`.
Check `day_boundary`: `system_day` trong state khớp ngày UTC hiện tại; nếu lệch ⇒ cảnh báo
"hạn mức có thể đã reset sai".

### 6.2 Sinh hàng loạt đáng ngờ
Check `throughput`: tốc độ ghi bản ghi (từ `log/`) vượt `max_records_per_second` (mặc định 50)
⇒ `fail`, vì khả năng cao là bịa chứ không phải xử lý thật.
Check `duplicates`: tỷ lệ trùng lặp nội dung > `max_duplicate_rate` (mặc định 0.05) ⇒ `fail`.
Check `length_distribution`: outlier độ dài quá 3×IQR ⇒ `warn`; nếu mẫu < 30 ⇒ **không đo được**,
ghi `value: null` + reason (không được ghi 0).

### 6.3 Số 0 giả
Check `fake_zero`: mọi `value == 0` phải có `measured_by` + `evidence` trỏ tới dòng log có thật.
Thiếu ⇒ `fail`.

## 7. Schema

`MUST` output khớp `spec/schema.json`. Record sai schema ⇒ `fail`, không được "tự sửa rồi bỏ qua".

## 8. Ngày làm việc

Một phiên = đọc `state/` → kiểm tra quota ngày → làm → ghi `output/` → ghi `log/`
→ Verifier chạy `checks.py` → ghi `verify/` → Human duyệt → ghi `reports/` (kết thúc bằng mục
**"Ngày mai"**).

`MUST NOT` báo cáo ngày tự quyết định trạng thái hệ thống. Báo cáo chỉ **phản ánh** trạng thái đã
được `checks.py` kiểm lại.
