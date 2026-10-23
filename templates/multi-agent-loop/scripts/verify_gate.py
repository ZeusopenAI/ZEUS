#!/usr/bin/env python3
"""Cổng verification: CHẠY LỆNH THẬT rồi mới sinh evidence.

Đây là công cụ duy nhất được phép tạo ra evidence cho `loop_state.py verify`.
Nó luôn thực thi lệnh — không có chế độ "dùng lại log cũ", không có cờ `--reuse`,
vì mục tiêu là verifier phải chạy lại từ đầu sau mỗi lần executor submit.

    python3 verify_gate.py run --dir .ai/loop --label "pytest" -- pytest -q
    python3 verify_gate.py run --dir .ai/loop --label "build"  -- npm run build
    python3 verify_gate.py show --dir .ai/loop

Mỗi lần chạy sinh `evidence/ev_<số>.json`:

    {
      "evidence_id": "ev_0001",
      "label": "pytest",
      "command": "pytest -q",
      "argv": ["pytest", "-q"],
      "exit_code": 0,
      "started_at": "2026-10-23T19:00:00Z",
      "finished_at": "2026-10-23T19:00:12Z",
      "duration_ms": 12000,
      "stdout_sha256": "…",
      "stdout_tail": "…",
      "cwd": "/repo"
    }

`started_at` là mốc để `loop_state.py` phân biệt evidence mới với evidence cũ —
nhờ vậy không thể tái sử dụng báo cáo của lần chạy trước.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

TAIL_CHARS = 4000


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def next_id(evidence_dir: Path) -> str:
    existing = sorted(evidence_dir.glob("ev_*.json")) if evidence_dir.exists() else []
    numbers = []
    for path in existing:
        try:
            numbers.append(int(path.stem.split("_")[1]))
        except (IndexError, ValueError):
            continue
    return f"ev_{(max(numbers) + 1 if numbers else 1):04d}"


def cmd_run(args: argparse.Namespace) -> int:
    argv = list(args.command)
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        print("❌ thiếu lệnh. Ví dụ: verify_gate.py run --dir .ai/loop --label test -- pytest -q",
              file=sys.stderr)
        return 2

    evidence_dir = Path(args.dir) / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_id = next_id(evidence_dir)

    started = now()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            cwd=args.cwd or None,
        )
        exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        timed_out = False
    except FileNotFoundError:
        exit_code, stdout, stderr, timed_out = 127, "", f"command not found: {argv[0]}", False
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = f"timeout sau {args.timeout}s"
        timed_out = True
    finished = now()

    record = {
        "evidence_id": evidence_id,
        "label": args.label,
        "command": " ".join(shlex.quote(part) for part in argv),
        "argv": argv,
        "exit_code": exit_code,
        "started_at": iso(started),
        "finished_at": iso(finished),
        "duration_ms": int((finished - started).total_seconds() * 1000),
        "timed_out": timed_out,
        "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
        "stdout_tail": stdout[-TAIL_CHARS:],
        "stderr_tail": stderr[-TAIL_CHARS:],
        "cwd": str(Path(args.cwd).resolve()) if args.cwd else str(Path.cwd()),
    }
    path = evidence_dir / f"{evidence_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    icon = "✅" if exit_code == 0 else "❌"
    print(f"{icon} {evidence_id} [{args.label}] exit={exit_code} "
          f"({record['duration_ms']} ms) → {path}")
    if exit_code != 0 and args.show_output:
        tail = (stdout + stderr)[-2000:]
        if tail.strip():
            print("--- output cuối ---")
            print(tail)
    if args.print_id:
        print(evidence_id)
    return 0 if (exit_code == 0 or args.allow_failure) else exit_code


def cmd_show(args: argparse.Namespace) -> int:
    evidence_dir = Path(args.dir) / "evidence"
    items = sorted(evidence_dir.glob("ev_*.json"))
    if not items:
        print("(chưa có evidence nào)")
        return 0
    print(f"{len(items)} evidence trong {evidence_dir}:")
    for path in items:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  {path.name}: JSON hỏng")
            continue
        mark = "ok  " if int(data.get("exit_code", 1)) == 0 else "FAIL"
        print(f"  {mark} {data.get('evidence_id')} [{data.get('label')}] "
              f"{data.get('started_at')} — {data.get('command')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verify_gate.py", description="Chạy lệnh thật để sinh evidence")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Chạy một lệnh và ghi evidence")
    run.add_argument("--dir", required=True, help="Thư mục loop (evidence/ nằm trong đây)")
    run.add_argument("--label", required=True, help="Nhãn ngắn, vd 'pytest'")
    run.add_argument("--timeout", type=int, default=1800)
    run.add_argument("--cwd", default="")
    run.add_argument("--allow-failure", action="store_true",
                     help="Trả mã 0 kể cả khi lệnh fail (evidence vẫn ghi exit_code thật)")
    run.add_argument("--show-output", action="store_true")
    run.add_argument("--print-id", action="store_true")
    run.add_argument("command", nargs=argparse.REMAINDER, help="-- <lệnh> [tham số...]")
    run.set_defaults(func=cmd_run)

    show = sub.add_parser("show", help="Liệt kê evidence")
    show.add_argument("--dir", required=True)
    show.set_defaults(func=cmd_show)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
