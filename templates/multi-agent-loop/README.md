# Multi-Agent Loop — template 5 vai

Template tối thiểu, chạy được ngay, để nhiều AI (hoặc AI + CI + người) phối hợp mà **không tự khen nhau**.
Không phụ thuộc framework, không cần server: chỉ Python 3.11+ và git.

```
Planner ──plan──▶ State(file) ──▶ Executor ──submit──▶ State
                                     ▲                    │
                                     │                    ▼
                                  retry            Verifier (chạy lại từ đầu)
                                                          │
                                                          ▼
                                                       Human ──accept/reject──▶ State
```

| Vai | Làm gì | Không được làm |
|---|---|---|
| **Planner** | Đặt mục tiêu, cắt bước, viết lệnh kiểm chứng cho **từng** bước | Tự sửa code của executor |
| **Executor** | Làm đúng plan, gửi kết quả kèm metric có nguồn | Tự chấm điểm, tự chuyển sang `accepted` |
| **Verifier** | Chạy lại lệnh từ đầu, sinh evidence mới | Đọc báo cáo cũ của executor để kết luận |
| **State** | `STATE.json` + `journal.jsonl` (append-only) | Nằm trong prompt / trong đầu model |
| **Human** | `accept` / `reject` có lý do | Bị thay bằng "agent tự duyệt" |

## 5 luật được CODE cưỡng chế

| Luật | Cơ chế |
|---|---|
| State lưu trên file, không trong prompt | Mọi chuyển pha ghi `STATE.json` nguyên tử + 1 dòng `journal.jsonl` |
| Executor không tự chấm | `init` từ chối nếu executor ≡ verifier; `verify` từ chối nếu người chấm là executor hoặc chính người vừa submit |
| Verification chạy lại từ đầu | `verify` chỉ nhận evidence có `started_at >= submitted_at`; evidence cũ bị đếm vào `ignored_stale_evidence` |
| `null` + reason khi chưa đo được | Metric `{"value": null}` thiếu `reason` ⇒ từ chối |
| Không ghi 0 giả | Metric `0` bắt buộc có `measured_by` + `evidence` trỏ tới lệnh đã chạy thật |

Kết quả kiểm chứng do **lệnh** quyết định, không do lời khai: verifier muốn nói `pass` mà evidence có
`exit_code != 0` thì bị từ chối (`--result pass` ≠ kết quả suy ra từ evidence).

Executor cũng được dùng `verify_gate.py` để tự chạy lệnh và lấy `evidence_id` chứng minh cho metric
của mình. Những file đó có `started_at` **trước** `submit` nên verifier sẽ tự động bỏ qua —
chúng là provenance cho số liệu, không phải bằng chứng kiểm chứng.

## Quickstart (60 giây)

```bash
cd templates/multi-agent-loop

# 1) Planner mở loop
python3 scripts/loop_state.py init --dir .loop --slug "va-loi-sync" \
  --goal "Đồng bộ skill không mất dữ liệu" \
  --planner hermes --executor arena --verifier ci --human operator

# 2) Planner viết plan: mỗi bước BẮT BUỘC có "→ lệnh kiểm chứng"
cat > plan.md <<'EOF'
1. Sửa scripts/hermes-sync.sh → bash -n scripts/hermes-sync.sh
2. Chạy doctor → bash scripts/hermes-doctor.sh --quiet
3. Unit test → python3 -m unittest discover -s scripts/tests -q
EOF
python3 scripts/loop_state.py plan --dir .loop --by hermes --file plan.md

# 3) Executor làm việc rồi submit (metric do CHÍNH nó đo cũng phải có evidence)
cat > metrics.json <<'EOF'
{
  "tests_passed": {"value": 24, "measured_by": "arena", "evidence": "ev_0001"},
  "latency_p95_ms": {"value": null, "reason": "chưa có môi trường đo tải"}
}
EOF
python3 scripts/loop_state.py submit --dir .loop --by arena \
  --summary "Sửa sync, thêm test" --metrics-json metrics.json

# 4) Verifier chạy lại từ đầu — luôn tạo evidence MỚI
python3 scripts/verify_gate.py run --dir .loop --label "unit" -- python3 -m unittest discover -s scripts/tests -q
python3 scripts/loop_state.py verify --dir .loop --by ci --evidence-glob ".loop/evidence/ev_*.json"

# 5) Human quyết định
python3 scripts/loop_state.py decide --dir .loop --by operator --accept --note "ổn, merge"
python3 scripts/loop_state.py status --dir .loop
```

## Nội dung

```
templates/multi-agent-loop/
├── CONTRACT.md              # đặc tả chuẩn (MUST / MUST NOT), bảng chuyển pha
├── state.schema.json        # JSON Schema cho STATE.json
├── prompts/                 # prompt mẫu cho từng vai (dán vào agent nào cũng được)
│   ├── planner.md
│   ├── executor.md
│   ├── verifier.md
│   └── human.md
├── scripts/
│   ├── loop_state.py        # máy trạng thái + cưỡng chế luật
│   └── verify_gate.py       # chạy lệnh thật → sinh evidence
├── examples/STATE.example.json
└── tests/test_loop.py       # 25 test, mỗi test = 1 luật
```

Chạy test: `python3 -m unittest discover -s templates/multi-agent-loop/tests -v`

## Gắn vào repo khác

```bash
# copy nguyên thư mục rồi bỏ .loop/ (dữ liệu chạy) trước khi commit
cp -r templates/multi-agent-loop /duong/dan/repo-moi/loop
cd /duong/dan/repo-moi/loop && rm -rf .loop
printf '\n# dữ liệu chạy của loop\n.loop/\n' >> .gitignore
```

Hoặc clone repo này rồi `git subtree`/`cp` — template không có import nội bộ, copy là chạy.

## Áp vào ZEUS

| Vai | Ai |
|---|---|
| Planner | **Hermes** (workflow `hermes-owner-loop.yml` ban hành mệnh lệnh) |
| Executor | **Arena agent / Codespaces** (phiên làm việc) |
| Verifier | **CI** (`hermes-owner-protocol-ci.yml`, `hermes-runtime-ci.yml`) hoặc một agent khác |
| State | `.ai/handoff/STATE.json` + `OUTBOX.md` của Hermes Owner Protocol |
| Human | **Operator Nguyễn Quang Quý** |

Template này là bản tổng quát hoá của Hermes Owner Protocol: cùng luật "chủ ra lệnh — thợ thi hành —
trọng tài chạy lại từ đầu", nhưng dùng được cho repo bất kỳ và gắn trực tiếp với CI.

## Giới hạn (nói thẳng)

- **Không chống được agent nói dối hoàn toàn.** Nếu executor tự tay viết file `ev_*.json` giả thay vì
  chạy `verify_gate.py`, state sẽ tin. Chặn thật bằng cách: chỉ cho verifier chạy trong CI sạch
  (`evidence` sinh trên runner), hoặc ký evidence bằng key CI. Template giữ đơn giản có chủ ý.
- **Không phải orchestrator chạy nền.** Nó là *hợp đồng + máy trạng thái*; ai gọi từng bước là việc
  của bạn (người, cron, hay workflow).
- **Không tự sửa code.** Mọi thay đổi file do executor làm; template chỉ ghi nhận và chặn.
- `journal.jsonl` là append-only ở mức quy ước — ai có quyền ghi file vẫn sửa được. Muốn bất biến
  thật thì đẩy journal lên nơi chỉ-ghi (S3 object-lock, git tag ký, …).
