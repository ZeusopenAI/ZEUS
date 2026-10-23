#!/usr/bin/env bash
set -uo pipefail

# ============================================================================
# Cấp "toàn quyền làm việc" cho Hermes trên VPS/Codespace — một lệnh duy nhất.
#
# Cài & kiểm tra:
#   1. ffmpeg      → cắt/ghép/nén video, xuất thumbnail, trích frame
#   2. Pillow      → resize/crop/nén ảnh, đóng watermark của chính bạn
#   3. git + gh    → commit, push, mở PR (cần token, xem mục 4)
#   4. GitHub token → gọi scripts/hermes-github-setup.sh (hỏi token, ẩn ký tự)
#   5. Đọc bài viết → kiểm tra mạng + scripts/read-article.py
#   6. Đồng bộ skill/ngữ cảnh sang Hermes
#
# CÁCH DÙNG
#   bash scripts/hermes-power-setup.sh                 # cài + kiểm tra + sync
#   bash scripts/hermes-power-setup.sh --check         # CHỈ kiểm tra, không cài gì
#   bash scripts/hermes-power-setup.sh --with-token    # kèm bước nhập GitHub token
#   bash scripts/hermes-power-setup.sh --skip-sync     # không đụng tới Hermes
#   bash scripts/hermes-power-setup.sh --venv /opt/venv  # cài vào venv chỉ định
#
# Mã thoát: 0 = mọi thứ sẵn sàng, 1 = có mục chưa đạt, 2 = tham số sai.
# Không bao giờ in giá trị token.
# ============================================================================

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
VENV="${VENV:-}"

CHECK_ONLY=0
WITH_TOKEN=0
DO_SYNC=1

while [ $# -gt 0 ]; do
  case "$1" in
    --check)      CHECK_ONLY=1 ;;
    --with-token) WITH_TOKEN=1 ;;
    --skip-sync)  DO_SYNC=0 ;;
    --venv)       shift; VENV="${1:-}" ;;
    -h|--help)    sed -n '2,28p' "$0"; exit 0 ;;
    *)            echo "Tham số không hỗ trợ: $1" >&2; exit 2 ;;
  esac
  shift
done

OK=0; FAIL=0
declare -a ROWS=()

say()  { printf '\n== %s ==\n' "$*"; }
info() { printf '   %s\n' "$*"; }
row()  { ROWS+=("$1|$2"); }
pass() { OK=$((OK+1)); row "✓" "$1"; info "✓ $1"; }
fail() { FAIL=$((FAIL+1)); row "✗" "$1"; info "✗ $1"; }
warn2(){ row "⚠" "$1"; info "⚠ $1"; }

PY="python3"
if [ -n "$VENV" ] && [ -x "$VENV/bin/python" ]; then PY="$VENV/bin/python"; fi

# ── 1. ffmpeg ───────────────────────────────────────────────────────────────
say "[1/6] ffmpeg (video)"
FF="$(command -v ffmpeg 2>/dev/null || true)"
if [ -z "$FF" ]; then FF="$("$PY" -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null || true)"; fi

if [ -n "$FF" ] && [ -x "$FF" ]; then
  pass "ffmpeg: $("$FF" -version 2>/dev/null | head -1 | cut -c1-60)"
elif [ "$CHECK_ONLY" = "1" ]; then
  fail "chưa có ffmpeg (cài: sudo apt install -y ffmpeg)"
else
  info "chưa có ffmpeg — đang cài…"
  installed=0
  if command -v apt-get >/dev/null 2>&1; then
    if [ "$(id -u)" -eq 0 ]; then
      DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null 2>&1 \
        && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg >/dev/null 2>&1 \
        && installed=1
    elif command -v sudo >/dev/null 2>&1; then
      sudo -n env DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null 2>&1 \
        && sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg >/dev/null 2>&1 \
        && installed=1
    fi
  fi
  if [ "$installed" = "1" ]; then
    FF="$(command -v ffmpeg)"
    pass "ffmpeg đã cài bằng apt"
  else
    info "apt không dùng được (không có quyền) → cài bản pip (không cần root)…"
    if "$PY" -m pip install --quiet --user imageio-ffmpeg >/dev/null 2>&1; then
      FF="$("$PY" -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null || true)"
      [ -n "$FF" ] && pass "ffmpeg (bản pip): $(basename "$FF")" \
                   || fail "cài imageio-ffmpeg nhưng không lấy được đường dẫn"
    else
      fail "không cài được ffmpeg — thử: sudo apt install -y ffmpeg"
    fi
  fi
