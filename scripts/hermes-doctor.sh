#!/usr/bin/env bash
set -uo pipefail

# ============================================================================
# Kiểm tra Hermes có đang "khớp" với repo không (drift check).
#
#   bash scripts/hermes-doctor.sh            # kiểm tra, in báo cáo
#   bash scripts/hermes-doctor.sh --quiet    # chỉ in vấn đề
#
# Kiểm:
#   1. Runtime Hermes có tồn tại và chạy được
#   2. Skill trong $HERMES_HOME/skills có khớp skills/ trong repo
#   3. Snapshot zeus-context có đúng commit hiện tại
#   4. Gateway có active (nếu máy dùng systemd)
#   5. .env có ít nhất một model key (chỉ kiểm tên, không in giá trị)
#   6. Timer auto-sync có bật (nếu đã cài)
#   7. GitHub token hợp lệ + đủ quyền ghi (nếu đã cấu hình)
#
# Mã thoát: 0 = khỏe, 1 = có drift/vấn đề, 2 = thiếu runtime
# ============================================================================

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SKILLS_DEST="$HERMES_HOME/skills"
GATEWAY_UNIT="${GATEWAY_UNIT:-hermes-gateway}"
QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

PROBLEMS=0
WARNINGS=0

ok()   { [ "$QUIET" = "1" ] || printf '  ✓ %s\n' "$*"; }
warn() { WARNINGS=$((WARNINGS + 1)); printf '  ⚠ %s\n' "$*"; }
bad()  { PROBLEMS=$((PROBLEMS + 1)); printf '  ✗ %s\n' "$*"; }
head_() { [ "$QUIET" = "1" ] || printf '\n== %s ==\n' "$*"; }

# ── 1. Runtime ──────────────────────────────────────────────────────────────
head_ "Runtime"
HERMES_BIN=""
for cand in "$HERMES_HOME/venv/bin/hermes" "$(command -v hermes 2>/dev/null || true)"; do
  [ -n "$cand" ] && [ -x "$cand" ] && HERMES_BIN="$cand" && break
done

if [ -z "$HERMES_BIN" ]; then
  bad "không tìm thấy binary hermes (đã thử \$HERMES_HOME/venv/bin/hermes và PATH)"
  printf '\nChưa cài Hermes — chạy: bash .devcontainer/setup-hermes.sh\n' >&2
  exit 2
fi
ok "binary: $HERMES_BIN ($("$HERMES_BIN" --version 2>/dev/null | head -1 || echo 'không đọc được version'))"

if [ -d "$HERMES_HOME" ]; then
  ok "HERMES_HOME: $HERMES_HOME"
else
  bad "thiếu thư mục $HERMES_HOME"
fi

# ── 2. Skill khớp repo ──────────────────────────────────────────────────────
head_ "Skill"
if [ ! -d "$SKILLS_DEST" ]; then
  bad "chưa có $SKILLS_DEST — chạy: bash scripts/hermes-sync.sh"
else
  drift=0
  for src in "$REPO_DIR"/skills/*/; do
    [ -f "$src/SKILL.md" ] || continue
    name="$(basename "$src")"
    if [ ! -d "$SKILLS_DEST/$name" ]; then
      bad "thiếu skill: $name"
      drift=1
    elif ! diff -rq "$src" "$SKILLS_DEST/$name" >/dev/null 2>&1; then
      bad "skill lệch repo: $name"
      drift=1
    fi
  done
  # Skill trong Hermes mà repo không còn (trừ zeus-context do script sinh)
  for dest in "$SKILLS_DEST"/*/; do
    [ -d "$dest" ] || continue
    name="$(basename "$dest")"
    [ "$name" = "zeus-context" ] && continue
    [ -d "$REPO_DIR/skills/$name" ] || warn "skill chỉ có trên máy (không trong repo): $name"
  done
  [ "$drift" = "0" ] && ok "mọi skill trong repo đã đồng bộ"
fi

# ── 3. Snapshot ngữ cảnh ────────────────────────────────────────────────────
head_ "Ngữ cảnh (zeus-context)"
CTX="$SKILLS_DEST/zeus-context/SKILL.md"
REPO_SHA="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
if [ ! -f "$CTX" ]; then
  bad "chưa có zeus-context — chạy: bash scripts/hermes-sync.sh"
else
  CTX_SHA="$(grep -o 'Commit: `[0-9a-f]*`' "$CTX" | head -1 | grep -o '[0-9a-f]\{7,\}' || echo unknown)"
  if [ "$CTX_SHA" = "$REPO_SHA" ]; then
    ok "snapshot khớp commit $REPO_SHA ($(wc -c < "$CTX" | tr -d ' ') bytes)"
  else
    bad "snapshot ở commit $CTX_SHA, repo ở $REPO_SHA — Hermes đang đọc thông tin cũ"
  fi
  head_ "Nội dung snapshot"
  for key in "Trạng thái hiện tại" "Việc đang mở" "Tác vụ phải hỏi trước"; do
    grep -q "$key" "$CTX" && ok "có mục: $key" || warn "thiếu mục: $key"
  done
