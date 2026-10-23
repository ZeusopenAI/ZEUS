#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# VPS: kéo repo ZEUS mới nhất rồi đồng bộ skill + ngữ cảnh vào Hermes
#
# Chạy bằng systemd timer (xem hermes-repo-sync.timer) hoặc thủ công:
#   sudo -u hermes bash deploy/vps/hermes-repo-sync.sh
#   sudo -u hermes bash deploy/vps/hermes-repo-sync.sh --dry-run
#   bash deploy/vps/hermes-repo-sync.sh --no-restart
#
# Mã thoát:
#   0  = không có gì mới
#   10 = đã cập nhật (và đã restart gateway, trừ khi --no-restart)
# ============================================================================

ZEUS_HOME="${ZEUS_HOME:-/opt/zeus}"
HERMES_HOME="${HERMES_HOME:-/home/hermes/.hermes}"
VENV="${VENV:-$ZEUS_HOME/hermes-env}"
REPO_BRANCH="${REPO_BRANCH:-main}"
GATEWAY_UNIT="${GATEWAY_UNIT:-hermes-gateway}"

DRY_RUN=0
NO_RESTART=0
SYNC_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --dry-run)    DRY_RUN=1; SYNC_ARGS+=("--dry-run") ;;
    --no-restart) NO_RESTART=1 ;;
    -h|--help)    sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "Tham số không hỗ trợ: $arg" >&2; exit 2 ;;
  esac
done

say()  { printf '\n== %s ==\n' "$*"; }
run()  { if [ "$DRY_RUN" = "1" ]; then echo "[dry-run] $*"; else "$@"; fi; }

if [ ! -d "$ZEUS_HOME/.git" ]; then
  echo "LỖI: $ZEUS_HOME không phải git repo. Chạy deploy/vps/install-hermes-vps.sh trước." >&2
  exit 1
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
HERMES_HOME="$HERMES_HOME" bash "$ZEUS_HOME/scripts/hermes-sync.sh" \
  --with-memory ${SYNC_ARGS[@]+"${SYNC_ARGS[@]}"} 2>&1 | tee "$SYNC_LOG"
SYNC_RC=${PIPESTATUS[0]}
set -e

if [ "$SYNC_RC" -ne 0 ] && [ "$SYNC_RC" -ne 10 ]; then
  echo "LỖI: hermes-sync.sh trả mã $SYNC_RC" >&2
  exit "$SYNC_RC"
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

# Ưu tiên CLI của Hermes (nó biết cách restart đúng unit + chờ healthcheck);
# fallback sang systemctl nếu CLI không có.
if [ -x "$VENV/bin/hermes" ]; then
  "$VENV/bin/hermes" gateway restart || systemctl restart "$GATEWAY_UNIT"
else
  systemctl restart "$GATEWAY_UNIT"
fi

sleep 3
if systemctl is-active --quiet "$GATEWAY_UNIT"; then
  echo "    gateway: active — đã nạp skill mới"
  exit 10
fi

echo "LỖI: gateway không active sau restart. Xem: journalctl -u $GATEWAY_UNIT -n 50" >&2
exit 1
