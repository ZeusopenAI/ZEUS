# /output — nơi DUY NHẤT Executor được ghi

Định dạng: mỗi file `*.jsonl`, mỗi dòng là một record khớp `spec/schema.json`.

Hợp lệ:

```json
{"id": "r-0001", "created_at": "2026-10-23T08:12:00Z", "source": "input/raw.jsonl#L10",
 "status": "ok", "content": "...", "evidence": "log/run-2026-10-23.jsonl#L2",
 "metrics": {"latency_ms": {"value": 812, "measured_by": "executor", "unit": "ms"}}}
```

Chưa đo được — ghi `null` + `reason`, **không** ghi 0:

```json
{"id": "r-0002", "created_at": "2026-10-23T08:12:03Z", "source": "input/raw.jsonl#L11",
 "status": "partial", "reason": "thiếu trường 'address' trong bản ghi gốc",
 "metrics": {"confidence": {"value": null, "reason": "model không trả score"}}}
```

## Cấm

- Ghi `0` khi chưa chạy gì. `0` chỉ hợp lệ khi có `measured_by` **và** `evidence` trỏ tới dòng log có thật.
- Tự sửa `verify/` hay `reports/`.
- Ghi đè output cũ mà không tăng số batch (verifier cần lịch sử để so).
