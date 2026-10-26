#!/usr/bin/env python3
"""Hermes Owner Protocol — engine (stdlib only).

Repo là *đường truyền* giữa Hermes (chủ) và các phiên agent (thực thi):

    .ai/handoff/INBOX.md    Mệnh lệnh Hermes  -> agent      (có front matter + seal)
    .ai/handoff/OUTBOX.md   Báo cáo agent     -> Hermes     (nối thêm, mới nhất ở trên)
    .ai/handoff/STATE.json  Trạng thái máy đọc (directive đang hiệu lực, báo cáo cuối)

Lệnh:

    python3 scripts/hermes_owner.py boot        # BƯỚC 0 của MỌI phiên agent
    python3 scripts/hermes_owner.py status      # xem nhanh trạng thái, không gọi LLM
    python3 scripts/hermes_owner.py issue ...   # (workflow) Hermes ban hành mệnh lệnh
    python3 scripts/hermes_owner.py closeout .. # kết phiên, ghi báo cáo
    python3 scripts/hermes_owner.py selftest    # tự kiểm tra trong thư mục tạm

Mã thoát của `boot` / `status --strict`:

    0  OK — có mệnh lệnh hợp lệ của Hermes
    2  lỗi dùng / thiếu file
    3  chưa có mệnh lệnh nào
    4  mệnh lệnh đã hết hạn
    5  seal không khớp (file bị sửa tay / hỏng)
    6  sai người ban hành / id không khớp STATE

Chính sách đã chốt với Operator: **không có mệnh lệnh hợp lệ thì phiên phải DỪNG**
(không tự quyết, không sửa code). Không có fallback im lặng.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PROTOCOL = "hermes-owner-v1"
SCHEMA = 1
HANDOFF_REL = Path(".ai") / "handoff"
INBOX_NAME = "INBOX.md"
OUTBOX_NAME = "OUTBOX.md"
STATE_NAME = "STATE.json"
ARCHIVE_DIRNAME = "archive"
CACHE_DIRNAME = ".cache"
DEFAULT_REMOTE_REF = "origin/hermes-owner/state"
DEFAULT_TTL_HOURS = 72
MAX_AGE_HOURS = 24 * 14
HISTORY_LIMIT = 30

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 3
EXIT_STALE = 4
EXIT_TAMPERED = 5
EXIT_WRONG_ISSUER = 6

REPORT_START = "<!-- report:start -->"
REPORT_END = "<!-- report:end -->"
# Marker phải đứng riêng một dòng — tránh khớp nhầm khi marker được nhắc trong văn xuôi.
REPORT_RE = re.compile(r"(?ms)^<!-- report:start -->[ \t]*$(.*?)^<!-- report:end -->[ \t]*$")

OUTBOX_HEADER = f"""# OUTBOX — báo cáo của agent gửi Hermes

> Máy đọc: mỗi báo cáo nằm giữa hai dòng đánh dấu `report:start` và `report:end`
> (dạng comment HTML, mỗi dòng đứng riêng). Mới nhất ở trên.
> Không sửa báo cáo cũ; chỉ nối thêm.
"""

INBOX_STUB = """# INBOX — chưa có mệnh lệnh

Hermes chưa ban hành mệnh lệnh nào. Chạy workflow **Hermes owner loop** để triệu tập chủ:

    .github/workflows/hermes-owner-loop.yml

