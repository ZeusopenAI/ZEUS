#!/usr/bin/env python3
"""Scaffolder: sinh một loop mới từ preset (Planner/Executor/Verifier/State/Human).

    python3 scripts/new_loop.py list
    python3 scripts/new_loop.py create --preset batch-extract --dir ../loc-khach-hang \\
        --slug "loc-danh-ba" --goal "Trích xuất tên/công ty/email từ 1000 dòng chat" \\
        --owner quangquy

Loop mới là một repo (hoặc thư mục) tự chứa: spec + state + input/output/verify/log/reports
+ workflow verify + bộ test. Không import gì từ template gốc — copy là chạy.

Mặc định scaffolder **tự kiểm chứng** loop vừa sinh: chép example vào một bản tạm, chạy
`spec/checks.py run` và đòi kết quả `pass`. Nếu không pass, nó xoá thư mục vừa tạo và báo lỗi —
không giao cho bạn một loop hỏng. Dùng `--no-verify` để bỏ qua (không khuyến khích).

Mã thoát: 0 OK · 2 lỗi dùng · 4 loop tự kiểm chứng không pass · 5 thư mục đích đã có file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
PRESETS_DIR = TEMPLATE_ROOT / "presets"

COPY_ALWAYS = (
    "CONTRACT.md",
    "ARCHITECTURE.md",
    "spec/checks.py",
    "spec/rules.md",
    "spec/state.schema.json",
    "scripts/loop_state.py",
    "scripts/verify_gate.py",
    "scripts/README.md",
    "scripts/new_loop.py",
    "scripts/check_state.py",
    "prompts",
    "tests/test_loop.py",
    ".github/workflows/verify.yml",
    "output/README.md",
    "verify/README.md",
    "reports/README.md",
    "input/README.md",
)

EXIT_OK, EXIT_USAGE, EXIT_SELFTEST, EXIT_EXISTS = 0, 2, 4, 5


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def load_presets() -> dict[str, dict[str, Any]]:
    presets: dict[str, dict[str, Any]] = {}
    if not PRESETS_DIR.exists():
        return presets
    for path in sorted(PRESETS_DIR.iterdir()):
        meta_path = path / "preset.json"
        if not path.is_dir() or not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"⚠ preset {path.name} có preset.json hỏng: {exc}", file=sys.stderr)
            continue
        meta.setdefault("name", path.name)
        presets[meta["name"]] = {**meta, "_dir": path}
    return presets


def cmd_list(args: argparse.Namespace) -> int:
    presets = load_presets()
    if not presets:
        print("❌ không tìm thấy preset nào trong", PRESETS_DIR, file=sys.stderr)
        return EXIT_USAGE
    width = max(len(name) for name in presets)
    print(f"{'PRESET'.ljust(width)}  TIÊU ĐỀ / DÙNG CHO")
    for name, meta in presets.items():
        print(f"{name.ljust(width)}  {meta.get('title', '')}")
        print(f"{''.ljust(width)}  {meta.get('description', '')}")
    print()
    print("Tạo loop mới:  python3 scripts/new_loop.py create --preset <tên> --dir <thư mục>")
    return EXIT_OK


def build_state(meta: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    now = utc_now()
    preset_state = meta.get("state") or {}
    quota = preset_state.get("quota") or {}
    max_records = int(quota.get("max_records_per_day") or 500)
    return {
        "schema": "multi-agent-loop-state/1",
        "system_day": now.strftime("%Y-%m-%d"),
        "timezone": "UTC",
        "task": {
            "slug": args.slug,
            "goal": args.goal or meta.get("description", ""),
            "preset": meta.get("name"),
            "done_criteria": preset_state.get("done_criteria") or [
                "mọi record khớp spec/schema.json",
                "không có metric 0 nào thiếu evidence",
                "checks.py overall = pass",
            ],
            "created_at": iso(now),
        },
        "quota": {
            "max_records_per_day": max_records,
            "used_records_today": {
                "value": None,
                "reason": "loop mới khởi tạo, chưa có lần chạy nào — không ghi 0 giả",
            },
            "remaining_records": {
                "value": None,
                "reason": "chưa đo được vì chưa có lần chạy nào",
            },
            "reset_at": (now.replace(hour=0, minute=0, second=0) + dt.timedelta(days=1)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        },
        "progress": {"done": [], "in_progress": None, "blocked": None},
        "roles": {
            "planner": args.planner,
            "executor": args.executor,
            "verifier": args.verifier,
            "human": args.owner,
        },
        "counters": {
            "records_processed": {
                "value": None,
                "reason": "chưa chạy lần nào — số thật sẽ do log/ ghi lại ở lần chạy đầu",
            },
            "records_failed": {"value": None, "reason": "chưa chạy lần nào"},
            "avg_ms_per_record": {"value": None, "reason": "chưa có log xử lý để tính trung bình"},
        },
        "last_verified": None,
        "updated_at": iso(now),
        "updated_by": "new_loop.py",
    }


def build_readme(meta: dict[str, Any], args: argparse.Namespace) -> str:
    return f"""# {args.slug} — loop 5 vai ({meta.get('title', meta.get('name'))})