fi

# ── 4. Gateway ──────────────────────────────────────────────────────────────
head_ "Gateway"
if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
  if systemctl list-unit-files "$GATEWAY_UNIT.service" >/dev/null 2>&1 \
     && systemctl list-unit-files "$GATEWAY_UNIT.service" | grep -q "$GATEWAY_UNIT"; then
    if systemctl is-active --quiet "$GATEWAY_UNIT"; then
      ok "$GATEWAY_UNIT: active"
    else
      bad "$GATEWAY_UNIT không active — xem: journalctl -u $GATEWAY_UNIT -n 50"
    fi
    if systemctl is-enabled --quiet "$GATEWAY_UNIT" 2>/dev/null; then
      ok "$GATEWAY_UNIT: bật khi khởi động"
    else
      warn "$GATEWAY_UNIT chưa enable → không tự chạy lại sau reboot"
    fi
  else
    warn "chưa cài $GATEWAY_UNIT (bình thường nếu chỉ dùng Codespace)"
  fi

  if systemctl list-unit-files hermes-repo-sync.timer >/dev/null 2>&1 \
     && systemctl list-unit-files hermes-repo-sync.timer | grep -q hermes-repo-sync; then
    if systemctl is-active --quiet hermes-repo-sync.timer; then
      ok "auto-sync timer: active"
      [ "$QUIET" = "1" ] || systemctl list-timers hermes-repo-sync.timer --no-pager 2>/dev/null | sed -n '1,2p' | sed 's/^/    /'
    else
      bad "auto-sync timer không chạy → không tự cập nhật: sudo systemctl enable --now hermes-repo-sync.timer"
    fi
  else
    warn "chưa cài auto-sync timer (VPS sẽ không tự cập nhật theo giờ)"
  fi
else
  warn "không có systemd ở môi trường này — bỏ qua kiểm tra service/timer"
fi

# ── 5. Secrets (chỉ kiểm tên biến) ──────────────────────────────────────────
head_ "Cấu hình model"
ENV_FILE="$HERMES_HOME/.env"
if [ -f "$ENV_FILE" ]; then
  perms="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE" 2>/dev/null || echo '?')"
  [ "$perms" = "600" ] && ok ".env quyền 600" || warn ".env quyền $perms (nên là 600: chmod 600 $ENV_FILE)"
  found=0
  for var in OPENROUTER_API_KEY GEMINI_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY NOUS_API_KEY; do
    if grep -qE "^${var}=.+" "$ENV_FILE" 2>/dev/null; then
      ok "có $var"
      found=1
    fi
  done
  [ "$found" = "0" ] && bad "chưa có model key nào trong .env → Hermes không gọi được model"
else
  warn "chưa có $ENV_FILE (chưa cấu hình model key)"
fi

# ── 6. GitHub token (nếu có) ────────────────────────────────────────────────
head_ "GitHub token"
# Chỉ kiểm khi token nằm trong .env của chính Hermes — đó là thứ gateway nạp.
# (env var trong shell hiện tại có thể là token của công cụ khác, không liên quan Hermes.)
if [ -x "$REPO_DIR/scripts/hermes-github-check.sh" ] && \
   grep -qE '^(GITHUB_TOKEN|GH_TOKEN)=.+' "$HERMES_HOME/.env" 2>/dev/null; then
  set +e
  out="$(HERMES_HOME="$HERMES_HOME" bash "$REPO_DIR/scripts/hermes-github-check.sh" --quiet 2>&1)"
  rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then
    ok "token hợp lệ và đủ quyền"
  else
    printf '%s\n' "$out" | sed 's/^/    /'
    bad "token GitHub có vấn đề (chạy: bash scripts/hermes-github-check.sh)"
  fi
else
  warn "chưa cấu hình GitHub token (Hermes không tự push/PR được)"
fi

# ── Kết luận ────────────────────────────────────────────────────────────────
printf '\n'
if [ "$PROBLEMS" -gt 0 ]; then
  printf 'KẾT LUẬN: %d lỗi, %d cảnh báo → cần xử lý.\n' "$PROBLEMS" "$WARNINGS"
  printf 'Gợi ý: bash scripts/hermes-sync.sh --with-memory && hermes gateway restart\n'
  exit 1
fi
if [ "$WARNINGS" -gt 0 ]; then
  printf 'KẾT LUẬN: OK, %d cảnh báo (không chặn vận hành).\n' "$WARNINGS"
  exit 0
fi
printf 'KẾT LUẬN: Hermes đang khớp repo và sẵn sàng.\n'
exit 0
