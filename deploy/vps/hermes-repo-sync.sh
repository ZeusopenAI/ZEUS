#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# VPS: kéo repo ZEUS mới nhất rồi đồng bộ skill + ngữ cảnh vào Hermes
#
# Chạy bằng systemd timer (hermes-repo-sync.timer), từ GitHub Actions qua SSH,
# hoặc thủ công:
#   sudo /opt/zeus/deploy/vps/hermes-repo-sync.sh           # root: sync bằng user hermes
#   sudo -u hermes bash deploy/vps/hermes-repo-sync.sh      # không phải root
#   sudo /opt/zeus/deploy/vps/hermes-repo-sync.sh --dry-run
#   sudo /opt/zeus/deploy/vps/hermes-repo-sync.sh --no-restart
#
# Mã thoát:
#   0  = không có gì mới
#   10 = đã cập nhật (và đã restart gateway, trừ khi --no-restart)
#   3  = từ chối chạy: bản checkout không sạch / sai nhánh (bảo vệ dữ liệu)
# ============================================================================

ZEUS_HOME="${ZEUS_HOME:-/opt/zeus}"
HERMES_HOME="${HERMES_HOME:-/home/hermes/.hermes}"
VENV="${VENV:-$ZEUS_HOME/hermes-env}"
REPO_BRANCH="${REPO_BRANCH:-main}"
GATEWAY_UNIT="${GATEWAY_UNIT:-hermes-gateway}"
HERMES_USER="${HERMES_USER:-hermes}"

DRY_RUN=0
NO_RESTART=0
FORCE=0
SYNC_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --dry-run)    DRY_RUN=1; SYNC_ARGS+=("--dry-run") ;;
    --no-restart) NO_RESTART=1 ;;
    --force)      FORCE=1 ;;
    -h|--help)    sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "Tham số không hỗ trợ: $arg" >&2; exit 2 ;;
  esac
done

say()  { printf '\n== %s ==\n' "$*"; }
run()  { if [ "$DRY_RUN" = "1" ]; then echo "[dry-run] $*"; else "$@"; fi; }
die()  { echo "LỖI: $*" >&2; exit 1; }

if [ ! -d "$ZEUS_HOME/.git" ]; then
  die "$ZEUS_HOME không phải git repo. Chạy deploy/vps/install-hermes-vps.sh trước."
fi

# ── Chốt an toàn ────────────────────────────────────────────────────────────
# Script này chạy `git reset --hard`, nên phải chắc chắn đang ở bản checkout dành
# riêng cho Hermes — không phải máy đang có người sửa code — để không nuốt mất
# thay đổi chưa commit.
CURRENT_BRANCH="$(git -C "$ZEUS_HOME" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
DIRTY="$(git -C "$ZEUS_HOME" status --porcelain 2>/dev/null | grep -v '^?? ' || true)"
DIRTY_COUNT="$(printf '%s' "$DIRTY" | grep -c . || true)"

if [ "$FORCE" != "1" ]; then
  if [ "$CURRENT_BRANCH" != "$REPO_BRANCH" ]; then
    cat >&2 <<EOF
LỖI: $ZEUS_HOME đang ở nhánh '$CURRENT_BRANCH', không phải '$REPO_BRANCH'.
      Từ chối chạy để không ghi đè nhánh đang làm việc.
      Nếu chắc chắn: --force, hoặc đổi nhánh bằng tay:
        git -C $ZEUS_HOME checkout $REPO_BRANCH
EOF
    exit 3
  fi
  if [ "$DIRTY_COUNT" -gt 0 ]; then
    {
      echo "LỖI: $ZEUS_HOME có $DIRTY_COUNT thay đổi chưa commit — 'git reset --hard' sẽ xoá mất:"
      printf '%s\n' "$DIRTY" | head -8 | sed 's/^/      /'
      echo "      Commit/stash trước, hoặc dùng --force nếu muốn bỏ các thay đổi đó."
    } >&2
    exit 3
  fi
fi

