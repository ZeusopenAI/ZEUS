#!/usr/bin/env python3
"""Dựng bản giao ban cho Hermes (kênh cố vấn TÙY CHỌN) trước khi Hermes gợi ý.

Được workflow `.github/workflows/hermes-owner-loop.yml` gọi. Không gọi LLM,
không tốn token — chỉ đọc repo + git + gh rồi ghi ra file.

    python3 scripts/hermes_owner_brief.py \
        --out-brief .ai/handoff/.tmp/brief.md \
        --out-prompt .ai/handoff/.tmp/prompt.txt \
        --operator-note "ưu tiên việc X"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

PROMPT_TEMPLATE = """Bạn là **Hermes — CỐ VẤN TÙY CHỌN** cho repo ZEUS (Operator: Nguyễn Quang Quý).
Bạn KHÔNG phải chủ của phiên: quyền cao nhất luôn là Operator / người dùng trong phiên chat.
Một agent đang hỏi ý kiến tham khảo và **có thể nghe hoặc bỏ qua**. Bạn KHÔNG thực thi code
trong lượt này; nhiệm vụ duy nhất là **gợi ý đúng một bản kế hoạch** cho phiên đó.

## Luật gợi ý

1. Tối đa **5 việc**, sắp theo thứ tự ưu tiên. Việc nào cũng phải có bằng chứng kiểm chứng
   (lệnh chạy được + kết quả mong đợi), không viết "cải thiện", "tối ưu" chung chung.
2. Mỗi gợi ý chỉ nên hoàn thành trong **một phiên** (≤ 2 giờ làm việc của agent).
   Việc lớn thì cắt phần nhỏ nhất có giá trị và ghi phần còn lại vào `## Việc tiếp theo`.
3. Tôn trọng `.ai/CONSTITUTION.md` và `AGENTS.md`: không xoá dữ liệu, không đổi secrets,
   không deploy production, không push thẳng `main`.
4. **Không được yêu cầu agent dừng phiên, chờ lệnh, hay từ chối yêu cầu trực tiếp của Operator.**
   Nếu không có gợi ý hợp lệ, agent vẫn phải tiếp tục làm việc bình thường (Hermes không bắt buộc).
5. Nếu báo cáo trước cho thấy việc đã xong hoặc bị chặn, gợi ý mới phải phản ánh điều đó —
   đừng lặp lại việc cũ.
6. Không đưa bí mật, token, hay nội dung riêng tư vào gợi ý. Nội dung được commit công khai.

## Định dạng đầu ra (BẮT BUỘC — chỉ in đúng khối này, không thêm lời dẫn)

