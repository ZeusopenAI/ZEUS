#!/usr/bin/env python3
"""Xử lý ảnh/video hàng loạt cho Hermes — chạy offline, không tốn credit.

Chỉ dùng Pillow (ảnh) và ffmpeg (video). Không gọi API nào.

    # Xem thông tin
    python3 scripts/media-batch.py info anh1.jpg video1.mp4

    # Ảnh: resize + nén, xuất sang thư mục khác
    python3 scripts/media-batch.py image --input raw/ --output out/ \
        --max-width 1920 --quality 82

    # Ảnh: crop vuông + đóng watermark chữ của chính bạn
    python3 scripts/media-batch.py image --input raw/ --output out/ \
        --crop square --watermark-text "quangquy.ai" --position bottom-right

    # Video: nén cho TikTok/Reels (1080x1920, 30fps, h264)
    python3 scripts/media-batch.py video --input clips/ --output out/ --preset vertical

    # Video: cắt 3 giây đầu + xuất thumbnail
    python3 scripts/media-batch.py video --input a.mp4 --output out/ --trim 0:3 --thumbnail

    # Xem trước, không ghi gì
    python3 scripts/media-batch.py video --input clips/ --output out/ --preset vertical --dry-run

Mã thoát: 0 = OK, 1 = có file lỗi, 2 = tham số sai, 3 = thiếu công cụ.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv"}

PRESETS = {
    # name: (width, height, fps, crf, audio_bitrate)
    "vertical": (1080, 1920, 30, 23, "128k"),   # TikTok / Reels / Shorts
    "square": (1080, 1080, 30, 23, "128k"),     # feed vuông
    "landscape": (1920, 1080, 30, 23, "160k"),  # YouTube
    "preview": (720, 1280, 30, 30, "96k"),      # bản nhẹ để gửi duyệt
}


# ── Tiện ích ────────────────────────────────────────────────────────────────

def die(msg: str, code: int = 2) -> None:
    print(f"LỖI: {msg}", file=sys.stderr)
    sys.exit(code)


def collect(inputs: list[str], exts: set[str]) -> list[Path]:
    files: list[Path] = []
    for raw in inputs:
        p = Path(raw).expanduser()
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in exts and not f.name.startswith("."):
                    files.append(f)
        elif p.is_file():
            if p.suffix.lower() in exts:
                files.append(p)
            else:
                print(f"BỎ QUA: {p} (không phải định dạng hỗ trợ)", file=sys.stderr)
        else:
            print(f"BỎ QUA: {p} (không tồn tại)", file=sys.stderr)
    # loại trùng, giữ thứ tự
    seen: set[Path] = set()
    out = []
    for f in files:
        r = f.resolve()
        if r not in seen:
            seen.add(r)
            out.append(f)
    return out


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}GB"


def ffmpeg_bin() -> str | None:
    """Tìm ffmpeg: PATH trước, rồi imageio-ffmpeg (bản pip, không cần apt)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def run_ffmpeg(args: list[str], dry: bool) -> tuple[bool, str]:
    if dry:
        print("   [dry-run] ffmpeg " + " ".join(args))
        return True, ""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return False, "quá thời gian (30 phút)"
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()[-3:]
        return False, " | ".join(tail) or f"ffmpeg exit {r.returncode}"
    return True, ""


def safe_out(src: Path, outdir: Path, suffix: str = "", ext: str | None = None,
             create: bool = True) -> Path:
    if create:
        outdir.mkdir(parents=True, exist_ok=True)
    stem, out_ext = src.stem, (ext or src.suffix)
    if suffix:
        stem = f"{stem}-{suffix}"
    target = outdir / f"{stem}{out_ext}"
    # không ghi đè file lạ: thêm hậu tố nếu trùng
    i = 1
    while target.exists():
        target = outdir / f"{stem}-{i}{out_ext}"
        i += 1
    return target


# ── Ảnh ─────────────────────────────────────────────────────────────────────

