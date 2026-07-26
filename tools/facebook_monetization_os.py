#!/usr/bin/env python3
"""Offline planner for Quang Quý AI's Facebook Lead & Monetization OS.

The tool deliberately makes no network/API calls. It validates the declared
integration state and produces a deterministic daily production brief. A
separate, officially authenticated connector is required before any action can
be published or analytics can be synced.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = REPO_ROOT / "ops" / "facebook-monetization"
STATE_PATH = OPS_DIR / "state.json"
BACKLOG_PATH = OPS_DIR / "content-backlog.json"
READY_STATUSES = {"READY_FOR_DRAFT", "APPROVED_FOR_PRODUCTION"}
REQUIRED_STATE_KEYS = {
    "schema_version",
    "brand",
    "website",
    "primary_goal",
    "secondary_goal",
    "execution_mode",
    "daily_target",
    "integrations",
    "gates",
    "safeguards",
}
REQUIRED_CONTENT_KEYS = {
    "id",
    "status",
    "channel",
    "audience",
    "hypothesis",
    "hook",
    "script_outline",
    "visual_direction",
    "primary_kpi",
    "cta",
    "originality_requirements",
}


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Không tìm thấy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON không hợp lệ tại {path}: {exc}") from exc


def validate_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_STATE_KEYS - state.keys()
    if missing:
        errors.append("state.json thiếu trường: " + ", ".join(sorted(missing)))

    if state.get("execution_mode") not in {"DRAFT_ONLY", "READY_FOR_OFFICIAL_API"}:
        errors.append("execution_mode phải là DRAFT_ONLY hoặc READY_FOR_OFFICIAL_API")

    if not isinstance(state.get("daily_target"), dict):
        errors.append("daily_target phải là object")
    elif not isinstance(state["daily_target"].get("original_reels"), int):
        errors.append("daily_target.original_reels phải là số nguyên")

    if state.get("execution_mode") == "DRAFT_ONLY":
        blocked = set(state.get("safeguards", {}).get("external_actions_disabled", []))
        if "publish_to_facebook" not in blocked:
            errors.append("DRAFT_ONLY phải khóa publish_to_facebook")

    return errors


def validate_backlog(backlog: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(backlog, list) or not backlog:
        return ["content-backlog.json phải là danh sách không rỗng"]

    ids: set[str] = set()
    for index, item in enumerate(backlog, start=1):
        if not isinstance(item, dict):
            errors.append(f"Nội dung #{index} phải là object")
            continue
        missing = REQUIRED_CONTENT_KEYS - item.keys()
        if missing:
            errors.append(
                f"Nội dung #{index} thiếu trường: " + ", ".join(sorted(missing))
            )
        content_id = item.get("id")
        if content_id in ids:
            errors.append(f"Trùng content id: {content_id}")
        if content_id:
            ids.add(content_id)
        if item.get("channel") != "facebook_reel":
            errors.append(f"{content_id}: V1 chỉ chấp nhận facebook_reel")
        outline = item.get("script_outline")
        if not isinstance(outline, list) or len(outline) < 3:
            errors.append(f"{content_id}: script_outline cần ít nhất 3 bước")
        if not item.get("originality_requirements"):
            errors.append(f"{content_id}: phải có điều kiện tính nguyên bản")

    return errors


def validate(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    state = read_json(root / "ops" / "facebook-monetization" / "state.json")
    backlog = read_json(root / "ops" / "facebook-monetization" / "content-backlog.json")
    if not isinstance(state, dict):
        raise ValueError("state.json phải là object")
    errors = validate_state(state) + validate_backlog(backlog)
    return state, backlog, errors


def select_items(backlog: list[dict[str, Any]], run_date: date, limit: int) -> list[dict[str, Any]]:
    candidates = [item for item in backlog if item.get("status") in READY_STATUSES]
    if not candidates or limit <= 0:
        return []
    start = run_date.toordinal() % len(candidates)
    return [candidates[(start + offset) % len(candidates)] for offset in range(min(limit, len(candidates)))]


def build_daily_plan(
    state: dict[str, Any], backlog: list[dict[str, Any]], run_date: date
) -> dict[str, Any]:
    limit = state["daily_target"]["original_reels"]
    items = select_items(backlog, run_date, limit)
    publish_blocked = state["execution_mode"] != "READY_FOR_OFFICIAL_API"
    return {
        "run_date": run_date.isoformat(),
        "brand": state["brand"],
        "website": state["website"],
        "primary_goal": state["primary_goal"],
        "execution_mode": state["execution_mode"],
        "publish_allowed": not publish_blocked,
        "publish_block_reason": (
            None
            if not publish_blocked
            else "Chưa có kết nối Publish API chính thức được xác minh; chỉ tạo bản nháp."
        ),
        "items": items,
        "measurement_windows": ["24h", "72h"],
    }


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# Daily brief — {plan['run_date']}",
        "",
        f"- Thương hiệu: {plan['brand']}",
        f"- Mục tiêu chính: {plan['primary_goal']}",
        f"- Website/CTA đích: {plan['website']}",
        f"- Chế độ chạy: `{plan['execution_mode']}`",
    ]
    if not plan["publish_allowed"]:
        lines.extend(["", f"> Khóa xuất bản: {plan['publish_block_reason']}"])

    for ordinal, item in enumerate(plan["items"], start=1):
        lines.extend(
            [
                "",
                f"## {ordinal}. {item['id']} — {item['audience']}",
                "",
                f"- Giả thuyết: {item['hypothesis']}",
                f"- Hook: {item['hook']}",
                f"- Hình thức: {item['visual_direction']}",
                f"- CTA: {item['cta']}",
                f"- KPI chính: `{item['primary_kpi']}`",
                f"- KPI phụ: {', '.join(item.get('secondary_kpis', []))}",
                "- Dàn ý:",
            ]
        )
        lines.extend(f"  {step_number}. {step}" for step_number, step in enumerate(item["script_outline"], start=1))
        lines.append("- Kiểm tra nguyên bản: " + "; ".join(item["originality_requirements"]))

    lines.extend(
        [
            "",
            "## Checklist ghi nhận",
            "",
            "- [ ] Lưu file nguồn vào Drive sau khi kết nối Drive chính thức.",
            "- [ ] Ghi content ID, link asset, hook, CTA, giờ đăng vào Notion sau khi integration được chia sẻ.",
            "- [ ] Chỉ đăng qua connector API chính thức khi `publish_allowed = true`.",
            "- [ ] Lấy KPI sau 24h và 72h; không kết luận từ cảm nhận của AI.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Thư mục gốc repository")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Kiểm tra state và backlog")
    daily = subparsers.add_parser("daily-brief", help="Tạo brief sản xuất hằng ngày")
    daily.add_argument("--date", dest="run_date", default=date.today().isoformat(), help="YYYY-MM-DD")
    daily.add_argument("--output", type=Path, help="File markdown đích; mặc định in ra stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        state, backlog, errors = validate(root)
    except ValueError as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("LỖI kiểm tra:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if args.command == "validate":
        print(
            "OK: state/backlog hợp lệ; "
            f"chế độ={state['execution_mode']}; "
            f"reels/ngày={state['daily_target']['original_reels']}; "
            f"backlog={len(backlog)}"
        )
        return 0

    try:
        run_date = date.fromisoformat(args.run_date)
    except ValueError:
        print("LỖI: --date phải theo dạng YYYY-MM-DD", file=sys.stderr)
        return 2

    brief = render_markdown(build_daily_plan(state, backlog, run_date))
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(brief, encoding="utf-8")
        print(f"Đã tạo brief: {output}")
    else:
        print(brief, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