fi

# ── 2. Pillow ───────────────────────────────────────────────────────────────
say "[2/6] Pillow (ảnh)"
if "$PY" -c 'import PIL' >/dev/null 2>&1; then
  pass "Pillow $("$PY" -c 'import PIL;print(PIL.__version__)' 2>/dev/null)"
elif [ "$CHECK_ONLY" = "1" ]; then
  fail "chưa có Pillow (cài: $PY -m pip install --user pillow)"
else
  info "đang cài Pillow…"
  if "$PY" -m pip install --quiet --user pillow >/dev/null 2>&1 \
     || "$PY" -m pip install --quiet pillow >/dev/null 2>&1; then
    pass "Pillow $("$PY" -c 'import PIL;print(PIL.__version__)' 2>/dev/null)"
  else
    fail "không cài được Pillow"
  fi
fi

# ── 3. git + gh ─────────────────────────────────────────────────────────────
say "[3/6] git & gh"
if command -v git >/dev/null 2>&1; then
  pass "git $(git --version | awk '{print $3}')"
else
  fail "chưa có git — cài: sudo apt install -y git"
fi

if command -v gh >/dev/null 2>&1; then
  if GITHUB_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}" gh auth status >/dev/null 2>&1; then
    pass "gh đã đăng nhập"
  else
    warn2 "gh có nhưng chưa đăng nhập (chạy --with-token)"
  fi
else
  warn2 "chưa có gh CLI (không bắt buộc — dùng git + ~/.git-credentials)"
fi

# Thử git tới repo (chỉ đọc)
if [ -d "$REPO_DIR/.git" ]; then
  if GIT_TERMINAL_PROMPT=0 timeout 25 git -C "$REPO_DIR" ls-remote --heads origin >/dev/null 2>&1; then
    pass "git ls-remote origin OK"
  else
    warn2 "git ls-remote thất bại (chưa có credential — chạy --with-token)"
  fi
fi

# ── 4. GitHub token ─────────────────────────────────────────────────────────
say "[4/6] GitHub token"
HAS_TOKEN=0
if grep -qE '^(GITHUB_TOKEN|GH_TOKEN)=.+' "$HERMES_HOME/.env" 2>/dev/null; then HAS_TOKEN=1; fi

if [ "$WITH_TOKEN" = "1" ] && [ "$CHECK_ONLY" != "1" ]; then
  if [ -x "$REPO_DIR/scripts/hermes-github-setup.sh" ]; then
    info "nhập token khi được hỏi (ký tự bị ẩn)…"
    if HERMES_HOME="$HERMES_HOME" bash "$REPO_DIR/scripts/hermes-github-setup.sh" \
         --repo ZeusOpenAI/ZEUS --test-write; then
      pass "GitHub token: có quyền ghi"
      HAS_TOKEN=1
    else
      fail "GitHub token: chưa đủ quyền (xem docs/HERMES_GITHUB_TOKEN.md)"
      HAS_TOKEN=1
    fi
  else
    fail "thiếu scripts/hermes-github-setup.sh"
  fi
elif [ "$HAS_TOKEN" = "1" ]; then
  if [ -x "$REPO_DIR/scripts/hermes-github-check.sh" ]; then
    if HERMES_HOME="$HERMES_HOME" bash "$REPO_DIR/scripts/hermes-github-check.sh" --quiet >/dev/null 2>&1; then
      pass "GitHub token hợp lệ và đủ quyền"
    else
      fail "GitHub token có vấn đề — chạy: bash scripts/hermes-github-check.sh"
    fi
  else
    pass "đã có token trong $HERMES_HOME/.env"
  fi
else
  warn2 "chưa có GitHub token → Hermes không tự push/PR được (chạy lại với --with-token)"
fi

# ── 5. Đọc bài viết ─────────────────────────────────────────────────────────
say "[5/6] Đọc bài viết (mạng + parser)"
if [ -f "$REPO_DIR/scripts/read-article.py" ]; then
  # test parser trên file tạo tại chỗ, không phụ thuộc mạng
  TMPH="$(mktemp --suffix=.html 2>/dev/null || mktemp)"
  cat > "$TMPH" <<'HTML'
