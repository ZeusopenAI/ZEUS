#!/usr/bin/env python3
"""Kiểm tra frontmatter của mọi skill trong skills/.

Không cần PyYAML: parser tối giản, chỉ đọc các dạng dùng thật trong repo
(`key: value`, `key: |` block scalar). Chạy được trên CI lẫn máy cá nhân.

    python3 scripts/validate-skills.py            # kiểm tra toàn bộ
    python3 scripts/validate-skills.py --strict   # coi warning là lỗi
    python3 scripts/validate-skills.py skills/edit-anh

Quy tắc kiểm (theo giới hạn Hermes: agents/hermes/tools/skills_tool.py):
  - SKILL.md phải có frontmatter --- ... ---
  - `name` bắt buộc, <= 64 ký tự, chỉ [a-z0-9-], không trùng nhau
  - `description` bắt buộc, <= 1024 ký tự
  - link nội bộ dạng [x](file.md) phải trỏ tới file có thật
  - thân skill phải có nội dung thực chất (> 200 ký tự)

Mã thoát: 0 = OK, 1 = có lỗi.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAX_NAME = 64
MAX_DESCRIPTION = 1024
MIN_BODY = 200
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SKIP_PARTS = {"references", "templates", "assets", "scripts", "node_modules", ".venv"}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Trả về (frontmatter, body). Không có frontmatter -> ({}, text)."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end = idx
            break
    if end is None:
        return {}, text

    data: dict[str, str] = {}
    key = None
    buffer: list[str] = []
    for raw in lines[1:end]:
        if raw[:1] in (" ", "\t") and key is not None:
            buffer.append(raw.strip())
            continue
        if key is not None:
            data[key] = "\n".join(buffer).strip()
            key, buffer = None, []
        if not raw or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        k, _, v = raw.partition(":")
        k = k.strip()
        v = v.strip()
        if v in ("|", ">", "|-", ">-", "|+", ">+"):
            key = k
            buffer = []
        else:
            data[k] = v.strip("'\"")

    if key is not None:
        data[key] = "\n".join(buffer).strip()

    return data, "\n".join(lines[end + 1 :])


def find_skill_files(targets: list[str]) -> list[Path]:
    found: list[Path] = []
    for target in targets or ["skills"]:
        path = Path(target)
        if path.is_file():
            found.append(path)
        elif path.is_dir():
            for md in sorted(path.rglob("SKILL.md")):
                if SKIP_PARTS & set(md.parts):
                    continue
                found.append(md)
        else:
            print(f"LỖI: không tìm thấy {target}", file=sys.stderr)
    return found


def check(skill_md: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = skill_md.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    if not fm:
        return ["không có YAML frontmatter (--- ... ---)"], warnings

    name = fm.get("name", "").strip()
    if not name:
        errors.append("thiếu `name`")
    else:
        if len(name) > MAX_NAME:
            errors.append(f"`name` dài {len(name)} > {MAX_NAME}")
        if not NAME_RE.match(name):
            errors.append(f"`name` = {name!r} phải là chữ thường/số/gạch nối")
        if name != skill_md.parent.name:
            warnings.append(f"`name` ({name}) khác tên thư mục ({skill_md.parent.name})")

    desc = " ".join(fm.get("description", "").split())
    if not desc:
        errors.append("thiếu `description`")
    elif len(desc) > MAX_DESCRIPTION:
        errors.append(f"`description` dài {len(desc)} > {MAX_DESCRIPTION}")

    if len(body.strip()) < MIN_BODY:
        errors.append(f"thân skill quá ngắn ({len(body.strip())} < {MIN_BODY} ký tự)")

    for link in LINK_RE.findall(body):
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        rel = link.split("#", 1)[0]
        if not rel:
            continue
        if not (skill_md.parent / rel).exists():
            warnings.append(f"link nội bộ không tồn tại: {rel}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ZEUS skills")
    parser.add_argument("targets", nargs="*", help="thư mục/file (mặc định: skills)")
    parser.add_argument("--strict", action="store_true", help="warning cũng là lỗi")
    args = parser.parse_args()

    files = find_skill_files(args.targets)
    if not files:
        print("LỖI: không có SKILL.md nào để kiểm tra", file=sys.stderr)
        return 1

    seen: dict[str, Path] = {}
    total_errors = 0
    total_warnings = 0

    for skill_md in files:
        rel = skill_md.relative_to(Path.cwd()) if skill_md.is_relative_to(Path.cwd()) else skill_md
        errors, warnings = check(skill_md)
        for err in errors:
            print(f"✗ {rel}: {err}")
        for warn in warnings:
            print(f"⚠ {rel}: {warn}")
        if errors or warnings:
            print()
        total_errors += len(errors)
        total_warnings += len(warnings)

        name = parse_frontmatter(skill_md.read_text(encoding="utf-8"))[0].get("name", "")
        if name:
            if name in seen:
                print(f"✗ {rel}: `name` trùng với {seen[name]}")
                total_errors += 1
            else:
                seen[name] = rel

    if args.strict:
        total_errors += total_warnings
        total_warnings = 0

    print(f"Đã kiểm {len(files)} skill: {total_errors} lỗi, {total_warnings} cảnh báo.")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
