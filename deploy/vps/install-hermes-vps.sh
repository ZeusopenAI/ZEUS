#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Zeus / Quang Quý AI — cài Hermes Gateway 24/7 trên VPS Ubuntu (systemd)
#
# Script này KHÔNG nhận bất kỳ secret nào qua tham số. Secrets được điền thủ
# công vào $HERMES_HOME/.env sau khi script chạy xong (mode 600).
#
# Cách dùng:
#   sudo bash deploy/vps/install-hermes-vps.sh                 # cài đầy đủ
#   sudo bash deploy/vps/install-hermes-vps.sh --dry-run       # chỉ in ra
#   sudo bash deploy/vps/install-hermes-vps.sh --skip-install  # bỏ bước pip
#
# Yêu cầu: Ubuntu 22.04/24.04, chạy bằng sudo, có kết nối internet.
# Chi tiết vận hành: docs/RUNBOOK_247.md
# ============================================================================

ZEUS_USER="${ZEUS_USER:-hermes}"
ZEUS_GROUP="${ZEUS_GROUP:-$ZEUS_USER}"
ZEUS_HOME="${ZEUS_HOME:-/opt/zeus}"
HERMES_HOME="${HERMES_HOME:-/home/${ZEUS_USER}/.hermes}"
REPO_URL="${REPO_URL:-https://github.com/ZeusopenAI/ZEUS.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
VENV="${VENV:-${ZEUS_HOME}/hermes-env}"

DRY_RUN=0
SKIP_INSTALL=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)     DRY_RUN=1 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    *) echo "Tham số không hỗ trợ: $arg (chỉ có --dry-run, --skip-install)" >&2; exit 2 ;;
  esac
done

run() {
  if [ "$DRY_RUN" = "1" ]; then echo "[dry-run] $*"; else "$@"; fi
}

say() { printf '\n== %s ==\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: phải chạy bằng sudo/root." >&2
  exit 1
fi

say "[1/7] Gói hệ thống"
export DEBIAN_FRONTEND=noninteractive
run apt-get update -qq
run apt-get install -y -qq python3 python3-venv python3-pip git ca-certificates curl tzdata

say "[2/7] Tài khoản dịch vụ '${ZEUS_USER}' (không đăng nhập, không shell)"
if id "$ZEUS_USER" >/dev/null 2>&1; then
  echo "    đã tồn tại, bỏ qua"
else
  run useradd --system --create-home --home-dir "/home/${ZEUS_USER}" --shell /usr/sbin/nologin "$ZEUS_USER"
fi

say "[3/7] Mã nguồn ZEUS tại ${ZEUS_HOME} (branch ${REPO_BRANCH})"
if [ "$DRY_RUN" = "1" ]; then
  echo "[dry-run] git clone --branch ${REPO_BRANCH} ${REPO_URL} ${ZEUS_HOME}"
elif [ -d "${ZEUS_HOME}/.git" ]; then
  git -C "$ZEUS_HOME" fetch origin "$REPO_BRANCH" --quiet
  git -C "$ZEUS_HOME" reset --hard "origin/${REPO_BRANCH}" --quiet
  echo "    đã cập nhật lên $(git -C "$ZEUS_HOME" rev-parse --short HEAD)"
else
  run git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_URL" "$ZEUS_HOME"
fi

say "[4/7] Virtualenv + cài hermes-agent từ agents/hermes"
if [ "$SKIP_INSTALL" = "1" ]; then
  echo "    bỏ qua theo yêu cầu --skip-install"
else
  run python3 -m venv "$VENV"
  run "$VENV/bin/pip" install --upgrade pip
  run "$VENV/bin/pip" install "${ZEUS_HOME}/agents/hermes"
  if [ "$DRY_RUN" != "1" ]; then
    "$VENV/bin/hermes" --version
  fi
fi

say "[5/7] Thư mục runtime ${HERMES_HOME} (permission riêng tư)"
run install -d -m 700 -o "$ZEUS_USER" -g "$ZEUS_GROUP" "$HERMES_HOME"
if [ ! -f "${HERMES_HOME}/.env" ]; then
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] tạo ${HERMES_HOME}/.env (mode 600) từ agents/hermes/.env.example — CHỈ tên biến, không giá trị"
  else
    # Chỉ lấy TÊN BIẾN từ .env.example; giá trị mẫu để trống để tránh nhầm placeholder là thật.
    grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "${ZEUS_HOME}/agents/hermes/.env.example" 2>/dev/null \
      | sed 's/=.*/=/' > "${HERMES_HOME}/.env.tmp" || true
    {
      echo "# Điền secret tại đây. KHÔNG commit file này."
      echo "# Bắt buộc để bật Telegram 24/7:"
      echo "TELEGRAM_BOT_TOKEN="
      echo "TELEGRAM_ALLOWED_USERS="
      echo "# Model key (ít nhất một):"
      echo "OPENROUTER_API_KEY="
      echo "GEMINI_API_KEY="
      if [ -s "${HERMES_HOME}/.env.tmp" ]; then
        echo "# Các biến khác Hermes hỗ trợ (điền khi cần):"
        cat "${HERMES_HOME}/.env.tmp"
      fi
    } > "${HERMES_HOME}/.env"
    rm -f "${HERMES_HOME}/.env.tmp"
    chown "$ZEUS_USER:$ZEUS_GROUP" "${HERMES_HOME}/.env"
    chmod 600 "${HERMES_HOME}/.env"
  fi
else
  echo "    .env đã tồn tại, GIỮ NGUYÊN (không ghi đè secret)"
fi

say "[6/7] Quyền sở hữu"
run chown -R "$ZEUS_USER:$ZEUS_GROUP" "$ZEUS_HOME"
run chown -R "$ZEUS_USER:$ZEUS_GROUP" "/home/${ZEUS_USER}"

say "[7/7] Cài Hermes Gateway làm systemd service (tự khởi động khi boot)"
# hermes gateway install tự sinh unit, enable boot-start và (tuỳ chọn) start ngay.
# Phải chạy bằng root (--system ghi unit vào /etc/systemd/system), còn tiến trình
# gateway sẽ chạy dưới user thường qua --run-as-user.
run env HOME="/home/${ZEUS_USER}" "$VENV/bin/hermes" gateway install --system --run-as-user "$ZEUS_USER" --start-now

cat <<'NEXT'

Hoàn tất phần cài đặt. Bước còn lại BẮT BUỘC (thủ công, không script hoá):
  1. sudo nano /home/hermes/.hermes/.env   # điền TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, model key
  2. sudo systemctl restart hermes-gateway  # hoặc: hermes gateway restart
  3. bash deploy/vps/healthcheck.sh         # phải ra "HEALTHY"
  4. Nhắn 1 tin Telegram cho bot → bot phải trả lời (round-trip test)

Chi tiết vận hành, backup, rollback, reboot drill: docs/RUNBOOK_247.md
NEXT