def process_image(
    src: Path,
    outdir: Path,
    *,
    max_width: int | None,
    max_height: int | None,
    crop: str | None,
    quality: int,
    fmt: str | None,
    watermark_text: str | None,
    watermark_image: str | None,
    position: str,
    opacity: int,
    dry: bool,
) -> dict:
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    info: dict = {"file": str(src), "ok": False}
    before = src.stat().st_size
    info["before"] = before

    ext = f".{fmt}" if fmt else src.suffix.lower()
    target = safe_out(src, outdir, ext=ext, create=not dry)
    info["out"] = str(target)

    if dry:
        info.update(ok=True, skipped_dry=True)
        return info

    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)          # ảnh điện thoại không bị quay
            orig = im.size

            if im.mode not in ("RGB", "RGBA", "L"):
                im = im.convert("RGB")

            # Cắt
            if crop == "square":
                side = min(im.size)
                im = ImageOps.fit(im, (side, side), method=Image.LANCZOS)
            elif crop == "16:9":
                w = im.size[0]
                im = ImageOps.fit(im, (w, int(w * 9 / 16)), method=Image.LANCZOS)
            elif crop == "9:16":
                h = im.size[1]
                im = ImageOps.fit(im, (int(h * 9 / 16), h), method=Image.LANCZOS)

            # Resize (giữ tỉ lệ, không phóng to ảnh nhỏ)
            if max_width or max_height:
                w, h = im.size
                ratio = 1.0
                if max_width and w > max_width:
                    ratio = min(ratio, max_width / w)
                if max_height and h > max_height:
                    ratio = min(ratio, max_height / h)
                if ratio < 1.0:
                    im = im.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)

            # Watermark CỦA CHÍNH NGƯỜI DÙNG (không phải xoá watermark nền tảng khác)
            if watermark_text or watermark_image:
                im = im.convert("RGBA")
                overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                pad = max(10, int(min(im.size) * 0.02))

                if watermark_image:
                    wm_path = Path(watermark_image).expanduser()
                    with Image.open(wm_path) as wm:
                        wm = wm.convert("RGBA")
                        wm_w = int(im.size[0] * 0.18)
                        wm_h = int(wm.size[1] * (wm_w / wm.size[0]))
                        wm = wm.resize((wm_w, wm_h), Image.LANCZOS)
                        if opacity < 255:
                            a = wm.getchannel("A").point(lambda v: int(v * opacity / 255))
                            wm.putalpha(a)
                        x, y = anchor_xy(im.size, (wm_w, wm_h), position, pad)
                        overlay.alpha_composite(wm, (x, y))
                else:
                    size = max(14, int(min(im.size) * 0.045))
                    try:
                        font = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
                    except Exception:
                        font = ImageFont.load_default()
                    bbox = draw.textbbox((0, 0), watermark_text, font=font)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    x, y = anchor_xy(im.size, (tw, th), position, pad)
                    # bóng mờ để chữ đọc được trên mọi nền
                    draw.text((x + 1, y + 1), watermark_text, font=font, fill=(0, 0, 0, opacity))
                    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, opacity))

                im = Image.alpha_composite(im, overlay)

            if ext in (".jpg", ".jpeg"):
                im = im.convert("RGB")
                im.save(target, quality=quality, optimize=True, progressive=True)
            elif ext == ".png":
                im.save(target, optimize=True)
            elif ext == ".webp":
                im.save(target, quality=quality, method=4)
            else:
                im.save(target)

        after = target.stat().st_size
        info.update(
            ok=True, after=after,
            saved_bytes=before - after,
            pct=round((1 - after / before) * 100, 1) if before else 0.0,
            from_size=f"{orig[0]}x{orig[1]}",
        )
    except Exception as e:  # noqa: BLE001
        info["error"] = f"{type(e).__name__}: {e}"
    return info


def anchor_xy(canvas: tuple[int, int], box: tuple[int, int], position: str, pad: int) -> tuple[int, int]:
    cw, ch = canvas
    bw, bh = box
    if position == "top-left":
        return pad, pad
    if position == "top-right":
        return cw - bw - pad, pad
    if position == "bottom-left":
        return pad, ch - bh - pad
    if position == "center":
        return (cw - bw) // 2, (ch - bh) // 2
    return cw - bw - pad, ch - bh - pad  # bottom-right


# ── Video ───────────────────────────────────────────────────────────────────

