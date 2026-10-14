#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Zeus / Quang Quý AI — healthcheck Hermes Gateway 24/7
# Dùng cho: cron, uptime monitor, hoặc chạy tay sau khi thao tác vận hành.
#
# Exit codes:
#   0 = HEALTHY   1 = DEGRADED (process sống nhưng chưa xác minh được kênh)
#   2 = DOWN (process chết / systemctl không thấy service)
#
# Không in secret ra stdout; chỉ in trạng thái.
# ============================================================================

SERVICE="${SERVICE:-hermes-gateway}"
HERMES_BIN="${HERMES_BIN:-/opt/zeus/hermes-env/bin/hermes}"
RUN_AS="${RUN_AS:-hermes}"
RUN_HOME="${RUN_HOME:-/home/${RUN_AS}}"

errors=0
warnings=0

section() { printf '\n[%s]\n' "$*"; }

section "1. systemd service: ${SERVICE}"
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q "^${SERVICE}"; then
  state="$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
  enabled="$(systemctl is-enabled "$SERVICE" 2>/dev/null || true)"
  echo "  active:  ${state:-unknown}"
  echo "  enabled: ${enabled:-unknown} (phải là enabled để tự chạy sau reboot)"
  [ "$state" = "active" ] || errors=$((errors+1))
  [ "$enabled" = "enabled" ] || warnings=$((warnings+1))
else
  echo "  KHÔNG thấy unit ${SERVICE} — gateway chưa được cài như service."
  errors=$((errors+1))
fi

section "2. Hermes CLI phản hồi"
if [ -x "$HERMES_BIN" ]; then
  ver="$("$HERMES_BIN" --version 2>/dev/null | head -1 || true)"
  if [ -n "$ver" ]; then
    echo "  OK: ${ver}"
  else
    echo "  FAIL: ${HERMES_BIN} không trả về phiên bản"
    errors=$((errors+1))
  fi
else
  echo "  FAIL: không tìm thấy ${HERMES_BIN}"
  errors=$((errors+1))
fi

section "3. Gateway status"
if [ -x "$HERMES_BIN" ]; then
  gs="$(sudo -u "$RUN_AS" env HOME="$RUN_HOME" "$HERMES_BIN" gateway status 2>&1 || true)"
  echo "$gs" | sed 's/^/  /'
  echo "$gs" | grep -qiE "running|active" || warnings=$((warnings+1))
fi

section "4. Kênh Telegram đã cấu hình chưa (chỉ kiểm tra sự tồn tại của giá trị)"
ENV_FILE="${ENV_FILE:-${RUN_HOME}/.hermes/.env}"
if [ -f "$ENV_FILE" ]; then
  if sudo -u "$RUN_AS" grep -qE '^TELEGRAM_BOT_TOKEN=..+' "$ENV_FILE"; then
    echo "  TELEGRAM_BOT_TOKEN: ĐÃ ĐIỀN"
  else
    echo "  TELEGRAM_BOT_TOKEN: CHƯA ĐIỀN — bot sẽ không nhận tin"
    warnings=$((warnings+1))
  fi
else
  echo "  Không thấy ${ENV_FILE}"
  errors=$((errors+1))
fi

section "Kết luận"
if [ "$errors" -gt 0 ]; then
  echo "DOWN — ${errors} lỗi nghiêm trọng. Xem: journalctl -u ${SERVICE} -n 50 --no-pager"
  exit 2
fi
if [ "$warnings" -gt 0 ]; then
  echo "DEGRADED — process sống nhưng còn ${warnings} cảnh báo (thường là chưa điền token Telegram)."
  exit 1
fi
echo "HEALTHY"
exit 0
