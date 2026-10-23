# Multi-Agent Loop — Planner / Executor / Verifier / State / Human

Template chạy được ngay để nhiều AI (hoặc AI + CI + người) phối hợp mà **không tự khen nhau**.
Không framework, không server, không thư viện ngoài: chỉ Python 3.11+ và git.

> **Một câu chốt:** cái chưa đo được thì không được biến thành số; cái đã đo được thì phải được
> kiểm lại bằng một tầng độc lập.

## Bộ khung

```
.
├── spec/                   ← Planner ghi. LUẬT CHƠI + máy kiểm
│   ├── rules.md            # luật người đọc được (RFC 2119)
│   ├── schema.json         # JSON Schema cho output
│   └── checks.py           # BỘ KIỂM THẬT — verifier chạy file này
├── state/state.json        ← State Keeper. ngày hệ thống, quota, đã làm, còn lại, "xong" là gì
├── input/                  ← dữ liệu gốc, chỉ đọc
├── output/                 ← Executor ghi DUY NHẤT ở đây (+ log/)
├── verify/                 ← Verifier ghi DUY NHẤT ở đây
├── log/                    ← append-only JSONL: chứng minh việc gì đã chạy thật
├── reports/                ← Human ghi báo cáo ngày, kết thúc bằng "Ngày mai"
├── prompts/                ← prompt mẫu cho từng vai
└── .github/workflows/verify.yml   ← Verifier chạy trên runner sạch
```

Cửa I/O tách biệt để **không ai ghi đè lên nhau**, và `checks.py ownership` kiểm được điều đó bằng git diff.

## 5 luật — cưỡng chế bằng code

| Luật | Cơ chế |
|---|---|
| **State trên file, không trong prompt** | `state/state.json` + `log/*.jsonl`; phiên mới đọc là biết đang ở đâu. `system_day` theo UTC. |
| **Executor không tự chấm** | Executor chỉ ghi `output/` + `log/`; `checks.py ownership --role executor` fail nếu đụng `spec/`, `verify/`, `reports/`. Verifier là danh tính khác, chạy ở runner sạch. |
| **Verification chạy lại từ đầu** | `checks.py run` **từ chối ghi đè** báo cáo cũ (exit 5); mỗi báo cáo có `output_snapshot` (hash của `output/`), `checks.py freshness` phát hiện báo cáo đã lạc hậu. |
| **`null` + reason khi chưa đo được** | `check_null_reason`: giá trị `null` thiếu `reason` ⇒ fail. Mẫu < 30 ⇒ median/outlier ghi `null` + reason, **không** ghi 0. |
| **Không ghi 0 giả** | `check_fake_zero`: `value == 0` bắt buộc `measured_by` + `evidence`, và `evidence` phải trỏ tới dòng log **có thật** (`log/*.jsonl#LN`). Bịa đường dẫn ⇒ fail. |

## Ba bẫy được kiểm riêng

| Bẫy | Check | Ngưỡng |
|---|---|---|
| Múi giờ / ranh giới ngày | `utc_format`, `day_boundary` | mọi timestamp phải UTC `…Z`; `system_day` lệch ngày UTC ⇒ **warn** (quota có thể reset sai) |
| Sinh hàng loạt đáng ngờ | `throughput`, `duplicates`, `length_distribution` | > 50 record/giây ⇒ fail; trùng lặp > 5% ⇒ fail; outlier > 3×IQR ⇒ warn; mẫu < 30 ⇒ `null` |
| Số 0 giả | `fake_zero` | 0 thiếu `measured_by`/`evidence` hoặc evidence không tồn tại ⇒ fail |

## Quickstart (60 giây)

```bash
cd templates/multi-agent-loop
mkdir -p verify

# 1) Executor: xử lý input → output (ghi đúng schema, số liệu có nguồn)
cat > output/batch-0001.jsonl <<'EOF'
{"id": "r-0001", "created_at": "2026-10-23T08:00:01Z", "source": "input/raw.jsonl#L1", "status": "ok", "content": "kết quả một", "evidence": "log/run-2026-10-23.jsonl#L1", "metrics": {"latency_ms": {"value": 120, "measured_by": "executor", "unit": "ms"}}}
{"id": "r-0002", "created_at": "2026-10-23T08:00:02Z", "source": "input/raw.jsonl#L2", "status": "partial", "reason": "thiếu trường address", "metrics": {"confidence": {"value": null, "reason": "model không trả score"}}}
EOF

# 2) Executor: log chứng minh đã chạy thật
mkdir -p log
echo '{"at": "2026-10-23T08:00:00Z", "started_at": "2026-10-23T08:00:00Z", "finished_at": "2026-10-23T08:00:12Z", "records": 2}' > log/run-2026-10-23.jsonl

# 3) Verifier: chạy lại từ đầu, sinh báo cáo MỚI
python3 spec/checks.py run --root . --report "verify/checks-$(date -u +%Y%m%dT%H%M%SZ).json"

# 4) Verifier: chứng minh báo cáo không phải của lần trước
python3 spec/checks.py freshness --root . --report verify/checks-*.json

# 5) Human: ghi reports/YYYY-MM-DD.md kết thúc bằng mục "Ngày mai"
```

Kết quả mẫu: `✅ PASS — 2 record`, từng check `ok / warn / n/a`, mỗi metric trong báo cáo đều có
`measured_by`, và mọi giá trị `0` đều kèm `evidence`.

## Gắn vào repo khác

```bash
cp -r templates/multi-agent-loop/ /duong/dan/repo-moi/loop
cd /duong/dan/repo-moi/loop && rm -rf verify/*.json
printf '\n# dữ liệu chạy của loop\nverify/*.json\n!verify/README.md\n' >> .gitignore
```

Template không import nội bộ — copy là chạy.

## Áp vào ZEUS

| Vai | Ai trong ZEUS |
|---|---|
| Planner | **Hermes** (workflow `hermes-owner-loop.yml` ban hành mệnh lệnh) |
| Executor | **Phiên Arena / Codespaces** |
| Verifier | **CI** (`multi-agent-loop-ci.yml`, `hermes-runtime-ci.yml`) — runner sạch |
| State Keeper | `.ai/handoff/STATE.json` + `log/` |
| Human | **Operator Nguyễn Quang Quý** |

## Giới hạn — nói thẳng

- **Không chống được executor gian lận có chủ đích** nếu nó có quyền ghi file: nó vẫn tạo được
  `log/*.jsonl` giả để "chứng minh" số 0. Chặn thật bằng cách: chạy `checks.py` trên runner sạch
  (workflow có sẵn), hoặc ký log bằng key CI. Template giữ đơn giản có chủ ý.
- **Không phải orchestrator chạy nền.** Đây là *hợp đồng + bộ kiểm*; ai gọi từng bước là việc của bạn
  (người, cron, workflow).
- **Kiểu công việc phù hợp**: lặp lại, có dữ liệu gốc, có tiêu chí kiểm bằng máy.
  Viết sáng tạo / luận chiến lược thì đừng ép vào khuôn này — `checks.py` sẽ không đo được gì
  và template sẽ nói thẳng `not_measured` thay vì bịa điểm.

## Test

```bash
python3 -m unittest discover -s templates/multi-agent-loop/tests -v   # 46 test
```

- `tests/test_checks.py` (21) — mỗi test là một bẫy: 0 giả, 0 có evidence bịa, null thiếu reason,
  trùng lặp, throughput 643 record/0.23s, mẫu nhỏ phải `null`, drift ngày, báo cáo cũ, ghi sai cửa I/O.
- `tests/test_loop.py` (25) — máy trạng thái của vòng planner→executor→verifier→human.
