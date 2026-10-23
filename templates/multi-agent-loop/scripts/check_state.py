#!/usr/bin/env python3
"""Kiểm `state/state.json` có vi phạm luật "state trên file / không 0 giả" không.

    python3 scripts/check_state.py --state state/state.json
    python3 scripts/check_state.py --state state/state.json --json

Dùng trong CI và trong scaffolder: sinh loop xong phải chứng minh state khởi tạo sạch,
không có số 0 bịa cho những thứ chưa từng chạy.

Mã thoát: 0 OK · 2 lỗi dùng · 4 state vi phạm luật.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_metric(node: Any) -> bool:
    return isinstance(node, dict) and "value" in node


def walk(node: Any, path: str = "$") -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if is_metric(node):
        found.append((path, node))
        return found
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(walk(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(walk(value, f"{path}[{index}]"))
    return found


def check(state: dict[str, Any], today: str) -> list[str]:
    problems: list[str] = []

    day = str(state.get("system_day") or "")
    if not DAY_RE.match(day):
        problems.append(f"system_day '{day}' không phải YYYY-MM-DD")
    elif day > today:
        problems.append(f"system_day {day} ở tương lai so với UTC {today}")
    if str(state.get("timezone") or "") != "UTC":
        problems.append("timezone phải là 'UTC' — hạn mức theo ngày chỉ đúng khi thống nhất UTC")

    roles = state.get("roles") or {}
    for role in ("planner", "executor", "verifier", "human"):
        if not str(roles.get(role) or "").strip():
            problems.append(f"thiếu tên vai {role}")
    if roles.get("executor") and roles.get("executor") == roles.get("verifier"):
        problems.append("executor và verifier trùng nhau — executor sẽ tự chấm bài mình")

    for path, metric in walk(state):
        value = metric.get("value")
        if value is None:
            if not str(metric.get("reason") or "").strip():
                problems.append(f"{path}: null nhưng thiếu reason")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if value == 0:
            if not str(metric.get("measured_by") or "").strip():
                problems.append(f"{path}: 0 nhưng thiếu measured_by (0 giả)")
            if not str(metric.get("evidence") or "").strip():
                problems.append(f"{path}: 0 nhưng thiếu evidence (0 giả)")

    task = state.get("task") or {}
    if not str(task.get("slug") or "").strip():
        problems.append("thiếu task.slug")
    if not (task.get("done_criteria") or []):
        problems.append("thiếu task.done_criteria — 'xong' là gì phải nằm trên file")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_state.py", description="Kiểm state không có 0 giả")
    parser.add_argument("--state", required=True)
    parser.add_argument("--json", action="store_true", help="In kết quả dạng JSON")
    args = parser.parse_args(argv)

    path = Path(args.state)
    if not path.exists():
        print(f"❌ không thấy {path}", file=sys.stderr)
        return 2
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"❌ {path} không phải JSON: {exc}", file=sys.stderr)
        return 4
    if not isinstance(state, dict):
        print(f"❌ {path} phải là object", file=sys.stderr)
        return 4

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    problems = check(state, today)

    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems, "system_day": today},
                         ensure_ascii=False, indent=2))
    elif problems:
        print(f"❌ state vi phạm {len(problems)} điểm:", file=sys.stderr)
        for problem in problems:
            print(f"   • {problem}", file=sys.stderr)
    else:
        print(f"✅ state sạch: system_day={state.get('system_day')}, "
              f"{len(walk(state))} metric, không có 0 giả")
    return 0 if not problems else 4


if __name__ == "__main__":
    sys.exit(main())