<html><head><title>Kiểm tra</title></head><body><article>
<h1>Kiểm tra</h1><p>Nội dung thử nghiệm để xác nhận parser hoạt động.</p>
</article></body></html>
HTML
  if "$PY" "$REPO_DIR/scripts/read-article.py" "$TMPH" 2>/dev/null | grep -q "Nội dung thử nghiệm"; then
    pass "parser HTML hoạt động"
  else
    fail "parser không đọc được HTML"
  fi
  rm -f "$TMPH"

  # test mạng ra ngoài (không chặn kết quả setup nếu mạng bị hạn chế)
  if timeout 15 "$PY" -c "import urllib.request;urllib.request.urlopen('https://api.github.com',timeout=10)" >/dev/null 2>&1; then
    pass "ra được Internet (đọc bài trực tiếp từ URL)"
  else
    warn2 "không ra được Internet — chỉ đọc được file đã tải về"
  fi
else
  fail "thiếu scripts/read-article.py"
fi

# ── 6. Media script + đồng bộ ───────────────────────────────────────────────
say "[6/6] Script media & đồng bộ Hermes"
if [ -f "$REPO_DIR/scripts/media-batch.py" ] && "$PY" -c 'import PIL' >/dev/null 2>&1; then
  MK="$(mktemp -d)"
  mkdir -p "$MK/in" "$MK/out"
  if "$PY" - "$MK/in" <<'PYMK' >/dev/null 2>&1
import sys
from PIL import Image
Image.new("RGB", (1000, 800), (40, 80, 120)).save(sys.argv[1] + "/t.jpg", quality=90)
PYMK
  then
    if "$PY" "$REPO_DIR/scripts/media-batch.py" image -i "$MK/in" -o "$MK/out" --max-width 500 >/dev/null 2>&1 \
       && [ -f "$MK/out/t.jpg" ]; then
      pass "media-batch.py chạy được (ảnh)"
    else
      fail "media-batch.py lỗi khi xử lý ảnh"
    fi
  else
    fail "không tạo được ảnh thử (Pillow lỗi?)"
  fi
  rm -rf "$MK"

  if [ -n "$FF" ] && [ -x "$FF" ]; then
    pass "media-batch.py có ffmpeg để xử lý video"
  else
    warn2 "chưa có ffmpeg → không xử lý được video"
  fi
elif [ ! -f "$REPO_DIR/scripts/media-batch.py" ]; then
  fail "thiếu scripts/media-batch.py"
else
  warn2 "bỏ qua kiểm media (chưa có Pillow)"
fi

if [ "$DO_SYNC" = "1" ] && [ "$CHECK_ONLY" != "1" ]; then
  if [ -x "$REPO_DIR/scripts/hermes-sync.sh" ]; then
    set +e
    HERMES_HOME="$HERMES_HOME" bash "$REPO_DIR/scripts/hermes-sync.sh" --with-memory >/dev/null 2>&1
    rc=$?
    set -e
    case "$rc" in
      0)  pass "skill/ngữ cảnh đã ở bản mới nhất" ;;
      10) pass "đã đồng bộ skill/ngữ cảnh sang Hermes" ;;
      *)  warn2 "đồng bộ Hermes lỗi (mã $rc) — chạy tay: bash scripts/hermes-sync.sh" ;;
    esac
  fi
fi

# ── Bảng tổng kết ───────────────────────────────────────────────────────────
printf '\n╔══════════════════════════════════════════════════╗\n'
printf '║  TỔNG KẾT NĂNG LỰC CỦA HERMES                    ║\n'
printf '╚══════════════════════════════════════════════════╝\n'
for r in "${ROWS[@]}"; do printf '  %s %s\n' "${r%%|*}" "${r#*|}"; done
printf '\n  %d đạt · %d chưa đạt\n' "$OK" "$FAIL"

cat <<EOF

Cách dùng ngay (dán vào chat với Hermes):
  • "Cắt clip này thành 1080x1920, xuất thumbnail"      → media-batch.py video
  • "Nén toàn bộ ảnh trong thư mục raw/, đóng logo"     → media-batch.py image
  • "Đọc bài này và tóm tắt: https://…"                 → read-article.py
  • "Sửa file X rồi mở PR"                              → skill hermes-github-access

Kiểm tra lại bất cứ lúc nào:
  bash scripts/hermes-power-setup.sh --check

Chi tiết: docs/HERMES_FULL_CAPABILITY.md
EOF

if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
