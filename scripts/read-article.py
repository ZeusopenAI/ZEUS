#!/usr/bin/env python3
"""Đọc một bài viết trên web (hoặc file HTML) → văn bản sạch / Markdown.

Không cần thư viện ngoài (chỉ stdlib). Bỏ menu, quảng cáo, script, footer; giữ
tiêu đề + đoạn văn + danh sách + link.

    python3 scripts/read-article.py https://vidu.com/bai-viet
    python3 scripts/read-article.py https://vidu.com/bai-viet --out bai.md
    python3 scripts/read-article.py trang.html --max-chars 8000
    python3 scripts/read-article.py https://... --json        # kèm metadata

Tùy chọn hữu ích:
    --max-chars N   cắt còn N ký tự (mặc định 20000, 0 = không cắt)
    --raw           in HTML gốc thay vì đã làm sạch
    --timeout N     giây (mặc định 20)
    --user-agent    mặc định giả lập trình duyệt

Mã thoát: 0 = OK, 1 = lỗi mạng/parse, 2 = tham số sai.
Lưu ý: chỉ đọc nội dung công khai. Tôn trọng robots.txt và bản quyền — trích dẫn
nguồn khi dùng lại nội dung của người khác.
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Thẻ thường là "rác" — bỏ cả nội dung bên trong
DROP_BLOCKS = (
    "head",  # chứa <title>/<meta> — nếu không bỏ, tiêu đề bị lặp vào nội dung
    "script", "style", "noscript", "iframe", "svg", "form", "nav", "footer",
    "header", "aside", "template", "button", "figure", "figcaption",
)
# Bỏ chính thẻ nhưng giữ nội dung
INLINE_KEEP = {"a", "strong", "b", "em", "i", "code", "span", "mark", "small", "sub", "sup"}


def fetch(url: str, timeout: int) -> tuple[bytes, str, dict]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"chỉ hỗ trợ http/https, nhận: {parsed.scheme!r}")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        if enc == "gzip":
            raw = gzip.decompress(raw)
        elif enc == "deflate":
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        charset = resp.headers.get_content_charset() or "utf-8"
        meta = {
            "url": resp.geturl(),
            "status": resp.status,
            "content_type": resp.headers.get("Content-Type", ""),
        }
        return raw, charset, meta


def decode(raw: bytes, charset: str) -> str:
    # Ưu tiên charset trong header, rồi <meta charset>, rồi utf-8
    head = raw[:4096].decode("ascii", errors="ignore")
    m = re.search(r'<meta[^>]+charset=["\']?([\w-]+)', head, re.I)
    if m and (not charset or charset.lower() in ("iso-8859-1", "text/plain")):
        charset = m.group(1)
    for enc in (charset, "utf-8", "cp1258", "latin-1"):
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def strip_blocks(doc: str) -> str:
    for tag in DROP_BLOCKS:
        doc = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", " ", doc, flags=re.I | re.S)
        doc = re.sub(rf"<{tag}\b[^>]*/?>", " ", doc, flags=re.I)
    doc = re.sub(r"<!--.*?-->", " ", doc, flags=re.S)
    return doc


def extract_meta(doc: str) -> dict:
    def grab(pattern: str) -> str:
        m = re.search(pattern, doc, re.I | re.S)
        return html.unescape(m.group(1)).strip() if m else ""

    title = grab(r"<title[^>]*>(.*?)</title>") or \
            grab(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)') or \
            grab(r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)')
    desc = grab(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)') or \
           grab(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)')
    author = grab(r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)')
    published = grab(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)')
    site = grab(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)')
    return {"title": title, "description": desc, "author": author,
            "published": published, "site": site}


def html_to_text(doc: str, keep_links: bool = True) -> str:
    doc = strip_blocks(doc)

    # Ưu tiên <article> hoặc <main> nếu có — ít rác hơn cả trang
    for tag in ("article", "main"):
        m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", doc, re.I | re.S)
        if m and len(m.group(1)) > 400:
            doc = m.group(1)
            break

    # Link: giữ dạng Markdown nếu bật
    if keep_links:
        def _link(m: re.Match) -> str:
            href = html.unescape(m.group(1))
            text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if not text:
                return ""
            if href.startswith(("/", "#")) or "javascript:" in href:
                return text
            return f"[{text}]({href})"
        doc = re.sub(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', _link,
                     doc, flags=re.I | re.S)

    # Heading
    for level in range(1, 7):
        doc = re.sub(rf"<h{level}\b[^>]*>(.*?)</h{level}>",
                     lambda m, l=level: "\n\n" + "#" * l + " " +
                     re.sub(r"<[^>]+>", "", m.group(1)).strip() + "\n\n",
                     doc, flags=re.I | re.S)

    # Xuống dòng / đoạn
    doc = re.sub(r"<br\s*/?>", "\n", doc, flags=re.I)
    doc = re.sub(r"</(p|div|section|li|tr|blockquote|pre)>", "\n\n", doc, flags=re.I)
    doc = re.sub(r"<li\b[^>]*>", "\n- ", doc, flags=re.I)
    doc = re.sub(r"</t[dh]>", " | ", doc, flags=re.I)

    # Bỏ mọi thẻ còn lại
    doc = re.sub(r"<[^>]+>", "", doc)
    doc = html.unescape(doc)

    # Chuẩn hoá khoảng trắng
    doc = doc.replace("\u00a0", " ")
    doc = re.sub(r"[ \t]+", " ", doc)
    doc = re.sub(r" *\n *", "\n", doc)
    doc = re.sub(r"\n{3,}", "\n\n", doc)
    # Gộp bullet liền nhau (Markdown thường xuất ra "- a\n\n- b")
    doc = re.sub(r"(?m)^(- .+)\n\n(?=- )", r"\1\n", doc)
    return doc.strip()


def looks_like_html(text: str) -> bool:
    head = text[:2000].lower()
    return "<html" in head or "<!doctype" in head or "<body" in head or "<div" in head


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Đọc bài viết trên web → văn bản sạch / Markdown",
        epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("source", help="URL hoặc đường dẫn file HTML/txt")
    ap.add_argument("--out", "-o", help="ghi ra file (mặc định: in ra stdout)")
    ap.add_argument("--max-chars", type=int, default=20000, help="0 = không cắt")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--raw", action="store_true", help="in nội dung gốc, không làm sạch")
    ap.add_argument("--json", action="store_true", help="xuất JSON kèm metadata")
    ap.add_argument("--no-links", action="store_true", help="bỏ link, chỉ giữ chữ")
    args = ap.parse_args()

    meta: dict = {"source": args.source}
    try:
        if re.match(r"^https?://", args.source, re.I):
            raw, charset, fmeta = fetch(args.source, args.timeout)
            text = decode(raw, charset)
            meta.update(fmeta)
        else:
            p = Path(args.source).expanduser()
            if not p.is_file():
                print(f"LỖI: không tìm thấy file {p}", file=sys.stderr)
                return 2
            text = decode(p.read_bytes(), "utf-8")
            meta.update(url=str(p), source_kind="file")
    except urllib.error.HTTPError as e:
        print(f"LỖI: HTTP {e.code} — {e.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"LỖI mạng: {e.reason}\n"
              f"      (nếu máy bị chặn domain, hãy tải file rồi đọc bằng đường dẫn)", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"LỖI: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if args.raw:
        body = text
    elif looks_like_html(text):
        page_meta = extract_meta(text)
        body = html_to_text(text, keep_links=not args.no_links)
        meta.update({k: v for k, v in page_meta.items() if v})
        header = []
        if page_meta["title"]:
            header.append(f"# {page_meta['title']}")
        sub = []
        if page_meta["site"]:
            sub.append(page_meta["site"])
        if page_meta["author"]:
            sub.append(f"tác giả: {page_meta['author']}")
        if page_meta["published"]:
            sub.append(page_meta["published"][:10])
        if sub:
            header.append("_" + " · ".join(sub) + "_")
        header.append(f"Nguồn: {meta.get('url', args.source)}")
        # Bỏ dòng tiêu đề bị lặp lại ngay đầu bài (rất phổ biến: <title> + <h1>)
        if page_meta["title"]:
            body = re.sub(
                r"^\s*(#+\s*)?" + re.escape(page_meta["title"]) + r"\s*\n",
                "", body, count=1,
            )
        body = "\n\n".join(header) + "\n\n" + body
    else:
        body = text.strip()
        if looks_like_html(body) is False and "<" in body[:200]:
            body = html_to_text(body, keep_links=not args.no_links)

    if args.max_chars and len(body) > args.max_chars:
        cut = body[:args.max_chars]
        cut = cut.rsplit("\n", 1)[0]
        body = cut + f"\n\n_(đã cắt ở {args.max_chars} ký tự — tổng {len(text)} ký tự gốc)_"

    meta["chars_out"] = len(body)
    if args.json:
        payload = json.dumps({**meta, "text": body}, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).write_text(payload, encoding="utf-8")
        else:
            print(payload)
    else:
        if args.out:
            Path(args.out).write_text(body, encoding="utf-8")
            print(f"Đã ghi: {args.out} ({len(body)} ký tự)")
        else:
            print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
