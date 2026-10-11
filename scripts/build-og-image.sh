#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
# build-og-image.sh — Tạo ảnh chia sẻ (Open Graph) 1200×630 cho landing page
# Dùng ImageMagick + font DejaVu (có sẵn trên Linux/CI). Không cần Chromium.
#
#   Chạy:  bash scripts/build-og-image.sh
#   Ra:    site/assets/img/og-image.png
#
# Sửa nội dung chữ: xem các biến TITLE_1 / TITLE_2 / SUB / FOOT bên dưới.
# ══════════════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/site/assets/img/og-image.png"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ── Font (đổi đường dẫn nếu máy bạn khác; macOS: /System/Library/Fonts/Supplemental/Arial Bold.ttf)
FONT_DIR="${FONT_DIR:-/usr/share/fonts/truetype/dejavu}"
F_BOLD="$FONT_DIR/DejaVuSans-Bold.ttf"
F_REG="$FONT_DIR/DejaVuSans.ttf"
[ -f "$F_BOLD" ] || { echo "Không tìm thấy font: $F_BOLD" >&2; exit 1; }

# ── Nội dung [SỬA Ở ĐÂY]
NAME="NGUYỄN QUANG QUÝ"
ROLE="AI CREATOR · DIGITAL MARKETING CMO"
TITLE_1="DÙNG AI ĐÚNG CÁCH,"
TITLE_2="TIẾT KIỆM CẢ NGÀY LÀM VIỆC"
SUB="AI Chatbot CSKH 24/7  ·  Automation Zalo + Facebook + CRM"
FOOT="0763 123 992  ·  quangquy.ai  ·  TP. Hồ Chí Minh"

W=1200; H=630

# ── 1. Nền + hai vệt sáng (vàng gold & hồng hoa đào)
convert -size ${W}x${H} xc:'#0a0a12' "$TMP/base.png"
convert -size ${W}x${H} xc:black -fill 'rgba(230,193,118,0.55)' \
  -draw 'circle 1020,40 1020,420' -blur 0x90 "$TMP/glow_gold.png"
convert -size ${W}x${H} xc:black -fill 'rgba(255,183,197,0.42)' \
  -draw 'circle 90,620 90,360' -blur 0x90 "$TMP/glow_pink.png"

convert "$TMP/base.png" "$TMP/glow_gold.png" -compose screen -composite \
        "$TMP/glow_pink.png" -compose screen -composite \
        -fill 'rgba(255,255,255,0.05)' \
        -draw "rectangle 0,0 ${W},1" \
        "$TMP/stage.png"

# ── 2. Vài cánh hoa đào rơi
convert "$TMP/stage.png" \
  -fill 'rgba(255,183,197,0.55)' -draw 'ellipse 1080,150 9,6 20,20' \
  -fill 'rgba(255,214,224,0.42)' -draw 'ellipse 1130,300 7,5 40,40' \
  -fill 'rgba(255,183,197,0.35)' -draw 'ellipse 990,470 8,5 -15,-15' \
  -fill 'rgba(230,193,118,0.4)'  -draw 'ellipse 1160,90 6,4 10,10' \
  "$TMP/stage2.png"

# ── 3. Khối chữ
convert "$TMP/stage2.png" \
  -font "$F_BOLD" -pointsize 26 -fill '#f6e2ad' -annotate +72+96  "$NAME" \
  -font "$F_REG"  -pointsize 20 -fill '#8b8ba3' -annotate +72+130 "$ROLE" \
  -font "$F_BOLD" -pointsize 66 -fill '#ffffff' -annotate +72+280 "$TITLE_1" \
  -font "$F_BOLD" -pointsize 66 \
    -fill '#e6c176' -annotate +72+360 "$TITLE_2" \
  -font "$F_REG"  -pointsize 25 -fill '#b9b9cc' -annotate +72+430 "$SUB" \
  -font "$F_BOLD" -pointsize 22 -fill '#e6c176' -annotate +72+560 "$FOOT" \
  -fill '#e6c176' -draw 'rectangle 72,510 260,513' \
  "$OUT"

echo "✔ Đã tạo $OUT"
identify "$OUT" 2>/dev/null || true