Sau đó chạy lại: `bash scripts/hermes-session-boot.sh`
"""


class ProtocolError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Tiện ích thời gian / chuỗi
# ---------------------------------------------------------------------------

def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_ts(raw: str) -> dt.datetime:
    text = str(raw).strip()
    if not text:
        raise ValueError("rỗng")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    value = dt.datetime.fromisoformat(text)
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def human_delta(delta: dt.timedelta) -> str:
    seconds = int(delta.total_seconds())
    future = seconds >= 0
    seconds = abs(seconds)
    if seconds < 90:
        text = f"{seconds} giây"
    elif seconds < 5400:
        text = f"{seconds // 60} phút"
    elif seconds < 172800:
        text = f"{seconds // 3600} giờ"
    else:
        text = f"{seconds // 86400} ngày"
    return f"còn {text}" if future else f"quá hạn {text}"


def short_commit(repo: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        return "?"


# ---------------------------------------------------------------------------
# Front matter + seal
# ---------------------------------------------------------------------------

def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if text == "":
        return ""
    if text.startswith('"') and text.endswith('"'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text.strip('"')
    if text in {"null", "None", "~"}:
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return text


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ProtocolError(EXIT_MISSING, "INBOX.md thiếu front matter (dòng đầu phải là ---)")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            meta: dict[str, Any] = {}
            for line in lines[1:index]:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                meta[key.strip()] = _parse_scalar(value)
            body = "".join(lines[index + 1:])
            return meta, body.lstrip("\n")
    raise ProtocolError(EXIT_MISSING, "INBOX.md thiếu dòng --- đóng front matter")


def normalize_body(body: str) -> str:
    return body.strip() + "\n"


def seal_of(body: str) -> str:
    digest = hashlib.sha256(normalize_body(body).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_inbox(meta: dict[str, Any], body: str) -> str:
    order = [
        "protocol", "schema", "id", "number", "issuer", "title",
        "issued_at", "valid_until", "seal", "model", "source_run",
    ]
    lines = ["---"]
    for key in order:
        if key not in meta:
            continue
        value = meta[key]
        if isinstance(value, int) or value is None:
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {json.dumps(str(value), ensure_ascii=False)}")
    for key, value in meta.items():
        if key in order:
            continue
        lines.append(f"{key}: {json.dumps(str(value), ensure_ascii=False)}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + "\n" + normalize_body(body)


# ---------------------------------------------------------------------------
# Đọc / ghi trạng thái
# ---------------------------------------------------------------------------

def empty_state() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "schema": SCHEMA,
        "active_directive": None,
        "history": [],
        "last_report": None,
        "updated_at": iso(now_utc()),
        "updated_by": "bootstrap",
    }


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except FileNotFoundError:
        return None
    except Exception:
        return None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_directive(handoff: Path) -> tuple[dict[str, Any], str]:
    inbox = handoff / INBOX_NAME
    try:
        text = inbox.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ProtocolError(EXIT_MISSING, f"chưa có {HANDOFF_REL / INBOX_NAME}")
    meta, body = split_front_matter(text)
    meta["_body"] = body
    return meta, body


def validate_directive(
    meta: dict[str, Any],
    state: dict[str, Any] | None,
    when: dt.datetime,
    max_age_hours: int = MAX_AGE_HOURS,
) -> None:
    if not meta.get("id"):
        raise ProtocolError(EXIT_MISSING, "mệnh lệnh không có id")

    issuer = str(meta.get("issuer") or "").strip()
    if issuer != "hermes":
        raise ProtocolError(
            EXIT_WRONG_ISSUER,
            f"người ban hành là '{issuer or 'không rõ'}', không phải 'hermes' — "
            "chỉ mệnh lệnh do Hermes ban hành mới có hiệu lực",
        )

    active = (state or {}).get("active_directive") or {}
    if active and str(active.get("id")) != str(meta.get("id")):
        raise ProtocolError(
            EXIT_WRONG_ISSUER,
            "INBOX.md không khớp id trong STATE.json "
            f"(INBOX={meta.get('id')}, STATE={active.get('id')}) — file bị sửa tay",
        )

    declared = str(meta.get("seal") or "")
    actual = seal_of(meta.get("_body", ""))
    if not declared:
        raise ProtocolError(EXIT_TAMPERED, "mệnh lệnh thiếu seal — không kiểm được toàn vẹn")
    if declared != actual:
        raise ProtocolError(
            EXIT_TAMPERED,
            "seal không khớp: nội dung mệnh lệnh đã bị thay đổi sau khi Hermes ban hành "
            f"(khai báo {declared[:19]}…, thực tế {actual[:19]}…)",
        )

    try:
        valid_until = parse_ts(str(meta.get("valid_until") or ""))
    except Exception:
        raise ProtocolError(EXIT_MISSING, "mệnh lệnh thiếu valid_until hợp lệ")

    if when > valid_until:
        raise ProtocolError(
            EXIT_STALE,
            f"mệnh lệnh {meta.get('id')} đã hết hạn ({human_delta(when - valid_until)})",
        )

    try:
        issued_at = parse_ts(str(meta.get("issued_at") or ""))
    except Exception:
        issued_at = valid_until

    if (when - issued_at) > dt.timedelta(hours=max_age_hours):
        raise ProtocolError(
            EXIT_STALE,
            f"mệnh lệnh đã cũ hơn {max_age_hours} giờ ({human_delta(when - issued_at)})",
        )


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(repo: Path, *args: str, timeout: int = 25) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, timeout=timeout,
    )


def repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
        if out:
            return Path(out).resolve()
    except Exception:
        pass
    return Path.cwd().resolve()


def fetch_remote(repo: Path, ref: str) -> bool:
    """Fetch `nhánh` về đúng remote-tracking ref `origin/<nhánh>`.

    `git fetch origin <branch>` chỉ cập nhật FETCH_HEAD, không tạo
    `refs/remotes/origin/<branch>` — nên phải chỉ định refspec đích.
    """
    if not ref:
        return False
    remote, _, branch = ref.partition("/")
    if not branch:
        remote, branch = "origin", ref
    result = git(repo, "fetch", "--depth=1", "--quiet", remote,
                 f"{branch}:refs/remotes/{remote}/{branch}")
    return result.returncode == 0


def show_remote_file(repo: Path, ref: str, rel: Path) -> str | None:
    result = git(repo, "show", f"{ref}:{rel.as_posix()}")
    return result.stdout if result.returncode == 0 else None


# ---------------------------------------------------------------------------
# Lệnh: boot
# ---------------------------------------------------------------------------

def _directive_from_text(text: str, source: str) -> tuple[dict[str, Any], str]:
    meta, body = split_front_matter(text)
    meta["_body"] = body
    meta["_source"] = source
    return meta, body


def _write_cache(handoff: Path, meta: dict[str, Any], source: str) -> None:
    cache = {
        "id": meta.get("id"),
        "number": meta.get("number"),
        "title": meta.get("title"),
        "issuer": meta.get("issuer"),
        "issued_at": meta.get("issued_at"),
        "valid_until": meta.get("valid_until"),
        "source": source,
        "cached_at": iso(now_utc()),
        "head": short_commit(handoff.parent.parent),
    }
    write_json(handoff / CACHE_DIRNAME / "active.json", cache)


def _log_boot(handoff: Path, payload: dict[str, Any]) -> None:
    cache_dir = handoff / CACHE_DIRNAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    with (cache_dir / "boot.log").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def print_banner(meta: dict[str, Any], when: dt.datetime, source: str) -> None:
    label = {
        "local": "repo (đã commit)",
        "remote": f"nhánh {DEFAULT_REMOTE_REF}",
        "live": "gọi trực tiếp Hermes",
    }.get(source, source)
    try:
        remaining = human_delta(parse_ts(str(meta.get("valid_until"))) - when)
    except Exception:
        remaining = "không rõ hạn"
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  MỆNH LỆNH TỪ HERMES — chủ của repo ZEUS                             ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"ID        : {meta.get('id')}  (#{meta.get('number', '?')})")
    print(f"Tiêu đề   : {meta.get('title')}")
    print(f"Ban hành  : {meta.get('issued_at')}  bởi {meta.get('issuer')}")
    print(f"Hiệu lực  : đến {meta.get('valid_until')} ({remaining})")
    print(f"Nguồn     : {label}")
    print(f"Seal      : OK ({str(meta.get('seal'))[:19]}…)")
    print()


def cmd_boot(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    handoff = repo / HANDOFF_REL
    when = now_utc()

    state = read_json(handoff / STATE_NAME)
    errors: list[tuple[int, str]] = []
    chosen: tuple[dict[str, Any], str] | None = None

    # 1) Bản trong working tree
    try:
        meta, _ = load_directive(handoff)
        validate_directive(meta, state, when, args.max_age_hours)
        chosen = (meta, "local")
    except ProtocolError as exc:
        errors.append((exc.code, exc.message))
    except Exception as exc:  # noqa: BLE001
        errors.append((EXIT_MISSING, f"không đọc được INBOX.md: {exc}"))

    # 2) Nhánh trạng thái do workflow Hermes ghi
    if chosen is None and not args.no_fetch and not args.offline:
        if fetch_remote(repo, args.remote):
            remote_state_text = show_remote_file(repo, args.remote, HANDOFF_REL / STATE_NAME)
            remote_inbox_text = show_remote_file(repo, args.remote, HANDOFF_REL / INBOX_NAME)
            if remote_inbox_text:
                try:
                    remote_state = json.loads(remote_state_text) if remote_state_text else None
                    meta, _ = _directive_from_text(remote_inbox_text, "remote")
                    validate_directive(meta, remote_state, when, args.max_age_hours)
                    chosen = (meta, "remote")
                    if args.materialize:
                        (handoff / INBOX_NAME).write_text(remote_inbox_text, encoding="utf-8")
                        if remote_state_text:
                            (handoff / STATE_NAME).write_text(remote_state_text, encoding="utf-8")
                except ProtocolError as exc:
                    errors.append((exc.code, exc.message))
                except Exception as exc:  # noqa: BLE001
                    errors.append((EXIT_MISSING, f"nhánh {args.remote} hỏng: {exc}"))

    # 3) Gọi Hermes trực tiếp (chỉ khi bật rõ ràng)
    if chosen is None and args.live:
        meta = live_directive(repo, args)
        if meta is not None:
            chosen = (meta, "live")

    if chosen is None:
        return report_blocked(repo, handoff, errors, when)

    meta, source = chosen
    if not args.quiet:
        print_banner(meta, when, source)
        print(normalize_body(meta.get("_body", "")))
        print("─" * 72)
        print("Bắt buộc khi kết thúc phiên:")
        print('  bash scripts/hermes-session-closeout.sh --status DONE --summary "…"')
        print("Chi tiết: docs/HERMES_OWNER_PROTOCOL.md")
    else:
        print(normalize_body(meta.get("_body", "")))

    _write_cache(handoff, meta, source)
    _log_boot(handoff, {
        "at": iso(when), "event": "boot_ok", "id": meta.get("id"),
        "source": source, "branch": short_commit(repo), "cwd": str(Path.cwd()),
    })

    if args.json:
        print(json.dumps({
            "ok": True, "source": source, "id": meta.get("id"),
            "number": meta.get("number"), "title": meta.get("title"),
            "valid_until": meta.get("valid_until"),
            "body": normalize_body(meta.get("_body", "")),
        }, ensure_ascii=False, indent=2))
    return EXIT_OK


def _never_issued(state: dict[str, Any], reason: str) -> bool:
    """True khi chưa từng có mệnh lệnh nào (khác với mệnh lệnh bị lỗi/hết hạn).

    Phân biệt này quan trọng: thông báo cũ luôn nói "INBOX.md thiếu front matter",
    khiến Operator tưởng file hỏng trong khi nguyên nhân thật là workflow
    `hermes-owner-loop` chưa chạy thành công lần nào.
    """
    if (state or {}).get("active_directive"):
        return False
    if not (state or {}).get("history") and (state or {}).get("updated_by") in (None, "bootstrap"):
        return True
    return "thiếu front matter" in reason or "chưa có" in reason.lower()


def report_blocked(repo: Path, handoff: Path, errors: list[tuple[int, str]], when: dt.datetime) -> int:
    code, reason = EXIT_MISSING, "chưa có mệnh lệnh nào từ Hermes"
    for candidate_code, candidate_reason in errors:
        if candidate_code != EXIT_MISSING:
            code, reason = candidate_code, candidate_reason
            break
    else:
        if errors:
            code, reason = errors[0]

    state = read_json(handoff / STATE_NAME) or {}
    first_time = _never_issued(state, reason)

    print()
    print("⛔ KHÔNG CÓ MỆNH LỆNH HỢP LỆ TỪ HERMES — DỪNG PHIÊN NGAY")
    print("─" * 72)
    if first_time:
        print("Chẩn đoán : CHƯA TỪNG có mệnh lệnh nào được ban hành")
        print("            (STATE.json chưa có active_directive/history)")
    else:
        print(f"Lý do      : {reason}")
    print(f"Thời điểm  : {iso(when)}")
    print(f"Repo       : {repo}")
    print()
    print("Việc Operator cần làm (1 lần):")
    print("  1. Mở tab Actions → workflow “Hermes owner loop”")
    print("     https://github.com/ZeusopenAI/ZEUS/actions/workflows/hermes-owner-loop.yml")
    print("  2. Bấm “Run workflow” → ở ô chọn branch, chọn đúng nhánh đang chứa")
    print("     bản sửa lỗi tách mệnh lệnh (workflow chạy theo branch được chọn,")
    print("     KHÔNG phải theo main).")
    print("  3. Chờ ~2 phút, rồi chạy lại:  bash scripts/hermes-session-boot.sh")
    print("  4. Muốn khỏi lặp lại mỗi phiên: đặt biến repo HERMES_OWNER_AUTO=on")
    print("     (Settings → Secrets and variables → Actions → Variables) để")
    print("     workflow tự chạy mỗi 6 giờ và mỗi khi OUTBOX.md đổi.")
    print()
    print("Chẩn đoán nhanh (1 lệnh):  bash scripts/hermes-owner-status.sh")
    print()
    print("Agent: KHÔNG sửa code, KHÔNG commit, KHÔNG tự đặt mục tiêu thay chủ.")
    print("Chỉ được báo lại nguyên văn khối này cho Operator.")
    print()
    _log_boot(handoff, {
        "at": iso(when), "event": "boot_blocked", "code": code, "reason": reason,
        "first_time": first_time, "cwd": str(Path.cwd()),
    })
    return code


# ---------------------------------------------------------------------------
# Live mode (tuỳ chọn — cần binary hermes + key provider)
# ---------------------------------------------------------------------------

LIVE_PROMPT = """Bạn là Hermes, CHỦ của repo ZEUS. Một phiên agent Arena vừa mở và xin mệnh lệnh.