Sinh từ template `multi-agent-loop` (preset `{meta.get('name')}`) lúc {iso(utc_now())}.

**Mục tiêu:** {args.goal or meta.get('description', '(chưa ghi)')}

## Vai

| Vai | Danh tính | Được ghi |
|---|---|---|
| Planner | `{args.planner}` | `spec/` |
| Executor | `{args.executor}` | `output/`, `log/` |
| Verifier | `{args.verifier}` | `verify/` |
| Human | `{args.owner}` | `reports/`, quyết định |

Verifier **phải khác** Executor. Nếu cùng một model, verify không có giá trị.

## Quy trình một phiên

```bash
# 1) Planner: đọc state, cập nhật spec nếu cần
python3 -c "import json;print(json.load(open('state/state.json'))['task']['done_criteria'])"

# 2) Executor: đọc input → ghi output + log  (chỉ trong output/ và log/)
python3 spec/checks.py ownership --role executor --staged   # tự kiểm cửa I/O trước khi commit

# 3) Verifier: chạy lại từ đầu, sinh báo cáo MỚI (không đọc báo cáo cũ)
python3 spec/checks.py run --report "verify/checks-$(date -u +%Y%m%dT%H%M%SZ).json"
python3 spec/checks.py freshness --report verify/checks-<mốc>.json

# 4) Human: đọc verify/, ghi reports/YYYY-MM-DD.md (kết thúc bằng mục "Ngày mai")
```

## Luật riêng của preset này

{meta.get('owner_note', '')}

Chi tiết: `spec/rules.md` (phần 9), `CONTRACT.md`, `ARCHITECTURE.md`.

## Ví dụ record hợp lệ

`examples/example-output.jsonl` — chép vào `output/` để thử, rồi xoá.

## Kiểm chứng

```bash
python3 -m unittest discover -s tests -v
```

Loop này đã được scaffolder tự chạy `checks.py` trên example và đòi `pass` trước khi giao.
"""


def build_schema_test(meta: dict[str, Any]) -> str:
    """Test riêng của loop: example phải khớp schema, và 0 giả phải bị chặn.

    Test này bắt hai lỗi từng xảy ra thật:
      - validator bỏ qua `additionalProperties` dạng schema ⇒ metric trong map không được kiểm;
      - schema có `minProperties` nhưng bộ kiểm không đọc ⇒ record rỗng vẫn "pass".
    """
    guard = (meta.get("checks") or {}).get("zero_guard_fields") or [
        "score", "grade", "count", "total", "errors", "violation_count",
    ]
    guard_literal = ", ".join(f'"{f}"' for f in guard)
    name = meta.get("name")
    return f'''#!/usr/bin/env python3
"""Test của loop '{name}' — example phải khớp spec/schema.json.

    python3 -m unittest discover -s tests -v

Test này KHÔNG phụ thuộc template gốc: nó dùng chính spec/checks.py của loop này.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("checks", ROOT / "spec" / "checks.py")
checks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checks)  # type: ignore[union-attr]

ZERO_GUARD_FIELDS = [{guard_literal}]


def load_schema() -> dict:
    return json.loads((ROOT / "spec" / "schema.json").read_text(encoding="utf-8"))