def process_video(
    src: Path,
    outdir: Path,
    *,
    preset: str | None,
    width: int | None,
    height: int | None,
    crf: int | None,
    trim: str | None,
    thumbnail: bool,
    frames: int,
    dry: bool,
) -> dict:
    info: dict = {"file": str(src), "ok": False}
    info["before"] = src.stat().st_size
    ff = ffmpeg_bin()
    if not ff:
        return {**info, "error": "không tìm thấy ffmpeg (cài: apt install ffmpeg, hoặc pip install imageio-ffmpeg)"}

    target = safe_out(src, outdir, suffix="out", ext=".mp4", create=not dry)
    info["out"] = str(target)

    w = h = fps = None
    q = crf if crf is not None else 23
    abr = "128k"
    if preset:
        if preset not in PRESETS:
            return {**info, "error": f"preset không hợp lệ: {preset}"}
        w, h, fps, q, abr = PRESETS[preset]
    if width:
        w = width
    if height:
        h = height

    # scale giữ tỉ lệ + pad cho vừa khung (video dọc/ngang khác nhau không bị méo)
    vf = []
    if w or h:
        w_expr = str(w) if w else f"trunc(oh*a/2)*2"
        h_expr = str(h) if h else f"trunc(ow/a/2)*2"
        vf.append(f"scale={w_expr}:{h_expr}:force_original_aspect_ratio=decrease")
        vf.append(f"pad={w or -2}:{h or -2}:(ow-iw)/2:(oh-ih)/2:color=black")
    if fps:
        vf.append(f"fps={fps}")

    args = [ff, "-hide_banner", "-loglevel", "error", "-y"]
    if trim:
        args += ["-ss", trim.split(":")[0] if ":" in trim else trim, "-to", trim.split(":")[1] if ":" in trim else ""]
    args += ["-i", str(src)]
    if vf:
        args += ["-vf", ",".join(vf)]
    args += [
        "-c:v", "libx264", "-preset", "medium", "-crf", str(q), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", abr, "-movflags", "+faststart", str(target),
    ]

    if dry:
        print("   [dry-run] ffmpeg " + " ".join(args))
        return {**info, "ok": True, "skipped_dry": True}

    ok, err = run_ffmpeg(args, dry)
    if not ok:
        return {**info, "error": err}

    after = target.stat().st_size
    info.update(
        ok=True, after=after,
        saved_bytes=info["before"] - after,
        pct=round((1 - after / info["before"]) * 100, 1) if info["before"] else 0.0,
    )

    # Thumbnail (1 ảnh) hoặc frames (n ảnh đều nhau)
    if thumbnail:
        thumb = safe_out(src, outdir, suffix="thumb", ext=".jpg")
        tok, terr = run_ffmpeg([ff, "-hide_banner", "-loglevel", "error", "-y",
                                "-ss", "1", "-i", str(src), "-frames:v", "1",
                                "-vf", "scale=1280:-2", "-q:v", "3", str(thumb)], dry)
        info["thumbnail"] = str(thumb) if tok else f"lỗi: {terr}"

    if frames and frames > 0:
        fdir = outdir / f"{src.stem}-frames"
        fdir.mkdir(parents=True, exist_ok=True)
        dok, derr = run_ffmpeg([ff, "-hide_banner", "-loglevel", "error", "-y",
                                "-i", str(src), "-vf", f"fps=1/{max(1, frames)}",
                                "-frames:v", str(frames), str(fdir / "%02d.jpg")], dry)
        info["frames"] = str(fdir) if dok else f"lỗi: {derr}"

    return info


