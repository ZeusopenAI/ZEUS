#!/usr/bin/env python3
"""SPEC / CHECKS — bộ kiểm mà Verifier chạy lại từ đầu (stdlib, không mạng).

Nguyên tắc: **cái gì đo được bằng máy thì phải bị buộc đo bằng máy**. File này là chỗ
"buộc" đó. Verifier không đọc báo cáo của Executor; Verifier chạy file này trên
`input/` + `output/` + `log/` và ghi kết quả mới vào `verify/`.

    # 1) Verifier chạy toàn bộ check, sinh báo cáo mới
    python3 spec/checks.py run \
      --spec spec --input input --output output --log log --state state/state.json \
      --report "verify/checks-$(date -u +%Y%m%dT%H%M%SZ).json"

    # 2) Kiểm báo cáo có khớp output hiện tại không (chống dùng lại báo cáo cũ)
    python3 spec/checks.py freshness --output output --report verify/checks-....json

    # 3) Kiểm ranh giới ghi file của từng vai (dùng trong CI)
    python3 spec/checks.py ownership --role executor --base origin/main

Mã thoát:

    0  mọi check bắt buộc pass
    2  lỗi dùng
    3  không đo được check nào (thiếu dữ liệu)
    4  có check fail
    5  report cũ / không khớp output hiện tại (freshness)
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

MAX_RECORDS_PER_SECOND = 50.0
MAX_DUPLICATE_RATE = 0.05
MIN_SAMPLE_FOR_DISTRIBUTION = 30
IQR_OUTLIER_FACTOR = 3.0
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]00:00)$")

PASS, FAIL, WARN, NOT_MEASURED = "pass", "fail", "warn", "not_measured"


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------

def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def system_day(value: dt.datetime | None = None) -> str:
    return (value or utc_now()).astimezone(dt.timezone.utc).strftime("%Y-%m-%d")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(output_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Đọc mọi record trong output/. Trả (records, files)."""
    records: list[dict[str, Any]] = []
    files: list[str] = []
    if not output_dir.exists():
        return records, files
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name.startswith(".") or path.name == "README.md":
            continue
        rel = str(path.relative_to(output_dir))
        if path.suffix == ".jsonl":
            files.append(rel)
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    records.append({"_invalid": f"{rel}:{number}: JSON hỏng — {exc}"})
                    continue
                if isinstance(data, dict):
                    data.setdefault("_file", f"{rel}:{number}")
                    records.append(data)
                else:
                    records.append({"_invalid": f"{rel}:{number}: không phải object"})
        elif path.suffix == ".json":
            files.append(rel)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                records.append({"_invalid": f"{rel}: JSON hỏng — {exc}"})
                continue
            items = data if isinstance(data, list) else [data]
            for index, item in enumerate(items):
                if isinstance(item, dict):
                    item.setdefault("_file", f"{rel}:{index}")
                    records.append(item)
                else:
                    records.append({"_invalid": f"{rel}:{index}: không phải object"})
    return records, files


def snapshot_of(output_dir: Path) -> str:
    """Hash nội dung output — dùng để phát hiện báo cáo verify đã cũ."""
    digest = hashlib.sha256()
    if output_dir.exists():
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and not path.name.startswith(".") and path.name != "README.md":
                digest.update(str(path.relative_to(output_dir)).encode("utf-8"))
                digest.update(path.read_bytes())
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# JSON Schema (tập con đủ dùng — không cần thư viện ngoài)
# ---------------------------------------------------------------------------

TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    python_type = TYPES.get(expected)
    return isinstance(value, python_type) if python_type else True