def example_records() -> list[dict]:
    path = ROOT / "examples" / "example-output.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ExampleSchemaTest(unittest.TestCase):
    def test_example_output_matches_schema(self) -> None:
        schema = load_schema()
        records = example_records()
        self.assertTrue(records, "thiếu examples/example-output.jsonl")
        for number, record in enumerate(records, 1):
            errors = checks.validate(record, schema, schema)
            self.assertEqual(errors, [], f"dòng {{number}} sai schema: {{errors}}")

    def test_fake_zero_is_detected(self) -> None:
        """0 không có evidence phải bị chặn — ở schema VÀ ở check_fake_zero."""
        schema = load_schema()
        record = copy.deepcopy(example_records()[0])

        metrics = record.get("metrics") or {{}}
        if metrics:
            key = next(iter(metrics))
            metrics[key] = {{"value": 0, "measured_by": "ai do"}}  # 0 giả: không evidence
            record["metrics"] = metrics
            where = f"metrics.{{key}}"
        else:  # loop không dùng metrics: bơm 0 vào trường số cấp record
            field = ZERO_GUARD_FIELDS[0]
            record[field] = 0
            record.pop("measured_by", None)
            record.pop("evidence", None)
            where = field

        self.assertTrue(
            checks.validate(record, schema, schema),
            f"schema phải chặn 0 thiếu evidence ở {{where}}",
        )

        result = checks.check_fake_zero(
            [dict(record, _file="examples/example-output.jsonl")],
            {{"root": ROOT, "log_dir": ROOT / "log", "zero_guard_fields": ZERO_GUARD_FIELDS}},
        )
        self.assertEqual(result["status"], checks.FAIL,
                         f"check_fake_zero phải bắt 0 giả ở {{where}}: {{result['problems']}}")

    def test_zero_with_real_evidence_passes(self) -> None:
        """0 hợp lệ (có measured_by + evidence trỏ log thật) phải qua — tránh chặn nhầm."""
        schema = load_schema()
        record = copy.deepcopy(example_records()[0])
        record["metrics"] = {{"errors": {{"value": 0, "measured_by": "ci",
                                       "evidence": "log/bootstrap.jsonl#L1"}}}}
        for field in ZERO_GUARD_FIELDS:
            record.pop(field, None)
        errors = checks.validate(record, schema, schema)
        self.assertEqual([e for e in errors if "errors" in e], [], errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''


def build_workflow(meta: dict[str, Any]) -> str:
    zero_fields = ",".join((meta.get("checks") or {}).get("zero_guard_fields")
                           or ["score", "grade", "count", "total", "errors", "violation_count"])
    max_dup = (meta.get("checks") or {}).get("max_duplicate_rate")
    max_rate = (meta.get("checks") or {}).get("max_records_per_second")
    extra = ""
    if max_dup is not None:
        extra += f" \\\n            --max-duplicate-rate {max_dup}"
    if max_rate is not None:
        extra += f" \\\n            --max-records-per-second {max_rate}"
    return f"""name: Verify loop

# Verifier chạy trên runner sạch — executor không sửa được log của runner này.
on:
  pull_request:
    paths:
      - "output/**"
      - "input/**"
      - "spec/**"
      - "state/**"
      - "log/**"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262  # v4
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5
        with:
          python-version: "3.12"

      - name: Kiểm ranh giới ghi file (executor chỉ được output/ + log/)
        run: python3 spec/checks.py ownership --role executor --base "origin/${{{{ github.base_ref || 'main' }}}}"

      - name: Chạy bộ kiểm
        run: |
          STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
          python3 spec/checks.py run --root . \\
            --zero-guard-fields "{zero_fields}"{extra} \\
            --report "verify/checks-${{STAMP}}.json" --by ci-verifier | tee verify-output.txt

      - name: Unit test
        run: python3 -m unittest discover -s tests -v

      - name: Lưu báo cáo
        if: always()
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02  # v4
        with:
          name: verify-report
          path: |
            verify/*.json
            verify-output.txt
          if-no-files-found: warn
"""


def cmd_create(args: argparse.Namespace) -> int:
    presets = load_presets()
    meta = presets.get(args.preset)
    if meta is None:
        print(f"❌ preset '{args.preset}' không có. Có: {', '.join(presets) or '(trống)'}", file=sys.stderr)
        return EXIT_USAGE

    target = Path(args.dir).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        if not args.force:
            print(f"❌ {target} đã có file. Dùng thư mục trống hoặc --force.", file=sys.stderr)
            return EXIT_EXISTS
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)
    for rel in COPY_ALWAYS:
        src = TEMPLATE_ROOT / rel
        dst = target / rel
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, dst)

    # spec: schema + rules của preset
    preset_dir: Path = meta["_dir"]
    shutil.copy2(preset_dir / "schema.json", target / "spec" / "schema.json")
    append = preset_dir / "rules.append.md"
    if append.exists():
        rules = target / "spec" / "rules.md"
        rules.write_text(
            rules.read_text(encoding="utf-8").rstrip("\n") + "\n" + append.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    # state + input/output mẫu
    (target / "state").mkdir(exist_ok=True)
    (target / "state" / "state.json").write_text(
        json.dumps(build_state(meta, args), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (target / "input").mkdir(exist_ok=True)
    (target / "input" / "raw.example.jsonl").write_text(
        '{"id": "in-0001", "text": "dữ liệu gốc mẫu — thay bằng dữ liệu thật"}\n',
        encoding="utf-8",
    )
    (target / "examples").mkdir(exist_ok=True)
    example = preset_dir / "example-output.jsonl"
    if example.exists():
        shutil.copy2(example, target / "examples" / "example-output.jsonl")
    (target / "log").mkdir(exist_ok=True)

    (target / "tests").mkdir(exist_ok=True)
    (target / "tests" / "test_schema_examples.py").write_text(
        build_schema_test(meta), encoding="utf-8"
    )
    (target / "README.md").write_text(build_readme(meta, args), encoding="utf-8")
    (target / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (target / ".github" / "workflows" / "verify.yml").write_text(
        build_workflow(meta), encoding="utf-8"
    )
    (target / ".gitignore").write_text(
        "verify/*.json\n!verify/README.md\noutput/*.jsonl\n!output/README.md\n"
        "input/*.jsonl\n!input/raw.example.jsonl\nlog/*.jsonl\n__pycache__/\n*.pyc\n",
        encoding="utf-8",
    )

    print(f"✅ Tạo loop '{meta.get('name')}' tại {target}")
    print(f"   Vai: planner={args.planner} · executor={args.executor} "
          f"· verifier={args.verifier} · human={args.owner}")

    if not args.no_verify:
        code = self_verify(target, meta, args)
        if code != EXIT_OK:
            shutil.rmtree(target, ignore_errors=True)
            print("❌ Tự kiểm chứng thất bại → đã xoá thư mục vừa tạo, không giao loop hỏng.",
                  file=sys.stderr)
            return code
        print("   ✅ Tự kiểm chứng: checks.py chạy trên example → pass")
    print()
    print("Bước tiếp theo:")
    print(f"   cd {target}")
    print("   cp examples/example-output.jsonl output/batch-0001.jsonl   # thử nhanh")
    print("   python3 spec/checks.py run --report \"verify/checks-$(date -u +%Y%m%dT%H%M%SZ).json\"")
    return EXIT_OK


def self_verify(target: Path, meta: dict[str, Any], args: argparse.Namespace) -> int:
    """Chạy checks.py trên example trong một bản sao tạm — không để lại rác trong loop."""
    example = target / "examples" / "example-output.jsonl"
    if not example.exists():
        print("⚠ preset không có example-output.jsonl → bỏ qua tự kiểm chứng", file=sys.stderr)
        return EXIT_OK
    state_check = subprocess.run(
        [sys.executable, str(target / "scripts" / "check_state.py"),
         "--state", str(target / "state" / "state.json")],
        capture_output=True, text=True, timeout=60,
    )
    if state_check.returncode != 0:
        print("   — state không hợp lệ —", file=sys.stderr)
        print((state_check.stdout + state_check.stderr).strip(), file=sys.stderr)
        return EXIT_SELFTEST

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp) / "loop"
        shutil.copytree(target, sandbox)
        (sandbox / "output").mkdir(exist_ok=True)
        shutil.copy2(example, sandbox / "output" / "batch-0001.jsonl")
        (sandbox / "log").mkdir(exist_ok=True)
        # Log mẫu để 0 có thể trỏ tới evidence có thật (đúng luật "không ghi 0 giả").
        (sandbox / "log" / "run-0001.jsonl").write_text(
            json.dumps({
                "at": iso(utc_now()),
                "started_at": iso(utc_now() - dt.timedelta(seconds=12)),
                "finished_at": iso(utc_now()),
                "records": 3,
                "by": args.executor,
            }) + "\n",
            encoding="utf-8",
        )
        checks = (meta.get("checks") or {})
        cmd = [
            sys.executable, str(sandbox / "spec" / "checks.py"), "run",
            "--root", str(sandbox),
            "--report", str(sandbox / "verify" / "selftest.json"),
            "--by", "scaffolder-selftest",
        ]
        zero_fields = checks.get("zero_guard_fields")
        if zero_fields:
            cmd += ["--zero-guard-fields", ",".join(zero_fields)]
        if checks.get("max_duplicate_rate") is not None:
            cmd += ["--max-duplicate-rate", str(checks["max_duplicate_rate"])]
        if checks.get("max_records_per_second") is not None:
            cmd += ["--max-records-per-second", str(checks["max_records_per_second"])]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print("   — tự kiểm chứng —")
        for line in (result.stdout or "").strip().splitlines():
            print("   " + line)
        if result.returncode != 0:
            print(result.stderr.strip(), file=sys.stderr)
            return EXIT_SELFTEST
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="new_loop.py", description="Sinh loop 5 vai từ preset")
    sub = parser.add_subparsers(dest="command", required=True)

    listing = sub.add_parser("list", help="Liệt kê preset")
    listing.set_defaults(func=cmd_list)

    create = sub.add_parser("create", help="Tạo loop mới")
    create.add_argument("--preset", required=True)
    create.add_argument("--dir", required=True, help="Thư mục đích (nên trống)")
    create.add_argument("--slug", required=True, help="Tên việc, vd loc-danh-ba")
    create.add_argument("--goal", default="")
    create.add_argument("--owner", default="human", help="Vai Human (người quyết định)")
    create.add_argument("--planner", default="planner")
    create.add_argument("--executor", default="executor")
    create.add_argument("--verifier", default="verifier")
    create.add_argument("--force", action="store_true", help="Ghi đè thư mục đích")
    create.add_argument("--no-verify", action="store_true", help="Bỏ qua tự kiểm chứng")
    create.set_defaults(func=cmd_create)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