# Nếu chạy bằng root: phần ghi vào $HERMES_HOME phải do user Hermes thực hiện,
# nếu không file skill sẽ thuộc root và gateway (chạy bằng user hermes) không đọc được.
RUN_AS=()
if [ "$(id -u)" -eq 0 ] && id "$HERMES_USER" >/dev/null 2>&1; then
  RUN_AS=(runuser -u "$HERMES_USER" --)
  echo "Chạy phần đồng bộ dưới user: $HERMES_USER"
fi

say "[1/3] Cập nhật mã nguồn (${REPO_BRANCH})"
BEFORE="$(git -C "$ZEUS_HOME" rev-parse HEAD)"
run git -C "$ZEUS_HOME" fetch origin "$REPO_BRANCH" --quiet
run git -C "$ZEUS_HOME" reset --hard "origin/${REPO_BRANCH}" --quiet
AFTER="$(git -C "$ZEUS_HOME" rev-parse HEAD)"
if [ "$BEFORE" = "$AFTER" ]; then
  echo "    code: không đổi ($(git -C "$ZEUS_HOME" rev-parse --short HEAD))"
else
  echo "    code: $(git -C "$ZEUS_HOME" rev-parse --short "$BEFORE") → $(git -C "$ZEUS_HOME" rev-parse --short "$AFTER")"
fi

say "[2/3] Đồng bộ skill + ngữ cảnh vào $HERMES_HOME"
SYNC_LOG="$(mktemp)"
trap 'rm -f "$SYNC_LOG"' EXIT
set +e
HERMES_HOME="$HERMES_HOME" ${RUN_AS[@]+"${RUN_AS[@]}"} bash "$ZEUS_HOME/scripts/hermes-sync.sh" \
  --with-memory ${SYNC_ARGS[@]+"${SYNC_ARGS[@]}"} 2>&1 | tee "$SYNC_LOG"
SYNC_RC=${PIPESTATUS[0]}
set -e

if [ "$SYNC_RC" -ne 0 ] && [ "$SYNC_RC" -ne 10 ]; then
  die "hermes-sync.sh trả mã $SYNC_RC"
fi

# --dry-run: sync luôn trả 0, nên suy ra "có thay đổi" từ log
if [ "$DRY_RUN" = "1" ] && grep -q "Có thay đổi (dry-run" "$SYNC_LOG"; then
  SYNC_RC=10
fi

say "[3/3] Nạp lại Hermes gateway"
if [ "$SYNC_RC" -eq 0 ] && [ "$BEFORE" = "$AFTER" ]; then
  echo "    không có thay đổi — không restart"
  exit 0
fi

if [ "$NO_RESTART" = "1" ]; then
  echo "    bỏ qua restart theo --no-restart (nhớ restart tay)"
  exit 10
fi

if [ "$DRY_RUN" = "1" ]; then
  echo "[dry-run] hermes gateway restart (hoặc systemctl restart $GATEWAY_UNIT)"
  exit 10
fi

# root → systemctl (chắc chắn có quyền). Không phải root → thử CLI của Hermes,
# rồi tới sudo -n (nếu đã cấu hình sudoers), cuối cùng mới báo lỗi rõ ràng.
if [ "$(id -u)" -eq 0 ]; then
  systemctl restart "$GATEWAY_UNIT"
elif [ -x "$VENV/bin/hermes" ] && "$VENV/bin/hermes" gateway restart 2>/dev/null; then
  :
elif sudo -n systemctl restart "$GATEWAY_UNIT" 2>/dev/null; then
  :
else
  die "không đủ quyền restart $GATEWAY_UNIT. Chạy: sudo $ZEUS_HOME/deploy/vps/hermes-repo-sync.sh"
fi

sleep 3
if systemctl is-active --quiet "$GATEWAY_UNIT"; then
  echo "    gateway: active — đã nạp skill mới"
  exit 10
fi

die "gateway không active sau restart. Xem: journalctl -u $GATEWAY_UNIT -n 50"