def _resolve(ref: str, root: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        return {}
    node: Any = root
    for part in ref[2:].split("/"):
        node = node.get(part, {}) if isinstance(node, dict) else {}
    return node if isinstance(node, dict) else {}


def validate(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    if not isinstance(schema, dict):
        return errors
    if "$ref" in schema:
        return validate(value, _resolve(str(schema["$ref"]), root), root, path)

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: phải bằng {schema['const']!r}, nhận {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: phải thuộc {schema['enum']}, nhận {value!r}")

    expected = schema.get("type")
    if expected:
        choices = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(value, choice) for choice in choices):
            errors.append(f"{path}: sai kiểu, cần {expected}, nhận {type(value).__name__}")
            return errors

    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            errors.append(f"{path}: ngắn hơn {schema['minLength']} ký tự")
        if "pattern" in schema and not re.search(str(schema["pattern"]), value):
            errors.append(f"{path}: không khớp pattern {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: nhỏ hơn minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: lớn hơn maximum {schema['maximum']}")

    if isinstance(value, dict):
        for key in schema.get("required", []) or []:
            if key not in value:
                errors.append(f"{path}: thiếu trường bắt buộc '{key}'")
        properties = schema.get("properties") or {}
        for key, sub in properties.items():
            if key in value:
                errors.extend(validate(value[key], sub, root, f"{path}.{key}"))
        extra = [k for k in value if k not in properties and not k.startswith("_")]
        if schema.get("additionalProperties") is False and extra:
            errors.append(f"{path}: trường lạ {extra}")
        if "maxProperties" in schema and len(value) > int(schema["maxProperties"]):
            errors.append(f"{path}: nhiều hơn {schema['maxProperties']} trường")
        if "minProperties" in schema and len(value) < int(schema["minProperties"]):
            errors.append(f"{path}: ít hơn {schema['minProperties']} trường")
    if isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for index, item in enumerate(value):
                errors.extend(validate(item, items, root, f"{path}[{index}]"))
        if "minItems" in schema and len(value) < int(schema["minItems"]):
            errors.append(f"{path}: ít hơn {schema['minItems']} phần tử")
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            errors.append(f"{path}: nhiều hơn {schema['maxItems']} phần tử")

    for sub in schema.get("allOf", []) or []:
        errors.extend(validate(value, sub, root, path))
    if "oneOf" in schema:
        matched = [sub for sub in schema["oneOf"] if not validate(value, sub, root, path)]
        if len(matched) != 1:
            errors.append(f"{path}: phải khớp đúng 1 nhánh oneOf, khớp {len(matched)}")
    if "if" in schema:
        condition = not validate(value, schema["if"], root, path)
        branch = schema.get("then") if condition else schema.get("else")
        if branch:
            errors.extend(validate(value, branch, root, path))
    return errors


# ---------------------------------------------------------------------------
# Các check
# ---------------------------------------------------------------------------

def check_schema(records, ctx) -> dict[str, Any]:
    schema = ctx.get("schema")
    if not schema:
        return {"status": NOT_MEASURED, "metrics": {"records_checked": {"value": None,
                "reason": "không nạp được spec/schema.json"}}}
    invalid_records = [r for r in records if "_invalid" in r]
    problems: list[str] = [r["_invalid"] for r in invalid_records]
    checked = 0
    for record in records:
        clean = {k: v for k, v in record.items() if not k.startswith("_")}
        if "_invalid" in record:
            continue
        checked += 1
        for error in validate(clean, schema, schema):
            problems.append(f"{record.get('_file', '?')}: {error}")
    status = PASS if not problems else FAIL
    return {
        "status": status,
        "metrics": {
            "records_checked": {"value": checked, "measured_by": "checks.py"},
            "schema_errors": {"value": len(problems), "measured_by": "checks.py:check_schema",
                              **({"evidence": "problems[]"} if problems else {})},
        },
        "problems": problems[:50],
    }


def _walk_metrics(node: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(node, dict):
        if "value" in node:
            yield path, node
            return
        for key, value in node.items():
            yield from _walk_metrics(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_metrics(value, f"{path}[{index}]")


def check_null_reason(records, ctx) -> dict[str, Any]:
    missing: list[str] = []
    total_null = 0
    for record in records:
        for path, metric in _walk_metrics(record):
            if metric.get("value") is None:
                total_null += 1
                if not str(metric.get("reason") or "").strip():
                    missing.append(f"{path}: null thiếu reason")
    return {
        "status": FAIL if missing else PASS,
        "metrics": {
            "null_values": {"value": total_null, "measured_by": "checks.py:check_null_reason",
                            **({"evidence": "problems[]"} if total_null == 0 else {})},
            "null_without_reason": {"value": len(missing), "measured_by": "checks.py:check_null_reason",
                                    **({"evidence": "problems[]"} if missing else {})},
        },
        "problems": missing[:50],
    }


def check_fake_zero(records, ctx) -> dict[str, Any]:
    """Số 0 phải có measured_by + evidence trỏ tới dòng log có thật.

    Kiểm hai dạng:
      1. metric dạng {"value": 0, ...} ở bất kỳ độ sâu nào;
      2. trường số cấp record có tên trong --zero-guard-fields (vd "score": 0), khi đó
         provenance lấy ở cấp record (measured_by + evidence).
    """
    log_dir: Path = ctx["log_dir"]
    log_lines: set[str] = set()
    if log_dir.exists():
        for path in sorted(log_dir.glob("*.jsonl")):
            rel = path.relative_to(ctx["root"]).as_posix()
            for number, _ in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                log_lines.add(f"{rel}#L{number}")

    problems: list[str] = []
    zeros = 0
    def _check_zero(label: str, measured_by: str, evidence: str) -> None:
        nonlocal zeros
        zeros += 1
        measured_by = measured_by.strip()
        evidence = evidence.strip()
        if not measured_by:
            problems.append(f"{label} = 0 nhưng thiếu measured_by")
        if not evidence:
            problems.append(f"{label} = 0 nhưng thiếu evidence (0 giả)")
        elif log_lines and evidence not in log_lines:
            problems.append(f"{label} = 0 trỏ tới evidence không tồn tại trong log: {evidence}")

    guard_fields = set(ctx.get("zero_guard_fields") or [])
    for record in records:
        for path, metric in _walk_metrics(record):
            if metric.get("value") != 0 or isinstance(metric.get("value"), bool):
                continue
            _check_zero(path, str(metric.get("measured_by") or ""), str(metric.get("evidence") or ""))

        # Trường số cấp record (vd score, violation_count): provenance ở cấp record.
        for field in guard_fields:
            if field not in record:
                continue
            value = record[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value != 0:
                continue
            _check_zero(
                f"{record.get('_file', '?')}:{field}",
                str(record.get("measured_by") or ""),
                str(record.get("evidence") or ""),
            )

    return {
        "status": FAIL if problems else PASS,
        "metrics": {
            "zero_values": {"value": zeros, "measured_by": "checks.py:check_fake_zero",
                            **({"evidence": "problems[]"} if zeros == 0 else {})},
            "unproven_zeros": {"value": len(problems), "measured_by": "checks.py:check_fake_zero",
                               **({"evidence": "problems[]"} if problems else {})},
        },
        "problems": problems[:50],
    }


def check_duplicates(records, ctx) -> dict[str, Any]:
    contents = [str(r.get("content") or "").strip() for r in records if r.get("content")]
    if not contents:
        return {"status": NOT_MEASURED, "metrics": {
            "duplicate_rate": {"value": None, "reason": "không có trường 'content' để so trùng"}}}
    unique = len(set(contents))
    rate = 1 - unique / len(contents)
    status = FAIL if rate > ctx["max_duplicate_rate"] else PASS
    return {
        "status": status,
        "metrics": {
            "records_with_content": {"value": len(contents), "measured_by": "checks.py"},
            "unique_contents": {"value": unique, "measured_by": "checks.py"},
            "duplicate_rate": {"value": round(rate, 4), "measured_by": "checks.py",
                               "unit": "ratio"},
            "max_allowed": {"value": ctx["max_duplicate_rate"], "measured_by": "spec/rules.md"},
        },
        "problems": ([] if status == PASS else
                     [f"tỷ lệ trùng lặp {rate:.2%} > {ctx['max_duplicate_rate']:.2%} — nghi sinh hàng loạt"]),
    }


def check_length_distribution(records, ctx) -> dict[str, Any]:
    lengths = [len(str(r["content"])) for r in records if r.get("content")]
    if len(lengths) < MIN_SAMPLE_FOR_DISTRIBUTION:
        return {
            "status": NOT_MEASURED,
            "metrics": {
                "sample_size": {"value": len(lengths), "measured_by": "checks.py"},
                "length_outliers": {"value": None,
                                    "reason": f"mẫu {len(lengths)} < {MIN_SAMPLE_FOR_DISTRIBUTION} "
                                              "nên không kết luận phân bố — không ghi 0 giả"},
                "median_length": {"value": None,
                                  "reason": "mẫu chưa đủ lớn để median có ý nghĩa"},
            },
        }
    ordered = sorted(lengths)
    q1 = statistics.quantiles(ordered, n=4)[0]
    q3 = statistics.quantiles(ordered, n=4)[2]
    iqr = q3 - q1
    low = q1 - IQR_OUTLIER_FACTOR * iqr
    high = q3 + IQR_OUTLIER_FACTOR * iqr
    outliers = [value for value in lengths if value < low or value > high]
    status = WARN if outliers else PASS
    return {
        "status": status,
        "metrics": {
            "sample_size": {"value": len(lengths), "measured_by": "checks.py"},
            "median_length": {"value": int(statistics.median(lengths)), "measured_by": "checks.py",
                              "unit": "chars"},
            "iqr": {"value": round(iqr, 2), "measured_by": "checks.py", "unit": "chars"},
            "length_outliers": {"value": len(outliers), "measured_by": "checks.py:check_length_distribution",
                                **({"evidence": "problems[]"} if outliers else {})},
        },
        "problems": ([f"{len(outliers)} record ngoài khoảng [{low:.0f}, {high:.0f}] ký tự"]
                     if outliers else []),
    }


def check_throughput(records, ctx) -> dict[str, Any]:
    """Đọc log để biết thời gian xử lý thật; tốc độ phi lý ⇒ nghi bịa."""
    log_dir: Path = ctx["log_dir"]
    spans: list[tuple[dt.datetime, dt.datetime, int]] = []
    if log_dir.exists():
        for path in sorted(log_dir.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                started = entry.get("started_at") or entry.get("at")
                finished = entry.get("finished_at") or entry.get("at")
                count = entry.get("records") or entry.get("count")
                if not started or not finished or not count:
                    continue
                try:
                    start_dt = dt.datetime.fromisoformat(str(started).replace("Z", "+00:00"))
                    end_dt = dt.datetime.fromisoformat(str(finished).replace("Z", "+00:00"))
                except ValueError:
                    continue
                spans.append((start_dt, end_dt, int(count)))
    if not spans:
        return {"status": NOT_MEASURED, "metrics": {
            "records_per_second": {"value": None,
                                   "reason": "log không có dòng {started_at, finished_at, records} "
                                             "nên không đo được tốc độ"}}}
    total_seconds = sum(max((end - start).total_seconds(), 0.001) for start, end, _ in spans)
    total_records = sum(count for _, _, count in spans)
    rate = total_records / total_seconds
    status = FAIL if rate > ctx["max_records_per_second"] else PASS
    return {
        "status": status,
        "metrics": {
            "records_processed": {"value": total_records, "measured_by": "checks.py"},
            "elapsed_seconds": {"value": round(total_seconds, 3), "measured_by": "checks.py"},
            "records_per_second": {"value": round(rate, 2), "measured_by": "checks.py"},
            "max_allowed_per_second": {"value": ctx["max_records_per_second"],
                                       "measured_by": "spec/rules.md"},
        },
        "problems": ([] if status == PASS else
                     [f"{rate:.1f} record/giây > {ctx['max_records_per_second']} — "
                      "tốc độ này thường là bịa, cần kiểm tay"]),
    }


def check_utc_format(records, ctx) -> dict[str, Any]:
    problems: list[str] = []
    checked = 0
    for record in records:
        for key in ("created_at", "at", "timestamp"):
            if key not in record:
                continue
            checked += 1
            if not TS_RE.match(str(record[key])):
                problems.append(f"{record.get('_file', '?')}: {key}={record[key]!r} không phải UTC Z")
    if checked == 0:
        return {"status": NOT_MEASURED, "metrics": {
            "timestamps_checked": {"value": None, "reason": "record không có trường thời gian"}}}
    return {
        "status": FAIL if problems else PASS,
        "metrics": {
            "timestamps_checked": {"value": checked, "measured_by": "checks.py"},
            "non_utc_timestamps": {"value": len(problems), "measured_by": "checks.py:check_utc_format",
                                   **({"evidence": "problems[]"} if problems else {})},
        },
        "problems": problems[:50],
    }


def check_day_boundary(records, ctx) -> dict[str, Any]:
    state_path: Path = ctx["state_path"]
    if not state_path or not state_path.exists():
        return {"status": NOT_MEASURED, "metrics": {
            "day_drift_days": {"value": None, "reason": "không có state/state.json"}}}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": FAIL, "problems": ["state/state.json không phải JSON hợp lệ"],
                "metrics": {"day_drift_days": {"value": None, "reason": "state hỏng"}}}
    recorded = str(state.get("system_day") or "").strip()
    today = system_day()
    if not recorded:
        return {"status": FAIL, "problems": ["state thiếu system_day — không xác định được ngày hệ thống"],
                "metrics": {"day_drift_days": {"value": None, "reason": "thiếu system_day"}}}
    try:
        drift = (dt.date.fromisoformat(today) - dt.date.fromisoformat(recorded)).days
    except ValueError:
        return {"status": FAIL, "problems": [f"system_day '{recorded}' không phải YYYY-MM-DD"],
                "metrics": {"day_drift_days": {"value": None, "reason": "system_day sai định dạng"}}}
    return {
        "status": PASS if drift == 0 else WARN,
        "metrics": {
            "system_day_state": {"value": recorded, "measured_by": "checks.py"},
            "system_day_utc_now": {"value": today, "measured_by": "checks.py"},
            "day_drift_days": {"value": drift, "measured_by": "checks.py:check_day_boundary",
                               **({"evidence": "problems[]"} if drift else {})},
        },
        "problems": ([] if drift == 0 else
                     [f"state đang ở ngày {recorded}, UTC hiện tại {today} — hạn mức có thể đã reset sai"]),
    }


CHECKS = {
    "schema": (check_schema, True),
    "null_reason": (check_null_reason, True),
    "fake_zero": (check_fake_zero, True),
    "duplicates": (check_duplicates, True),
    "length_distribution": (check_length_distribution, False),
    "throughput": (check_throughput, True),
    "utc_format": (check_utc_format, True),
    # Bắt buộc: thiếu/sai system_day thì không xác định được ngày hệ thống ⇒ fail.
    # Lệch ngày (drift) chỉ là warn — vẫn đo được, chỉ cảnh báo quota có thể reset sai.
    "day_boundary": (check_day_boundary, True),
}


# ---------------------------------------------------------------------------
# Lệnh: run
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> int:
    root = Path(args.root or ".").resolve()
    spec_dir = (root / args.spec).resolve() if not Path(args.spec).is_absolute() else Path(args.spec)
    output_dir = (root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    input_dir = (root / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input)
    log_dir = (root / args.log).resolve() if not Path(args.log).is_absolute() else Path(args.log)
    state_path = (root / args.state).resolve() if not Path(args.state).is_absolute() else Path(args.state)

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = root / report_path
    if report_path.exists() and not args.force:
        print(f"❌ {report_path} đã tồn tại — verifier phải chạy lại từ đầu, không ghi đè báo cáo cũ. "
              "Dùng tên mới hoặc --force nếu bạn thật sự muốn thay.", file=sys.stderr)
        return 5

    schema_path = spec_dir / "schema.json"
    schema = None
    if schema_path.exists():
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            schema = None

    records, files = load_records(output_dir)
    if not records:
        print(f"❌ không có record nào trong {output_dir} — không có gì để kiểm.", file=sys.stderr)
        return 3

    ctx = {
        "root": root,
        "schema": schema,
        "log_dir": log_dir,
        "state_path": state_path,
        "input_dir": input_dir,
        "max_records_per_second": args.max_records_per_second,
        "max_duplicate_rate": args.max_duplicate_rate,
        "zero_guard_fields": [f.strip() for f in (args.zero_guard_fields or "").split(",") if f.strip()],
    }

    started = utc_now()
    results: dict[str, Any] = {}
    for name, (func, required) in CHECKS.items():
        try:
            result = func(records, ctx)
        except Exception as exc:  # noqa: BLE001 — một check hỏng không được làm sập cả báo cáo
            result = {"status": FAIL, "problems": [f"check lỗi khi chạy: {exc!r}"],
                      "metrics": {"value": {"value": None, "reason": f"check ném lỗi: {exc}"}}}
        result["required"] = required
        results[name] = result
    finished = utc_now()

    required_fail = [n for n, r in results.items() if r["required"] and r["status"] == FAIL]
    warnings = [n for n, r in results.items() if r["status"] == WARN]
    measured = [n for n, r in results.items() if r["status"] != NOT_MEASURED]
    overall = "fail" if required_fail else ("pass" if measured else NOT_MEASURED)

    report = {
        "schema": "checks-report/1",
        "system_day": system_day(started),
        "started_at": iso(started),
        "finished_at": iso(finished),
        "duration_ms": int((finished - started).total_seconds() * 1000),
        "ran_by": args.by,
        "tool": "spec/checks.py",
        "inputs": {
            "spec": str(spec_dir),
            "input": str(input_dir),
            "output": str(output_dir),
            "log": str(log_dir),
            "state": str(state_path),
            "records": len(records),
            "output_files": files,
        },
        "output_snapshot": snapshot_of(output_dir),
        "overall": overall,
        "required_failed": required_fail,
        "warnings": warnings,
        "checks": results,
        "verdict_rule": "pass chỉ khi mọi check bắt buộc (required=true) đều pass",
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    icon = {"pass": "✅", "fail": "❌", NOT_MEASURED: "⚠️"}[overall]
    print(f"{icon} {overall.upper()} — {len(records)} record, {report_path}")
    for name, result in results.items():
        mark = {"pass": "ok  ", "fail": "FAIL", "warn": "warn", NOT_MEASURED: "n/a "}[result["status"]]
        required = "" if result["required"] else " (không bắt buộc)"
        print(f"   [{mark}] {name}{required}")
        for problem in (result.get("problems") or [])[:3]:
            print(f"          ↳ {problem}")
    if required_fail:
        print(f"\nKết luận: FAIL vì {', '.join(required_fail)}. Executor phải sửa rồi submit lại.")
        return 4
    return 0


# ---------------------------------------------------------------------------
# Lệnh: freshness — chống dùng lại báo cáo cũ
# ---------------------------------------------------------------------------

def cmd_freshness(args: argparse.Namespace) -> int:
    root = Path(args.root or ".").resolve()
    output_dir = Path(args.output) if Path(args.output).is_absolute() else root / args.output
    report_path = Path(args.report) if Path(args.report).is_absolute() else root / args.report
    if not report_path.exists():
        print(f"❌ không có báo cáo {report_path}", file=sys.stderr)
        return 3
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"❌ báo cáo không phải JSON: {exc}", file=sys.stderr)
        return 3
    current = snapshot_of(output_dir)
    recorded = report.get("output_snapshot")
    if not recorded:
        print("❌ báo cáo không có output_snapshot — không chứng minh được là bản mới", file=sys.stderr)
        return 5
    if recorded != current:
        print("❌ BÁO CÁO CŨ: output đã thay đổi sau lần verify này. Phải chạy lại checks.", file=sys.stderr)
        print(f"   snapshot trong báo cáo: {recorded[:16]}…")
        print(f"   snapshot hiện tại      : {current[:16]}…", file=sys.stderr)
        return 5
    print(f"✅ Báo cáo khớp output hiện tại ({report.get('overall')}, {report.get('system_day')})")
    return 0


# ---------------------------------------------------------------------------
# Lệnh: ownership — mỗi vai chỉ ghi trong cửa của mình
# ---------------------------------------------------------------------------

ALLOWED_WRITES = {
    "planner": ("spec/",),
    "executor": ("output/", "log/"),
    "verifier": ("verify/",),
    "human": ("reports/",),
    "state": ("state/",),
}


def changed_files(root: Path, base: str | None, staged: bool) -> list[str]:
    if staged:
        args = ["git", "-C", str(root), "diff", "--cached", "--name-only"]
    elif base:
        args = ["git", "-C", str(root), "diff", "--name-only", f"{base}...HEAD"]
    else:
        args = ["git", "-C", str(root), "diff", "--name-only", "HEAD"]
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise SystemExit(f"❌ git diff lỗi: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def cmd_ownership(args: argparse.Namespace) -> int:
    root = Path(args.root or ".").resolve()
    role = args.role
    if role not in ALLOWED_WRITES:
        print(f"❌ vai '{role}' không hợp lệ. Chọn: {', '.join(ALLOWED_WRITES)}", file=sys.stderr)
        return 2
    allowed = ALLOWED_WRITES[role]
    prefix = args.prefix.strip("/")
    files = changed_files(root, args.base, args.staged)
    if prefix:
        files = [f for f in files if f == prefix or f.startswith(prefix + "/")]
        files = [f[len(prefix) + 1:] if f.startswith(prefix + "/") else f for f in files]
    violations = [f for f in files if not any(f.startswith(a) for a in allowed)]
    if violations:
        print(f"❌ vai {role} chỉ được ghi {allowed}, nhưng đã đụng:")
        for path in violations[:20]:
            print(f"   • {path}")
        return 4
    print(f"✅ vai {role} chỉ ghi trong {allowed} ({len(files)} file thay đổi)")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="checks.py", description="Bộ kiểm của Verifier (stdlib)")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Chạy toàn bộ check, sinh báo cáo mới")
    run.add_argument("--root", default=".")
    run.add_argument("--spec", default="spec")
    run.add_argument("--input", default="input")
    run.add_argument("--output", default="output")
    run.add_argument("--log", default="log")
    run.add_argument("--state", default="state/state.json")
    run.add_argument("--report", required=True)
    run.add_argument("--by", default="verifier")
    run.add_argument("--max-records-per-second", type=float, default=MAX_RECORDS_PER_SECOND)
    run.add_argument("--max-duplicate-rate", type=float, default=MAX_DUPLICATE_RATE)
    run.add_argument("--zero-guard-fields", default="score,grade,count,total,errors,violation_count",
                     help="Trường số cấp record mà 0 phải có measured_by + evidence")
    run.add_argument("--force", action="store_true", help="Ghi đè báo cáo đã tồn tại (không khuyến khích)")
    run.set_defaults(func=cmd_run)

    fresh = sub.add_parser("freshness", help="Kiểm báo cáo có khớp output hiện tại")
    fresh.add_argument("--root", default=".")
    fresh.add_argument("--output", default="output")
    fresh.add_argument("--report", required=True)
    fresh.set_defaults(func=cmd_freshness)

    own = sub.add_parser("ownership", help="Kiểm ranh giới ghi file của một vai")
    own.add_argument("--root", default=".")
    own.add_argument("--role", required=True, choices=sorted(ALLOWED_WRITES))
    own.add_argument("--base", default="")
    own.add_argument("--staged", action="store_true")
    own.add_argument("--prefix", default="", help="Chỉ xét file dưới thư mục này")
    own.set_defaults(func=cmd_ownership)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