def probe(path: Path) -> dict:
    out: dict = {"file": str(path), "size": path.stat().st_size}
    if path.suffix.lower() in IMAGE_EXT:
        try:
            from PIL import Image
            with Image.open(path) as im:
                out.update(kind="image", width=im.size[0], height=im.size[1], mode=im.mode,
                           format=im.format)
        except Exception as e:  # noqa: BLE001
            out["error"] = str(e)
    elif path.suffix.lower() in VIDEO_EXT:
        out["kind"] = "video"
        ff = ffmpeg_bin()
        if ff:
            try:
                r = subprocess.run([ff, "-hide_banner", "-i", str(path)],
                                   capture_output=True, text=True, timeout=60)
                for line in (r.stderr or "").splitlines():
                    if "Duration:" in line:
                        out["duration"] = line.split("Duration:")[1].split(",")[0].strip()
                    if "Video:" in line and "Stream" in line:
                        seg = line.split("Video:")[1]
                        out["video"] = seg.split(",")[0].strip()
                        m = re.search(r"\b(\d{2,5})x(\d{2,5})\b", seg)
                        if m:
                            out["resolution"] = f"{m.group(1)}x{m.group(2)}"
            except Exception as e:  # noqa: BLE001
                out["error"] = str(e)
    return out


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Xử lý ảnh/video hàng loạt (offline, không tốn credit)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_info = sub.add_parser("info", help="Xem thông tin file")
    p_info.add_argument("files", nargs="+")

    p_img = sub.add_parser("image", help="Xử lý ảnh hàng loạt")
    p_img.add_argument("--input", "-i", nargs="+", required=True, help="file hoặc thư mục")
    p_img.add_argument("--output", "-o", required=True, help="thư mục kết quả")
    p_img.add_argument("--max-width", type=int)
    p_img.add_argument("--max-height", type=int)
    p_img.add_argument("--crop", choices=["square", "16:9", "9:16"])
    p_img.add_argument("--quality", type=int, default=82, help="1-100 (jpg/webp)")
    p_img.add_argument("--format", choices=["jpg", "jpeg", "png", "webp"])
    p_img.add_argument("--watermark-text", help="chữ của CHÍNH bạn")
    p_img.add_argument("--watermark-image", help="logo PNG của CHÍNH bạn")
    p_img.add_argument("--position", default="bottom-right",
                       choices=["top-left", "top-right", "bottom-left", "bottom-right", "center"])
    p_img.add_argument("--opacity", type=int, default=200, help="0-255")
    p_img.add_argument("--dry-run", action="store_true")

    p_vid = sub.add_parser("video", help="Xử lý video hàng loạt")
    p_vid.add_argument("--input", "-i", nargs="+", required=True)
    p_vid.add_argument("--output", "-o", required=True)
    p_vid.add_argument("--preset", choices=list(PRESETS))
    p_vid.add_argument("--width", type=int)
    p_vid.add_argument("--height", type=int)
    p_vid.add_argument("--crf", type=int, help="thấp = đẹp hơn, 18-28 thường dùng")
    p_vid.add_argument("--trim", help="MM:SS-MM:SS hoặc START:END")
    p_vid.add_argument("--thumbnail", action="store_true")
    p_vid.add_argument("--frames", type=int, default=0, help="số ảnh trích ra")
    p_vid.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()

    if args.cmd == "info":
        for raw in args.files:
            p = Path(raw).expanduser()
            if not p.exists():
                print(json.dumps({"file": raw, "error": "không tồn tại"}, ensure_ascii=False))
                continue
            d = probe(p)
            d["size_human"] = human(d["size"])
            print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "image":
        try:
            import PIL  # noqa: F401
        except ImportError:
            die("thiếu Pillow — cài: python3 -m pip install --user pillow", 3)
        files = collect(args.input, IMAGE_EXT)
        if not files:
            die("không tìm thấy ảnh nào", 2)
        outdir = Path(args.output).expanduser()
        results = []
        t0 = time.time()
        for i, f in enumerate(files, 1):
            print(f"[{i}/{len(files)}] {f}")
            r = process_image(
                f, outdir,
                max_width=args.max_width, max_height=args.max_height,
                crop=args.crop, quality=args.quality, fmt=args.format,
                watermark_text=args.watermark_text, watermark_image=args.watermark_image,
                position=args.position, opacity=args.opacity, dry=args.dry_run,
            )
            results.append(r)
            if r.get("ok") and not r.get("skipped_dry"):
                print(f"   → {Path(r['out']).name}  {human(r['before'])} → {human(r['after'])} "
                      f"(-{r['pct']}%)")
            elif r.get("error"):
                print(f"   ✗ {r['error']}")

    else:  # video
        ff = ffmpeg_bin()
        if not ff:
            die("thiếu ffmpeg — cài: sudo apt install -y ffmpeg\n"
                "      hoặc: python3 -m pip install --user imageio-ffmpeg", 3)
        files = collect(args.input, VIDEO_EXT)
        if not files:
            die("không tìm thấy video nào", 2)
        outdir = Path(args.output).expanduser()
        results = []
        t0 = time.time()
        for i, f in enumerate(files, 1):
            print(f"[{i}/{len(files)}] {f}")
            r = process_video(
                f, outdir,
                preset=args.preset, width=args.width, height=args.height, crf=args.crf,
                trim=args.trim, thumbnail=args.thumbnail, frames=args.frames, dry=args.dry_run,
            )
            results.append(r)
            if r.get("ok") and not r.get("skipped_dry"):
                print(f"   → {Path(r['out']).name}  {human(r['before'])} → {human(r['after'])}")
            elif r.get("error"):
                print(f"   ✗ {r['error']}")

    # Tổng kết
    ok = sum(1 for r in results if r.get("ok"))
    bad = [r for r in results if not r.get("ok")]
    elapsed = round(time.time() - t0, 1)
    saved = sum(r.get("saved_bytes", 0) for r in results if r.get("ok") and r.get("saved_bytes", 0) > 0)
    print(f"\n== Tổng kết ==\n   {ok}/{len(results)} thành công · {elapsed}s · tiết kiệm {human(saved)}")
    summary = {"processed": len(results), "ok": ok, "failed": len(bad),
               "saved_bytes": saved, "elapsed_s": elapsed,
               "errors": [{"file": r["file"], "error": r.get("error")} for r in bad]}
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