Bối cảnh repo:
{brief}

Hãy ban hành ĐÚNG MỘT mệnh lệnh, ngắn, kiểm chứng được, và chỉ in phần giữa hai dòng đánh dấu:

<<<ZEUS_DIRECTIVE>>>
# MỆNH LỆNH — <tiêu đề ngắn>

## Mục tiêu
<1 câu>

## Việc phải làm (theo thứ tự, tối đa 5)
1. …
2. …

## Không được làm
- …

## Bằng chứng hoàn thành
- <lệnh kiểm tra / kết quả mong đợi>
<<<END_ZEUS_DIRECTIVE>>>
"""


# Model hay làm lệch marker: thêm dấu cách (<<< ZEUS_DIRECTIVE >>>), bọc đậm/nghiêng
# (**<<<ZEUS_DIRECTIVE>>>**), đổi khoảng trắng thành gạch dưới, hoặc viết hoa/thường khác.
# Parser phải chịu được các biến thể đó, nếu không cả phiên agent bị chặn (xem
# docs/HERMES_OWNER_PROTOCOL.md — boot trả mã 3 khi không tách được khối).
_DIRECTIVE_OPEN_RE = re.compile(
    r"<<<[^<>\n]{0,8}ZEUS[ _-]{0,3}DIRECTIVE[^<>\n]{0,8}>>>",
    re.IGNORECASE,
)
_DIRECTIVE_CLOSE_RE = re.compile(
    r"<<<[^<>\n]{0,8}END[ _-]{0,3}ZEUS[ _-]{0,3}DIRECTIVE[^<>\n]{0,8}>>>",
    re.IGNORECASE,
)
# Dự phòng khi model bỏ hẳn marker: lấy từ tiêu đề mệnh lệnh, nhưng chỉ khi có
# ít nhất một mục bắt buộc — tránh nhặt nhầm câu văn xuôi có nhắc "MỆNH LỆNH".
_DIRECTIVE_HEADING_RE = re.compile(
    r"^[ \t]*#{1,3}[ \t]*\**[ \t]*M[ỆE]NH[ \t]+L[ỆE]NH\b",
    re.IGNORECASE | re.MULTILINE,
)
_DIRECTIVE_REQUIRED_HINTS = ("## Mục tiêu", "## Việc phải làm", "## Bằng chứng")


_MARKDOWN_FILLER_LINES = {"", "*", "**", "***", "_", "__", "___", "---", "***"}


def _strip_code_fence(body: str) -> str:
    """Bỏ hàng rào ``` và dòng trang trí markdown (** __ ---) ở hai đầu khối."""
    lines = body.strip().splitlines()

    def drop_edges(lines: list[str]) -> list[str]:
        start = 0
        while start < len(lines) and (
            lines[start].strip() in _MARKDOWN_FILLER_LINES
            or lines[start].strip().startswith("```")
        ):
            start += 1
        end = len(lines)
        while end > start and (
            lines[end - 1].strip() in _MARKDOWN_FILLER_LINES
            or lines[end - 1].strip().startswith("```")
        ):
            end -= 1
        return lines[start:end]

    return "\n".join(drop_edges(lines)).strip()


