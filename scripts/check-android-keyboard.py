#!/usr/bin/env python3
"""Kiểm tra tĩnh cho `android-keyboard/` — chạy trước khi Gradle build.

Không cần Android SDK: bắt các lỗi từng làm `Build Zeus AI Keyboard APK` đỏ
(run 40010065069) và các tham chiếu resource gãy.

    python3 scripts/check-android-keyboard.py
    python3 scripts/check-android-keyboard.py --root android-keyboard

Kiểm tra:
  1. API không tồn tại trên KeyboardView/Keyboard (lỗi biên dịch).
  2. Mọi `R.<type>.<name>` trong Java phải có resource tương ứng.
  3. Mọi file XML trong res/ phải well-formed.

Mã thoát: 0 = sạch, 1 = có lỗi.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# (regex, giải thích, cách sửa)
BANNED_PATTERNS = [
    (
        re.compile(r"new\s+KeyboardView\s*\(\s*[A-Za-z_][\w.]*\s*\)"),
        "KeyboardView không có constructor 1 tham số",
        "inflate từ XML: (KeyboardView) getLayoutInflater().inflate(R.layout.keyboard_view, null)",
    ),
    (
        re.compile(r"\.setKeyBackgroundColor\s*\("),
        "KeyboardView không có setKeyBackgroundColor()",
        "đặt android:keyBackground (drawable) trong style XML",
    ),
    (
        re.compile(r"\.setKeyTextColor\s*\("),
        "KeyboardView không có setKeyTextColor()",
        "đặt android:keyTextColor trong style XML",
    ),
    (
        re.compile(r"\.isSticky\s*\(\s*\)"),
        "Keyboard không có isSticky() (sticky là thuộc tính của Keyboard.Key)",
        "bỏ điều kiện, hoặc duyệt Keyboard.Key và đọc isSticky của key shift",
    ),
]

R_REF_RE = re.compile(r"\bR\.(layout|xml|drawable|mipmap|string|color|style|id|array|dimen)\." r"([A-Za-z0-9_]+)")


def java_sources(root: Path) -> list[Path]:
    return sorted(root.glob("app/src/main/java/**/*.java"))


def check_banned_apis(root: Path) -> list[str]:
    errors: list[str] = []
    for path in java_sources(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for regex, problem, fix in BANNED_PATTERNS:
            for match in regex.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{path}:{line}: {problem} -> {fix}")
    return errors


def collect_resources(root: Path) -> tuple[dict[str, set[str]], list[str]]:
    """Trả về (map type -> tên resource, danh sách lỗi XML)."""
    res = root / "app/src/main/res"
    names: dict[str, set[str]] = {key: set() for key in
                                 ("layout", "xml", "drawable", "mipmap", "string", "color", "style", "id", "array", "dimen")}
    errors: list[str] = []

    for path in sorted(res.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".xml":
            try:
                tree = ET.parse(path)
            except ET.ParseError as exc:
                errors.append(f"{path}: XML không hợp lệ — {exc}")
                continue
            top = tree.getroot()
            for child in top:
                tag = child.tag.rsplit("}", 1)[-1]
                name = child.get("name")
                if not name:
                    continue
                if tag == "item" and child.get("type") == "id":
                    names["id"].add(name)
                elif tag in ("string", "color", "style", "dimen", "array", "string-array", "integer-array", "bool", "integer"):
                    key = {"string-array": "array", "integer-array": "array"}.get(tag, tag)
                    names.setdefault(key, set()).add(name)
            # @+id/... khai báo trong layout
            for match in re.finditer(r"@\+id/([A-Za-z0-9_]+)", path.read_text(encoding="utf-8", errors="replace")):
                names["id"].add(match.group(1))

        if path.parent.name.startswith("layout"):
            names["layout"].add(path.stem)
        elif path.parent.name.startswith("xml"):
            names["xml"].add(path.stem)
        elif path.parent.name.startswith("drawable"):
            names["drawable"].add(path.stem)
        elif path.parent.name.startswith("mipmap"):
            names["mipmap"].add(path.stem)

    return names, errors


def check_resource_refs(root: Path, names: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    for path in java_sources(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in R_REF_RE.finditer(text):
            kind, name = match.group(1), match.group(2)
            if kind not in names:
                continue
            if name not in names[kind]:
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{path}:{line}: R.{kind}.{name} không tồn tại trong app/src/main/res"
                )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="android-keyboard", help="Thư mục project Android")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not (root / "app").is_dir():
        print(f"FAIL: không thấy project Android tại {root}")
        return 1

    names, xml_errors = collect_resources(root)
    errors = check_banned_apis(root) + xml_errors + check_resource_refs(root, names)

    if errors:
        print(f"FAIL: {len(errors)} lỗi trong {root.name}/")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(
        f"PASS: {root.name}/ — {len(java_sources(root))} file Java, "
        f"{sum(len(v) for v in names.values())} resource, 0 lỗi API/XML/tham chiếu"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