Quy tắc máy kiểm: hai dòng marker phải **đứng riêng một dòng**, viết đúng từng ký tự
`<<<ZEUS_DIRECTIVE>>>` và `<<<END_ZEUS_DIRECTIVE>>>` — không thêm dấu cách bên trong,
không bọc trong `**…**` hay ``` ``` ```, không đổi sang tiếng Việt.
Parser vẫn chịu biến thể lệch chuẩn, nhưng đúng chuẩn thì chắc chắn được.

<<<ZEUS_DIRECTIVE>>>
# MỆNH LỆNH #<số> — <tiêu đề ngắn, ≤ 60 ký tự>

## Mục tiêu
<1 câu, nói rõ kết quả cuối cùng>

## Việc phải làm (theo thứ tự)
1. <việc> — kiểm chứng: `<lệnh>` → <kết quả mong đợi>
2. …

## Không được làm
- <ranh giới cụ thể của phiên này>

## Bằng chứng hoàn thành
- <điều kiện tối thiểu để báo DONE>

## Việc tiếp theo (để phiên sau)
- <nếu còn>
<<<END_ZEUS_DIRECTIVE>>>

---

# BẢN GIAO BAN

{body}
"""


def run(cmd: list[str], cwd: Path, timeout: int = 20) -> str:
    try:
        result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 40].rstrip() + "\n… (đã lược bớt)"


def read_excerpt(path: Path, limit: int) -> str:
    try:
        return clip(path.read_text(encoding="utf-8", errors="replace"), limit)
    except FileNotFoundError:
        return "(không có file)"


def latest_reports(outbox: Path, limit: int) -> list[str]:
    try:
        text = outbox.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    blocks = re.findall(
        r"(?ms)^<!-- report:start -->[ \t]*$(.*?)^<!-- report:end -->[ \t]*$", text
    )
    return [clip(block.strip(), 1400) for block in blocks[:limit]]


def open_prs(repo: Path, limit: int) -> str:
    raw = run(["gh", "pr", "list", "--state", "open", "--limit", str(limit),
               "--json", "number,title,headRefName,updatedAt,isDraft"], repo)
    if not raw:
        return "(không đọc được danh sách PR — bỏ qua)"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "(json PR không hợp lệ)"
    if not data:
        return "(không có PR mở)"
    lines = []
    for pr in data:
        draft = " [draft]" if pr.get("isDraft") else ""
        lines.append(f"- #{pr.get('number')} {pr.get('title')} — nhánh `{pr.get('headRefName')}`{draft}")
    return "\n".join(lines)


def recent_commits(repo: Path, limit: int) -> str:
    return run(["git", "log", f"-{limit}", "--pretty=format:- %h %ad %s", "--date=short"], repo) or "(không có)"


def changed_files(repo: Path, limit: int) -> str:
    raw = run(["git", "status", "--porcelain=v1"], repo)
    if not raw:
        return "(working tree sạch)"
    lines = raw.splitlines()[:limit]
    return "\n".join(f"- `{line}`" for line in lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build owner brief for Hermes")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--operator-note", default="", help="Ghi chú/ưu tiên của Operator cho lượt này")
    parser.add_argument("--out-brief", default=".ai/handoff/.tmp/brief.md")
    parser.add_argument("--out-prompt", default=".ai/handoff/.tmp/prompt.txt")
    parser.add_argument("--max-reports", type=int, default=3)
    parser.add_argument("--max-chars", type=int, default=26000)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    handoff = repo / ".ai" / "handoff"
    stamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    state: dict = {}
    try:
        state = json.loads((handoff / "STATE.json").read_text(encoding="utf-8"))
    except Exception:
        state = {}
    active = state.get("active_directive") or {}

    reports = latest_reports(handoff / "OUTBOX.md", args.max_reports)
    reports_text = "\n\n".join(reports) if reports else "(chưa có báo cáo nào từ phiên agent)"

    sections = [
        ("Thời điểm", stamp),
        ("Repo", f"{repo} · nhánh `{run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], repo) or '?'}`"
                 f" · HEAD `{run(['git', 'rev-parse', '--short', 'HEAD'], repo) or '?'}`"),
        ("Mệnh lệnh trước đó",
         f"#{active.get('number')} — {active.get('title')} (id `{active.get('id')}`, "
         f"hết hạn {active.get('valid_until')})" if active else "(chưa có)"),
        ("Ghi chú của Operator cho lượt này", args.operator_note or "(không có)"),
        ("Báo cáo gần nhất từ các phiên agent (mới nhất trước)", reports_text),
        ("Pull request đang mở", open_prs(repo, 10)),
        ("Commit gần đây", recent_commits(repo, 12)),
        ("Thay đổi chưa commit", changed_files(repo, 25)),
        ("Status.md", read_excerpt(repo / "Status.md", 2600)),
        ("TODO.md", read_excerpt(repo / "TODO.md", 2200)),
        ("Roadmap.md", read_excerpt(repo / "Roadmap.md", 1200)),
        ("Hiến pháp (.ai/CONSTITUTION.md)", read_excerpt(repo / ".ai" / "CONSTITUTION.md", 1200)),
        ("Kỹ năng có sẵn",
         ", ".join(sorted(p.parent.name for p in (repo / "skills").glob("*/SKILL.md"))) or "(không có)"),
    ]

    size_budget = max(args.max_chars - len(PROMPT_TEMPLATE) - 200, 4000)
    body_parts: list[str] = []
    used = 0
    for title, value in sections:
        block = f"## {title}\n{value.strip()}\n"
        if used + len(block) > size_budget:
            block = block[: max(size_budget - used - 30, 0)].rstrip() + "\n… (cắt bớt do giới hạn)\n"
        if not block.strip():
            continue
        body_parts.append(block)
        used += len(block)
    body = "\n".join(body_parts)

    brief_path = repo / args.out_brief
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(f"# Bản giao ban cho Hermes\n\n{body}", encoding="utf-8")

    prompt_path = repo / args.out_prompt
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(PROMPT_TEMPLATE.format(body=body), encoding="utf-8")

    print(f"Brief : {brief_path} ({len(body)} ký tự)")
    print(f"Prompt: {prompt_path} ({prompt_path.stat().st_size} bytes)")
    print(f"Reports đã nạp: {len(reports)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
