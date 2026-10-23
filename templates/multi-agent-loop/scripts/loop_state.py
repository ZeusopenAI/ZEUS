#!/usr/bin/env python3
"""Multi-Agent Loop — máy trạng thái lưu trên FILE (stdlib, không phụ thuộc mạng).

Mô hình 5 vai: **Planner / Executor / Verifier / State / Human**.

Nguyên tắc bất biến (được CODE cưỡng chế, không chỉ là lời khuyên):

1. **State trên file** — mọi thứ nằm trong `STATE.json` + `journal.jsonl` (append-only).
   Không có trạng thái ẩn trong prompt, trong context model, hay trong đầu agent.
2. **Executor không tự chấm** — `submit` bị từ chối nếu người gửi chính là verifier;
   `verify` bị từ chối nếu người chấm là executor hoặc chính người vừa submit.
3. **Verification chạy lại từ đầu** — chỉ evidence có `started_at >= submitted_at` mới
   được tính; evidence cũ bị loại bỏ tự động, không đọc báo cáo cũ của executor.
4. **null + reason khi chưa đo được** — metric chưa đo phải là `{"value": null,
   "reason": "..."}`. `null` không kèm lý do bị từ chối.
5. **Không ghi 0 giả** — giá trị `0` bắt buộc có `evidence` trỏ tới một command đã chạy
   thật, exit code 0, và `measured_by`. Thiếu provenance ⇒ từ chối.
6. **Không tự chuyển pha** — mỗi chuyển pha kiểm tra pha hiện tại; mọi thay đổi ghi journal.

Chuỗi pha:

    (init) → planned → submitted → verified_pass ─┬→ accepted
                          ↑                       └→ rejected
                          └── verified_fail ← retry (attempt mới)

Lệnh:

    loop_state.py init    --dir DIR --slug SLUG --goal "..." \
                          --planner who --executor who --verifier who --human who
    loop_state.py plan    --dir DIR --by PLANNER --file plan.md
    loop_state.py submit  --dir DIR --by EXECUTOR --summary "..." \
                          [--metrics-json metrics.json] [--evidence FILE]...
    loop_state.py verify  --dir DIR --by VERIFIER   [--evidence FILE]...
    loop_state.py decide  --dir DIR --by HUMAN (--accept | --reject) --note "..."
    loop_state.py status  --dir DIR [--json]

Mã thoát: 0 OK · 2 lỗi dùng · 3 sai thứ tự pha · 4 vi phạm nguyên tắc · 5 state hỏng.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "multi-agent-loop/1"
STATE_NAME = "STATE.json"
JOURNAL_NAME = "journal.jsonl"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PHASE = 3
EXIT_POLICY = 4
EXIT_CORRUPT = 5

PHASES = (
    "planned",
    "submitted",
    "verified_pass",
    "verified_fail",
    "accepted",
    "rejected",
)


class LoopError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Thời gian
# ---------------------------------------------------------------------------

def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_ts(raw: Any) -> dt.datetime | None:
    if not raw:
        return None
    text = str(raw).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        value = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


# ---------------------------------------------------------------------------
# Đọc / ghi state (ghi nguyên tử + journal)
# ---------------------------------------------------------------------------

def state_path(dir_: Path) -> Path:
    return dir_ / STATE_NAME


def journal_path(dir_: Path) -> Path:
    return dir_ / JOURNAL_NAME


def load(dir_: Path) -> dict[str, Any]:
    path = state_path(dir_)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise LoopError(EXIT_USAGE, f"chưa có {path} — chạy `init` trước")
    except json.JSONDecodeError as exc:
        raise LoopError(EXIT_CORRUPT, f"{path} không phải JSON hợp lệ: {exc}")
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise LoopError(EXIT_CORRUPT, f"{path} sai schema (cần {SCHEMA})")
    return data


def save(dir_: Path, state: dict[str, Any], event: dict[str, Any]) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = iso(now())
    state["updated_by"] = event.get("by") or "system"
    tmp = state_path(dir_).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(state_path(dir_))
    entry = {"at": state["updated_at"], **event}
    with journal_path(dir_).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def append_journal(dir_: Path, entry: dict[str, Any]) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    with journal_path(dir_).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": iso(now()), **entry}, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Cưỡng chế nguyên tắc
# ---------------------------------------------------------------------------

def role_of(state: dict[str, Any], who: str) -> str | None:
    for role, name in (state.get("roles") or {}).items():
        if str(name) == who:
            return role
    return None


def require_role(state: dict[str, Any], who: str, expected: str) -> None:
    actual = role_of(state, who)
    if actual != expected:
        found = actual or "không có trong state"
        raise LoopError(
            EXIT_POLICY,
            f"'{who}' là {found}, không phải {expected}. "
            f"Vai trong phiên này: {json.dumps(state.get('roles'), ensure_ascii=False)}",
        )


def require_distinct_roles(roles: dict[str, str]) -> None:
    """Executor và Verifier BẮT BUỘC khác nhau — nếu không, executor tự chấm bài mình.

    Planner/human được phép trùng (một người vừa đặt mục tiêu vừa duyệt).
    """
    for role, name in roles.items():
        if not str(name or "").strip():
            raise LoopError(EXIT_USAGE, f"thiếu tên cho vai {role}")
    if roles["executor"] == roles["verifier"]:
        raise LoopError(
            EXIT_POLICY,
            f"'{roles['executor']}' vừa là executor vừa là verifier. "
            "Hai vai này phải là hai thực thể khác nhau, nếu không kết quả verify vô nghĩa.",
        )


def require_phase(state: dict[str, Any], allowed: tuple[str, ...], action: str) -> None:
    phase = state.get("phase")
    if phase not in allowed:
        raise LoopError(
            EXIT_PHASE,
            f"không thể {action} khi pha là '{phase}'. Pha hợp lệ: {', '.join(allowed)}.",
        )


def current_attempt(state: dict[str, Any]) -> dict[str, Any]:
    attempts = state.get("attempts") or []
    if not attempts:
        raise LoopError(EXIT_PHASE, "chưa có attempt nào — executor phải `submit` trước")
    return attempts[-1]


# ---------------------------------------------------------------------------
# Metric: null + reason, không 0 giả
# ---------------------------------------------------------------------------

def _evidence_ids_from_files(paths: list[str]) -> set[str]:
    ids: set[str] = set()
    for raw in paths:
        try:
            data = json.loads(Path(raw).read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("evidence_id"):
            ids.add(str(data["evidence_id"]))
    return ids


def validate_metric(
    name: str,
    spec: Any,
    attempt: dict[str, Any],
) -> dict[str, Any]:
    """Trả về metric đã chuẩn hoá, hoặc ném LoopError nếu vi phạm."""
    if not isinstance(spec, dict):
        raise LoopError(
            EXIT_POLICY,
            f"metric '{name}' phải là object. Ví dụ hợp lệ: "
            '{"value": 12, "measured_by": "ci", "evidence": "ev_0001"} '
            'hoặc {"value": null, "reason": "chưa có môi trường đo"}.',
        )

    value = spec.get("value", "__missing__")
    if value == "__missing__":
        raise LoopError(
            EXIT_POLICY,
            f"metric '{name}' thiếu khóa 'value'. Không suy diễn giá trị mặc định — "
            "chưa đo thì ghi null kèm reason.",
        )

    # -- Chưa đo được: bắt buộc null + reason ---------------------------------
    if value is None:
        reason = str(spec.get("reason") or "").strip()
        if not reason:
            raise LoopError(
                EXIT_POLICY,
                f"metric '{name}' có value=null nhưng thiếu 'reason'. "
                "Null mà không nói vì sao coi như che giấu việc chưa đo.",
            )
        return {"value": None, "reason": reason}

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LoopError(EXIT_POLICY, f"metric '{name}' có value không phải số/boolean: {value!r}")

    measured_by = str(spec.get("measured_by") or "").strip()
    evidence = str(spec.get("evidence") or "").strip()

    # -- Số thật: phải có người đo + bằng chứng ------------------------------
    if not measured_by:
        raise LoopError(
            EXIT_POLICY,
            f"metric '{name}' có giá trị {value} nhưng thiếu 'measured_by'. "
            "Số không có nguồn gốc là số bịa.",
        )

    # -- Không ghi 0 giả -----------------------------------------------------
    if value == 0:
        if not evidence:
            raise LoopError(
                EXIT_POLICY,
                f"metric '{name}' = 0 nhưng thiếu 'evidence'. "
                "0 phải chứng minh được (lệnh đã chạy, exit 0) — không được ghi 0 giả.",
            )
        known = _evidence_ids_from_files([]) | set(attempt.get("evidence_ids") or [])
        if known and evidence not in known:
            raise LoopError(
                EXIT_POLICY,
                f"metric '{name}' = 0 trỏ tới evidence '{evidence}' không có trong attempt này "
                f"({sorted(known)}). Không chấp nhận bằng chứng không tồn tại.",
            )

    normalized: dict[str, Any] = {"value": value, "measured_by": measured_by}
    if evidence:
        normalized["evidence"] = evidence
    if spec.get("unit"):
        normalized["unit"] = str(spec["unit"])
    if spec.get("note"):
        normalized["note"] = str(spec["note"])
    normalized["at"] = attempt.get("submitted_at") or iso(now())
    return normalized


# ---------------------------------------------------------------------------
# Evidence của verifier
# ---------------------------------------------------------------------------

def load_evidence(paths: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw in paths:
        path = Path(raw)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise LoopError(EXIT_USAGE, f"không thấy evidence {path}")
        except json.JSONDecodeError as exc:
            raise LoopError(EXIT_USAGE, f"evidence {path} không phải JSON: {exc}")
        if not isinstance(data, dict):
            raise LoopError(EXIT_USAGE, f"evidence {path} phải là object")
        for key in ("evidence_id", "command", "exit_code", "started_at", "finished_at"):
            if key not in data:
                raise LoopError(
                    EXIT_POLICY,
                    f"evidence {path} thiếu '{key}'. Evidence phải do `verify_gate.py run` "
                    "sinh ra (có lệnh, exit code, thời điểm chạy).",
                )
        data["_source"] = str(path)
        records.append(data)
    return records


def select_fresh_evidence(evidence: list[dict[str, Any]], submitted_at: str) -> list[dict[str, Any]]:
    submitted = parse_ts(submitted_at)
    if submitted is None:
        raise LoopError(EXIT_CORRUPT, f"attempt có submitted_at không đọc được: {submitted_at!r}")
    fresh: list[dict[str, Any]] = []
    for item in evidence:
        started = parse_ts(item.get("started_at"))
        if started is None:
            continue
        if started >= submitted:
            fresh.append(item)
    return fresh


# ---------------------------------------------------------------------------
# Lệnh
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    dir_ = Path(args.dir)
    if state_path(dir_).exists() and not args.force:
        raise LoopError(
            EXIT_USAGE,
            f"{state_path(dir_)} đã tồn tại. Dùng --force để tạo lại (sẽ mất lịch sử).",
        )
    roles = {
        "planner": args.planner,
        "executor": args.executor,
        "verifier": args.verifier,
        "human": args.human,
    }
    require_distinct_roles(roles)
    dir_.mkdir(parents=True, exist_ok=True)
    stamp = iso(now())
    state = {
        "schema": SCHEMA,
        "task": {
            "slug": args.slug,
            "goal": args.goal or "",
            "created_at": stamp,
            "created_by": args.planner,
        },
        "roles": roles,
        "phase": "planned",
        "plan": None,
        "attempts": [],
        "decisions": [],
        "updated_at": stamp,
        "updated_by": args.planner,
    }
    save(dir_, state, {"event": "init", "by": args.planner, "slug": args.slug})
    print(f"✅ Khởi tạo loop tại {dir_}")
    print(f"   Vai: planner={args.planner} · executor={args.executor} "
          f"· verifier={args.verifier} · human={args.human}")
    print(f"   Pha: {state['phase']} (chưa có plan — planner phải `plan` trước)")
    return EXIT_OK


def _parse_plan_markdown(text: str) -> list[dict[str, Any]]:
    """Đọc plan dạng markdown list. Mỗi bước: `<việc> → <kiểm chứng>`."""
    steps: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = re.match(r"^\s*(?:\d+[.)]|[-*])\s+(.*\S)\s*$", line)
        if not match:
            continue
        parts = re.split(r"\s*(?:→|->)\s*", match.group(1), maxsplit=1)
        steps.append({
            "id": len(steps) + 1,
            "text": parts[0].strip(),
            "check": parts[1].strip() if len(parts) > 1 else "",
        })
    return steps


def cmd_plan(args: argparse.Namespace) -> int:
    dir_ = Path(args.dir)
    state = load(dir_)
    require_role(state, args.by, "planner")
    require_phase(state, ("planned",), "lập plan")

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    steps = _parse_plan_markdown(text)
    if not steps:
        raise LoopError(EXIT_USAGE, "plan rỗng — cần ít nhất 1 bước dạng `1. việc → kiểm chứng`")
    missing = [step["id"] for step in steps if not step["check"]]
    if missing:
        raise LoopError(
            EXIT_POLICY,
            f"bước {missing} thiếu phần kiểm chứng. Mỗi bước phải viết "
            "`<việc> → <lệnh kiểm chứng>`, nếu không verifier không có gì để chạy lại.",
        )

    state["plan"] = {
        "source": args.file or "stdin",
        "steps": steps,
        "planned_at": iso(now()),
        "planned_by": args.by,
        "raw": text.strip(),
    }
    state["phase"] = "planned"
    save(dir_, state, {"event": "plan", "by": args.by, "steps": len(steps)})
    print(f"✅ Plan: {len(steps)} bước, mỗi bước có kiểm chứng")
    return EXIT_OK


def cmd_submit(args: argparse.Namespace) -> int:
    dir_ = Path(args.dir)
    state = load(dir_)
    require_role(state, args.by, "executor")
    if not state.get("plan"):
        raise LoopError(EXIT_PHASE, "chưa có plan — planner phải `plan` trước khi executor làm")
    require_phase(state, ("planned", "verified_fail", "rejected"), "submit")

    submitted_at = iso(now())
    evidence_ids: list[str] = []
    evidence_paths: list[str] = list(args.evidence or [])
    if args.evidence_glob:
        evidence_paths.extend(sorted(glob.glob(args.evidence_glob)))
    for raw in evidence_paths:
        try:
            data = json.loads(Path(raw).read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("evidence_id"):
            evidence_ids.append(str(data["evidence_id"]))

    attempt = {
        "n": len(state.get("attempts") or []) + 1,
        "submitted_at": submitted_at,
        "submitted_by": args.by,
        "summary": args.summary,
        "evidence_ids": evidence_ids,
        "metrics": {},
        "verification": None,
    }

    if args.metrics_json:
        try:
            raw_metrics = json.loads(Path(args.metrics_json).read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise LoopError(EXIT_USAGE, f"không thấy {args.metrics_json}")
        except json.JSONDecodeError as exc:
            raise LoopError(EXIT_USAGE, f"metrics JSON hỏng: {exc}")
        if not isinstance(raw_metrics, dict):
            raise LoopError(EXIT_USAGE, "metrics phải là object {tên: {value, ...}}")
        for name, spec in raw_metrics.items():
            attempt["metrics"][name] = validate_metric(name, spec, attempt)

    state.setdefault("attempts", []).append(attempt)
    state["phase"] = "submitted"
    save(dir_, state, {
        "event": "submit",
        "by": args.by,
        "attempt": attempt["n"],
        "metrics": len(attempt["metrics"]),
    })
    print(f"✅ Submit attempt #{attempt['n']} — {len(attempt['metrics'])} metric")
    if attempt["metrics"]:
        for name, spec in attempt["metrics"].items():
            if spec["value"] is None:
                print(f"   • {name}: null ({spec['reason']})")
            else:
                print(f"   • {name}: {spec['value']} (đo bởi {spec['measured_by']})")
    print("   Chờ verifier chạy lại từ đầu. Executor không được tự chấm.")
    return EXIT_OK


def cmd_verify(args: argparse.Namespace) -> int:
    dir_ = Path(args.dir)
    state = load(dir_)
    require_role(state, args.by, "verifier")
    require_phase(state, ("submitted",), "verify")

    attempt = current_attempt(state)
    if str(attempt.get("submitted_by")) == args.by:
        raise LoopError(
            EXIT_POLICY,
            "người vừa submit không được tự verify. Cần một thực thể khác chấm.",
        )

    paths = list(args.evidence or [])
    if args.evidence_glob:
        paths.extend(sorted(glob.glob(args.evidence_glob)))
    if not paths:
        raise LoopError(
            EXIT_USAGE,
            "cần evidence do `verify_gate.py run` sinh ra (--evidence / --evidence-glob). "
            "Verifier phải chạy lệnh thật, không đọc báo cáo của executor.",
        )

    records = load_evidence(paths)
    fresh = select_fresh_evidence(records, attempt["submitted_at"])
    stale = [item for item in records if item not in fresh]

    if not fresh:
        raise LoopError(
            EXIT_POLICY,
            f"toàn bộ {len(records)} evidence được chạy TRƯỚC lúc submit "
            f"({attempt['submitted_at']}) ⇒ không dùng được. "
            "Verifier phải chạy lại từ đầu, không tái sử dụng bằng chứng cũ.",
        )

    failed = [item for item in fresh if int(item.get("exit_code", 1)) != 0]
    derived = "fail" if failed else "pass"
    if args.result and args.result != "auto" and args.result != derived:
        raise LoopError(
            EXIT_POLICY,
            f"verifier khai '{args.result}' nhưng evidence nói '{derived}' "
            f"({len(fresh)} lệnh, {len(failed)} lệnh lỗi). Kết quả do lệnh quyết định, không do lời khai.",
        )

    verification = {
        "result": derived,
        "verified_at": iso(now()),
        "verified_by": args.by,
        "fresh_evidence": len(fresh),
        "ignored_stale_evidence": len(stale),
        "commands": [
            {
                "evidence_id": item["evidence_id"],
                "command": item["command"],
                "exit_code": item["exit_code"],
                "started_at": item["started_at"],
                "finished_at": item["finished_at"],
                "stdout_sha256": item.get("stdout_sha256"),
                "source": item.get("_source"),
            }
            for item in fresh
        ],
    }
    attempt["verification"] = verification
    state["phase"] = "verified_pass" if derived == "pass" else "verified_fail"
    save(dir_, state, {
        "event": "verify",
        "by": args.by,
        "attempt": attempt["n"],
        "result": derived,
        "fresh": len(fresh),
        "stale": len(stale),
    })
    icon = "✅" if derived == "pass" else "❌"
    print(f"{icon} Verify attempt #{attempt['n']}: {derived.upper()}")
    print(f"   Evidence mới: {len(fresh)} · bỏ qua evidence cũ: {len(stale)}")
    for item in fresh:
        mark = "ok" if int(item.get("exit_code", 1)) == 0 else "FAIL"
        print(f"   • [{mark}] {item['command']}")
    if derived == "fail":
        print("   Executor phải sửa và submit attempt mới.")
    return EXIT_OK


def cmd_decide(args: argparse.Namespace) -> int:
    dir_ = Path(args.dir)
    state = load(dir_)
    require_role(state, args.by, "human")
    require_phase(state, ("verified_pass", "verified_fail"), "quyết định")
    if args.accept and args.reject:
        raise LoopError(EXIT_USAGE, "chọn --accept hoặc --reject, không cả hai")
    if not args.accept and not args.reject:
        raise LoopError(EXIT_USAGE, "cần --accept hoặc --reject")

    attempt = current_attempt(state)
    if args.accept and state["phase"] != "verified_pass":
        raise LoopError(EXIT_PHASE, "không thể accept khi verify chưa pass")
    if args.reject and not str(args.note or "").strip():
        raise LoopError(EXIT_POLICY, "reject bắt buộc có --note nêu lý do")

    action = "accept" if args.accept else "reject"
    state.setdefault("decisions", []).append({
        "at": iso(now()),
        "by": args.by,
        "action": action,
        "attempt": attempt["n"],
        "note": args.note or "",
    })
    state["phase"] = "accepted" if args.accept else "rejected"
    save(dir_, state, {"event": action, "by": args.by, "attempt": attempt["n"]})
    print(f"✅ Human {action} attempt #{attempt['n']} → pha '{state['phase']}'")
    return EXIT_OK


def cmd_status(args: argparse.Namespace) -> int:
    dir_ = Path(args.dir)
    state = load(dir_)
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return EXIT_OK

    roles = state.get("roles") or {}
    print(f"Task    : {state['task'].get('slug')} — {state['task'].get('goal') or '(không có mô tả)'}")
    print(f"Vai     : planner={roles.get('planner')} · executor={roles.get('executor')} "
          f"· verifier={roles.get('verifier')} · human={roles.get('human')}")
    print(f"Pha     : {state.get('phase')}")
    plan = state.get("plan") or {}
    if plan:
        print(f"Plan    : {len(plan.get('steps') or [])} bước (bởi {plan.get('planned_by')})")
    attempts = state.get("attempts") or []
    print(f"Attempt : {len(attempts)}")
    for attempt in attempts:
        verification = attempt.get("verification") or {}
        result = verification.get("result", "chưa verify")
        print(f"   #{attempt['n']} {attempt.get('submitted_at')} bởi {attempt.get('submitted_by')} "
              f"→ {result}")
        for name, spec in (attempt.get("metrics") or {}).items():
            if spec.get("value") is None:
                print(f"      {name}: null — {spec.get('reason')}")
            else:
                print(f"      {name}: {spec.get('value')} (đo bởi {spec.get('measured_by')})")
    journal = journal_path(dir_)
    if journal.exists():
        lines = journal.read_text(encoding="utf-8").splitlines()
        print(f"Journal : {len(lines)} dòng ({journal})")
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loop_state.py",
        description="Multi-Agent Loop: Planner / Executor / Verifier / State / Human",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Khởi tạo loop")
    init.add_argument("--dir", required=True)
    init.add_argument("--slug", required=True)
    init.add_argument("--goal", default="")
    init.add_argument("--planner", required=True)
    init.add_argument("--executor", required=True)
    init.add_argument("--verifier", required=True)
    init.add_argument("--human", required=True)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    plan = sub.add_parser("plan", help="Planner lập plan")
    plan.add_argument("--dir", required=True)
    plan.add_argument("--by", required=True)
    plan.add_argument("--file", default="")
    plan.set_defaults(func=cmd_plan)

    submit = sub.add_parser("submit", help="Executor gửi kết quả")
    submit.add_argument("--dir", required=True)
    submit.add_argument("--by", required=True)
    submit.add_argument("--summary", required=True)
    submit.add_argument("--metrics-json", default="")
    submit.add_argument("--evidence", action="append", default=[])
    submit.add_argument("--evidence-glob", default="")
    submit.set_defaults(func=cmd_submit)

    verify = sub.add_parser("verify", help="Verifier chấm (chạy lại từ đầu)")
    verify.add_argument("--dir", required=True)
    verify.add_argument("--by", required=True)
    verify.add_argument("--evidence", action="append", default=[])
    verify.add_argument("--evidence-glob", default="")
    verify.add_argument("--result", default="auto", choices=["auto", "pass", "fail"])
    verify.set_defaults(func=cmd_verify)

    decide = sub.add_parser("decide", help="Human chấp nhận / từ chối")
    decide.add_argument("--dir", required=True)
    decide.add_argument("--by", required=True)
    decide.add_argument("--accept", action="store_true")
    decide.add_argument("--reject", action="store_true")
    decide.add_argument("--note", default="")
    decide.set_defaults(func=cmd_decide)

    status = sub.add_parser("status", help="Xem trạng thái")
    status.add_argument("--dir", required=True)
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except LoopError as exc:
        print(f"❌ {exc.message}", file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
