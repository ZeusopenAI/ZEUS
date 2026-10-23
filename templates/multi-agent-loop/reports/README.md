# /reports — báo cáo ngày cho người đọc

Một file mỗi ngày: `reports/YYYY-MM-DD.md`. Viết **sau** khi `verify/checks-*.json` có kết quả.

## Nguyên tắc

1. **Báo cáo không quyết định trạng thái.** Nó chỉ chép lại kết quả `checks.py` đã chạy.
   Số trong báo cáo phải trích từ `verify/checks-*.json`, không được tự tính lại bằng cảm giác.
2. Mọi số **phải kèm nguồn**: `(checks-20261023T1200Z.json → fake_zero.zero_values = 0, evidence: …)`.
3. Số chưa đo được ghi **`null` + lý do**, không ghi `0`.
4. Ghi rõ **"Ngày của hệ thống"** theo UTC — không dùng ngày địa phương.

## Mẫu

```markdown
# Báo cáo ngày 2026-10-23

**Ngày của hệ thống (UTC):** 2026-10-23
**Báo cáo verify dùng cho báo cáo này:** verify/checks-20261023T1400Z.json (overall: pass)

## Đã làm
- Xử lý 120 record từ input/raw.jsonl (checks → schema.records_checked = 120)

## Số đo
| Chỉ số | Giá trị | Nguồn |
|---|---|---|
| Record đã kiểm | 120 | checks-…json → schema.records_checked |
| Trường null có reason | 7 | checks-…json → null_reason.null_values |
| Trường null thiếu reason | 0 | checks-…json → null_reason.null_without_reason (0, proof: quét 120/120 record) |
| 0 thiếu evidence | 0 | checks-…json → fake_zero.unproven_zeros |
| Tốc độ | 12.4 record/giây | checks-…json → throughput.records_per_second |
| Trùng lặp | 0.8% | checks-…json → duplicates.duplicate_rate |
| Median độ dài | `null` | chưa đủ 30 mẫu — không kết luận |

## Cần người xem
- 3 record `status: partial` ở r-0091, r-0093, r-0101 (thiếu trường `address`)

## Ngày mai
- Bổ sung extraction cho `address`, chạy lại full batch
- Thêm check phân bố độ dài khi mẫu ≥ 30
```