def _has_directive_sections(text: str) -> bool:
    return any(hint in text for hint in _DIRECTIVE_REQUIRED_HINTS)


def _extract_directive(text: str) -> str | None:
    """Tách thân mệnh lệnh khỏi output của Hermes.

    Chấp nhận: marker chuẩn, marker có dấu cách/gạch dưới/bọc đậm, khối bọc trong
    code fence, và (dự phòng) output không có marker nhưng có tiêu đề + mục bắt buộc.
    """
    if not text or not text.strip():
        return None

    open_match = _DIRECTIVE_OPEN_RE.search(text)
    if open_match:
        rest = text[open_match.end():]
        close_match = _DIRECTIVE_CLOSE_RE.search(rest)
        body = rest[: close_match.start()] if close_match else rest
        body = _strip_code_fence(body)
        return body or None

    heading = _DIRECTIVE_HEADING_RE.search(text)
    if heading:
        candidate = _strip_code_fence(text[heading.start():])
        if candidate and _has_directive_sections(candidate):
            return candidate
    return None


def live_directive(repo: Path, args: argparse.Namespace) -> dict[str, Any] | None:
    binary = shutil.which("hermes") or os.environ.get("HERMES_OWNER_HERMES_BIN", "")
    if not binary:
        print("⚠ Không tìm thấy binary `hermes` — bỏ qua chế độ gọi trực tiếp.", file=sys.stderr)
        return None
    if not any(os.environ.get(key) for key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")):
        print("⚠ Không có API key provider trong môi trường — bỏ qua chế độ gọi trực tiếp.", file=sys.stderr)
        return None

    brief_parts = [
        f"- Thời điểm: {iso(now_utc())}",
        f"- Nhánh: {short_commit(repo)}",
    ]
    for rel in ("Status.md", "TODO.md"):
        path = repo / rel
        if path.exists():
            excerpt = path.read_text(encoding="utf-8", errors="replace")[:3000]
            brief_parts.append(f"\n### {rel}\n```markdown\n{excerpt}\n```")
    prompt = LIVE_PROMPT.format(brief="\n".join(brief_parts))

    model = os.environ.get("HERMES_OWNER_MODEL", "google/gemini-2.5-flash")
    cmd = [binary, "-z", prompt, "-m", model, "--provider", "openrouter", "-t", "safe"]
    try:
        result = subprocess.run(
            cmd, cwd=str(repo), capture_output=True, text=True,
            timeout=int(os.environ.get("HERMES_OWNER_LIVE_TIMEOUT", "300")),
        )
    except subprocess.TimeoutExpired:
        print("⚠ Gọi Hermes trực tiếp quá thời gian — bỏ qua.", file=sys.stderr)
        return None
    if result.returncode != 0:
        print(f"⚠ Hermes trả mã lỗi {result.returncode} — bỏ qua chế độ trực tiếp.", file=sys.stderr)
        return None
    body = _extract_directive(result.stdout)
    if not body:
        print("⚠ Hermes không trả về khối mệnh lệnh đúng định dạng — bỏ qua.", file=sys.stderr)
        return None
    return issue_directive(
        repo=repo,
        body=body,
        title=_title_of(body) or "Mệnh lệnh trực tiếp",
        ttl_hours=DEFAULT_TTL_HOURS,
        source_run="live",
        model=model,
        issuer="hermes",
        write_files=False,
    )


def _title_of(body: str) -> str | None:
    for line in body.splitlines():
        text = line.strip()
        if text.startswith("#"):
            return re.sub(r"^#+\s*", "", text).strip()
        if text:
            return text[:80]
    return None


# ---------------------------------------------------------------------------
# Lệnh: issue (workflow dùng)
# ---------------------------------------------------------------------------

def issue_directive(
    repo: Path,
    body: str,
    title: str,
    ttl_hours: int = DEFAULT_TTL_HOURS,
    source_run: str = "manual",
    model: str = "",
    issuer: str = "hermes",
    number: int | None = None,
    write_files: bool = True,
) -> dict[str, Any]:
    handoff = repo / HANDOFF_REL
    handoff.mkdir(parents=True, exist_ok=True)
    state = read_json(handoff / STATE_NAME) or empty_state()
    history = [item for item in (state.get("history") or []) if isinstance(item, dict)]
    active = state.get("active_directive") or {}

    numbers = [int(item.get("number") or 0) for item in history]
    numbers.append(int(active.get("number") or 0))
    next_number = number if number is not None else (max(numbers) + 1 if numbers else 1)

    issued = now_utc()
    valid_until = issued + dt.timedelta(hours=ttl_hours)
    directive_id = f"hermes-{issued.strftime('%Y%m%dT%H%MZ')}-{secrets.token_hex(2)}"
    normalized = normalize_body(body)

    meta: dict[str, Any] = {
        "protocol": PROTOCOL,
        "schema": SCHEMA,
        "id": directive_id,
        "number": next_number,
        "issuer": issuer,
        "title": (title or "Mệnh lệnh").replace("\n", " ").strip()[:160],
        "issued_at": iso(issued),
        "valid_until": iso(valid_until),
        "seal": seal_of(normalized),
        "model": model or "",
        "source_run": source_run or "",
    }
    text = build_inbox(meta, normalized)

    if write_files:
        (handoff / INBOX_NAME).write_text(text, encoding="utf-8")
        archive_dir = handoff / ARCHIVE_DIRNAME
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / f"INBOX-{directive_id}.md").write_text(text, encoding="utf-8")

    record = {key: meta[key] for key in meta if key != "seal"}
    record["seal"] = meta["seal"]
    record["file"] = (HANDOFF_REL / INBOX_NAME).as_posix()

    state["protocol"] = PROTOCOL
    state["schema"] = SCHEMA
    state["active_directive"] = record
    if active and active.get("id") != directive_id:
        history.insert(0, {
            "id": active.get("id"), "number": active.get("number"),
            "title": active.get("title"), "issued_at": active.get("issued_at"),
            "valid_until": active.get("valid_until"),
            "superseded_at": iso(issued),
        })
    state["history"] = history[:HISTORY_LIMIT]
    state["updated_at"] = iso(issued)
    state["updated_by"] = f"{issuer}(issue)"

    if write_files:
        write_json(handoff / STATE_NAME, state)
    return {"meta": meta, "text": text, "state": state}


