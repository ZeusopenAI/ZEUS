# /verify — nơi DUY NHẤT Verifier được ghi

Mỗi lần chạy sinh **một file mới**, không sửa file cũ:

```bash
python3 spec/checks.py run \
  --root . --spec spec --input input --output output --log log --state state/state.json \
  --by verifier \
  --report "verify/checks-$(date -u +%Y%m%dT%H%M%SZ).json"
```

Báo cáo chứa: `overall` (`pass` / `fail` / `not_measured`), từng check với `status` + `metrics`,
`output_snapshot` (hash của `output/` tại thời điểm chạy), `system_day`.

## Chống dùng lại báo cáo cũ

```bash
python3 spec/checks.py freshness --root . --output output --report verify/checks-<mốc>.json
```

- `output_snapshot` trong báo cáo ≠ hash output hiện tại ⇒ **exit 5**: báo cáo đã cũ, phải chạy lại.
- Đây là lý do `checks.py run` từ chối ghi đè báo cáo đã tồn tại (trừ `--force`).

## Cấm

- Đọc `reports/` (báo cáo của Executor) để kết luận.
- Sửa `output/` cho khớp check. Output sai là việc của Executor.
- Kết luận `pass` khi có check bắt buộc `fail`.