def cmd_issue(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    if args.body_file and args.body_file != "-":
        body = Path(args.body_file).read_text(encoding="utf-8")
    else:
        body = sys.stdin.read()
    if not body.strip():
        raise ProtocolError(EXIT_USAGE, "nội dung mệnh lệnh rỗng")
    title = args.title or _title_of(body) or "Mệnh lệnh"
    result = issue_directive(
        repo=repo, body=body, title=title, ttl_hours=args.ttl_hours,
        source_run=args.source_run, model=args.model, issuer=args.issuer,
        number=args.number,
    )
    meta = result["meta"]
    if not args.quiet:
        print(f"✅ Đã ban hành mệnh lệnh #{meta['number']} — {meta['id']}")
        print(f"   Tiêu đề : {meta['title']}")
        print(f"   Hiệu lực: {meta['issued_at']} → {meta['valid_until']}")
        print(f"   Seal    : {meta['seal'][:23]}…")
        print(f"   File    : {HANDOFF_REL / INBOX_NAME}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Lệnh: closeout
# ---------------------------------------------------------------------------

def _git_summary(repo: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    try:
        info["branch"] = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "?"
        info["head"] = short_commit(repo)
        info["changes"] = git(repo, "status", "--porcelain=v1").stdout.strip() or "(sạch)"
        diff = git(repo, "diff", "--stat", "HEAD").stdout.strip()
        info["diffstat"] = diff or "(không có thay đổi chưa commit)"
        base = git(repo, "merge-base", "HEAD", "origin/main").stdout.strip()
        if base:
            stat = git(repo, "diff", "--stat", f"{base}..HEAD").stdout.strip()
            info["branch_diffstat"] = stat or "(nhánh chưa khác main)"
            log = git(repo, "log", "--oneline", f"{base}..HEAD").stdout.strip()
            info["commits"] = log or "(chưa có commit mới)"
    except Exception:
        pass
    return info


def _active_id_cache_or_state(handoff: Path, state: dict[str, Any]) -> tuple[str, str]:
    active = state.get("active_directive") or {}
    if active.get("id"):
        return str(active.get("id")), str(active.get("title") or "")
    cache = read_json(handoff / CACHE_DIRNAME / "active.json") or {}
    return str(cache.get("id") or "không xác định"), str(cache.get("title") or "")


def cmd_closeout(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    handoff = repo / HANDOFF_REL
    handoff.mkdir(parents=True, exist_ok=True)
    state = read_json(handoff / STATE_NAME) or empty_state()

    directive_id, directive_title = _active_id_cache_or_state(handoff, state)
    if args.directive_id:
        directive_id = args.directive_id

    summary = args.summary or ""
    if args.summary_file:
        summary = Path(args.summary_file).read_text(encoding="utf-8").strip()
    if not summary and not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            summary = piped
    if not summary:
        raise ProtocolError(EXIT_USAGE, "thiếu --summary / --summary-file (hoặc stdin)")

    status = args.status.upper()
    if status not in {"DONE", "PARTIAL", "BLOCKED"}:
        raise ProtocolError(EXIT_USAGE, "--status phải là DONE | PARTIAL | BLOCKED")

    git_info = _git_summary(repo)
    stamp = now_utc()
    report_id = f"arena-{stamp.strftime('%Y%m%dT%H%MZ')}-{secrets.token_hex(2)}"

    bullets = [
        ("Mệnh lệnh", f"{directive_id} — {directive_title}".strip(" —")),
        ("Thời điểm", iso(stamp)),
        ("Nhánh", git_info.get("branch")),
        ("HEAD", git_info.get("head")),
        ("Tóm tắt", summary.replace("\n", " ")),
        ("Đã kiểm chứng", args.tests),
        ("Câu hỏi cho chủ", args.questions),
        ("Blocker", args.blocker),
    ]
    meta_block = [f"- **{name}:** {value}" for name, value in bullets if value]
    git_block = [
        (git_info.get("changes") or "").strip(),
        (git_info.get("diffstat") or "").strip(),
        (git_info.get("branch_diffstat") or "").strip(),
        (git_info.get("commits") or "").strip(),
    ]
    lines = [
        REPORT_START,
        f"## {report_id} — {status}",
        "",
        *meta_block,
        "",
        "<details><summary>Trạng thái git</summary>",
        "",
        "```",
        *[line for line in git_block if line],
        "```",
        "",
        "</details>",
        REPORT_END,
        "",
    ]
    report = "\n".join(lines) + "\n"

    outbox = handoff / OUTBOX_NAME
    if outbox.exists():
        current = outbox.read_text(encoding="utf-8")
    else:
        current = OUTBOX_HEADER + "\n"
    marker = REPORT_RE.search(current)
    if marker:
        head = current[: marker.start()]
        current = head + report + current[marker.start():]
    else:
        current = current.rstrip() + "\n\n" + report
    outbox.write_text(current, encoding="utf-8")

    state["last_report"] = {
        "id": report_id,
        "at": iso(stamp),
        "status": status,
        "directive_id": directive_id,
        "branch": git_info.get("branch"),
        "head": git_info.get("head"),
        "summary": summary.replace("\n", " ")[:400],
    }
    state["updated_at"] = iso(stamp)
    state["updated_by"] = "arena(closeout)"
    write_json(handoff / STATE_NAME, state)

    committed = False
    if args.commit:
        git(repo, "add", HANDOFF_REL.as_posix())
        message = f"chore(hermes-owner): báo cáo {status} cho {directive_id}"
        result = git(repo, "commit", "-m", message)
        committed = result.returncode == 0
        if not committed and result.stdout.strip():
            print(result.stdout.strip(), file=sys.stderr)

    print(f"✅ Đã ghi báo cáo {report_id} ({status}) cho mệnh lệnh {directive_id}")
    print(f"   File: {HANDOFF_REL / OUTBOX_NAME}")
    if args.commit:
        print(f"   Commit: {'có' if committed else 'không (không có gì để commit)'}")
    else:
        print("   Chưa commit. Arena sẽ tự lưu file; muốn ghi vào git: thêm --commit")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Lệnh: status
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    handoff = repo / HANDOFF_REL
    when = now_utc()
    state = read_json(handoff / STATE_NAME) or {}
    active = state.get("active_directive") or {}

    print("Hermes Owner Protocol — trạng thái")
    print("─" * 60)
    print(f"Repo        : {repo}")
    print(f"Bây giờ     : {iso(when)}")
    if not active:
        print("Mệnh lệnh   : (chưa có)")
    else:
        print(f"Mệnh lệnh   : #{active.get('number')} — {active.get('title')}")
        print(f"ID          : {active.get('id')}")
        print(f"Ban hành    : {active.get('issued_at')} bởi {active.get('issuer')}")
        try:
            print(f"Hiệu lực    : đến {active.get('valid_until')} ({human_delta(parse_ts(str(active.get('valid_until'))) - when)})")
        except Exception:
            print(f"Hiệu lực    : đến {active.get('valid_until')}")
    last = state.get("last_report") or {}
    if last:
        print(f"Báo cáo cuối: {last.get('status')} lúc {last.get('at')} bởi {last.get('branch')}")
    else:
        print("Báo cáo cuối: (chưa có)")

    code = EXIT_OK
    try:
        meta, _ = load_directive(handoff)
        validate_directive(meta, state or None, when, args.max_age_hours)
        print("Kiểm tra    : ✅ hợp lệ, dùng được ngay")
    except ProtocolError as exc:
        code = exc.code
        print(f"Kiểm tra    : ❌ {exc.message}")
    return code if args.strict else EXIT_OK


# ---------------------------------------------------------------------------
# Lệnh: extract (workflow dùng để tách khối mệnh lệnh từ output của Hermes)
# ---------------------------------------------------------------------------

DIRECTIVE_START = "<<<ZEUS_DIRECTIVE>>>"
DIRECTIVE_END = "<<<END_ZEUS_DIRECTIVE>>>"


def cmd_extract(args: argparse.Namespace) -> int:
    raw = Path(args.input).read_text(encoding="utf-8", errors="replace") if args.input != "-" else sys.stdin.read()
    body = _extract_directive(raw)
    if not body:
        preview = "\n".join(raw.strip().splitlines()[:15]) or "(rỗng)"
        raise ProtocolError(
            EXIT_MISSING,
            f"output của Hermes không có khối {DIRECTIVE_START} … {DIRECTIVE_END} "
            "và cũng không có tiêu đề '# MỆNH LỆNH' kèm mục bắt buộc.\n"
            f"--- 15 dòng đầu output ---\n{preview}",
        )
    if args.output:
        Path(args.output).write_text(normalize_body(body), encoding="utf-8")
    if args.title_out:
        Path(args.title_out).write_text((_title_of(body) or "Mệnh lệnh") + "\n", encoding="utf-8")
    if not args.output:
        print(normalize_body(body), end="")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Lệnh: selftest
# ---------------------------------------------------------------------------

def cmd_selftest(args: argparse.Namespace) -> int:
    failures = 0

    def check(name: str, condition: bool) -> None:
        nonlocal failures
        print(("  ✓ " if condition else "  ✗ ") + name)
        failures += 0 if condition else 1

    print("Hermes Owner Protocol — selftest")
    body = "# MỆNH LỆNH — thử\n\n## Mục tiêu\nKiểm tra seal.\n"
    sealed = seal_of(body)
    check("seal ổn định giữa 2 lần", sealed == seal_of(body + "\n\n"))
    check("seal đổi khi nội dung đổi", sealed != seal_of(body + "x"))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".ai/handoff").mkdir(parents=True)
        result = issue_directive(root, body, "Thử", ttl_hours=1, write_files=True)
        check("issue ghi INBOX", (root / HANDOFF_REL / INBOX_NAME).exists())
        check("issue ghi archive", any((root / HANDOFF_REL / ARCHIVE_DIRNAME).iterdir()))
        state = read_json(root / HANDOFF_REL / STATE_NAME) or {}
        check("STATE có directive hiện hành", (state.get("active_directive") or {}).get("id") == result["meta"]["id"])

        meta, _ = load_directive(root / HANDOFF_REL)
        try:
            validate_directive(meta, state, now_utc())
            check("validate bản hợp lệ", True)
        except ProtocolError:
            check("validate bản hợp lệ", False)

        tampered = (root / HANDOFF_REL / INBOX_NAME).read_text(encoding="utf-8") + "\nThêm dòng lạ.\n"
        (root / HANDOFF_REL / INBOX_NAME).write_text(tampered, encoding="utf-8")
        try:
            validate_directive(load_directive(root / HANDOFF_REL)[0], state, now_utc())
            check("bắt được sửa tay (seal)", False)
        except ProtocolError as exc:
            check("bắt được sửa tay (seal)", exc.code == EXIT_TAMPERED)

    print("\nKết quả:", "OK" if failures == 0 else f"{failures} lỗi")
    return EXIT_OK if failures == 0 else 1


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def _add_repo_flag(parser: argparse.ArgumentParser) -> None:
    """Cho phép đặt --repo sau subcommand, không ghi đè giá trị đặt trước đó."""
    parser.add_argument(
        "--repo", default=argparse.SUPPRESS,
        help="Đường dẫn repo (mặc định: git toplevel của CWD)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes_owner.py", description="Hermes Owner Protocol engine")
    parser.add_argument("--repo", help="Đường dẫn repo (mặc định: git toplevel của CWD)")
    sub = parser.add_subparsers(dest="command", required=True)

    boot = sub.add_parser("boot", help="BƯỚC 0 của mọi phiên agent")
    boot.add_argument("--no-fetch", action="store_true", help="Không fetch nhánh trạng thái từ origin")
    boot.add_argument("--offline", action="store_true", help="Không dùng mạng (tương đương --no-fetch)")
    boot.add_argument("--remote", default=DEFAULT_REMOTE_REF, help=f"Nhánh trạng thái (mặc định {DEFAULT_REMOTE_REF})")
    boot.add_argument("--live", action="store_true", help="Cho phép gọi Hermes trực tiếp nếu có binary + key")
    boot.add_argument("--materialize", action="store_true", help="Ghi bản remote vào working tree")
    boot.add_argument("--max-age-hours", type=int, default=MAX_AGE_HOURS, help="Tuổi tối đa của mệnh lệnh")
    boot.add_argument("--quiet", action="store_true", help="Chỉ in nội dung mệnh lệnh")
    boot.add_argument("--json", action="store_true", help="In thêm JSON máy đọc")
    _add_repo_flag(boot)
    boot.set_defaults(func=cmd_boot)

    status = sub.add_parser("status", help="Xem trạng thái")
    status.add_argument("--strict", action="store_true", help="Trả mã lỗi nếu mệnh lệnh không hợp lệ")
    status.add_argument("--max-age-hours", type=int, default=MAX_AGE_HOURS)
    _add_repo_flag(status)
    status.set_defaults(func=cmd_status)

    issue = sub.add_parser("issue", help="Ban hành mệnh lệnh mới")
    issue.add_argument("--body-file", default="-", help="File nội dung (mặc định: stdin)")
    issue.add_argument("--title", default="")
    issue.add_argument("--ttl-hours", type=int, default=DEFAULT_TTL_HOURS)
    issue.add_argument("--source-run", default="manual")
    issue.add_argument("--model", default="")
    issue.add_argument("--issuer", default="hermes")
    issue.add_argument("--number", type=int, default=None)
    issue.add_argument("--quiet", action="store_true")
    _add_repo_flag(issue)
    issue.set_defaults(func=cmd_issue)

    closeout = sub.add_parser("closeout", help="Ghi báo cáo kết phiên")
    closeout.add_argument("--status", default="DONE", help="DONE | PARTIAL | BLOCKED")
    closeout.add_argument("--summary", default="")
    closeout.add_argument("--summary-file", default="")
    closeout.add_argument("--tests", default="")
    closeout.add_argument("--questions", default="")
    closeout.add_argument("--blocker", default="")
    closeout.add_argument("--directive-id", default="")
    closeout.add_argument("--commit", action="store_true", help="git add + commit .ai/handoff")
    _add_repo_flag(closeout)
    closeout.set_defaults(func=cmd_closeout)

    extract = sub.add_parser("extract", help="Tách khối mệnh lệnh từ output Hermes")
    extract.add_argument("--input", default="-", help="File output (mặc định: stdin)")
    extract.add_argument("--output", default="", help="Ghi thân mệnh lệnh ra file")
    extract.add_argument("--title-out", default="", help="Ghi tiêu đề ra file")
    _add_repo_flag(extract)
    extract.set_defaults(func=cmd_extract)

    selftest = sub.add_parser("selftest", help="Tự kiểm tra")
    _add_repo_flag(selftest)
    selftest.set_defaults(func=cmd_selftest)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "repo"):
        args.repo = None
    try:
        return int(args.func(args))
    except ProtocolError as exc:
        print(f"❌ {exc.message}", file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
