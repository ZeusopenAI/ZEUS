#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Codespaces / Dev Container: cài Hermes từ agents/hermes + nạp skill + ngữ cảnh
#
#   bash .devcontainer/setup-hermes.sh              # cài (idempotent) + sync
#   bash .devcontainer/setup-hermes.sh --sync-only  # chỉ sync skill/context
#
# Chạy tự động bởi devcontainer.json:
#   postCreateCommand → cài lần đầu
#   postStartCommand  → mỗi lần mở Codespace, kéo skill + ngữ cảnh mới nhất
#
# Secrets (Codespaces → Settings → Secrets) được đọc từ biến môi trường và ghi
# vào $HERMES_HOME/.env (mode 600). Không bao giờ echo giá trị ra log.
# ============================================================================

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
VENV="${VENV:-$HERMES_HOME/venv}"
MODE="install"

case "${1:-}" in
  --sync-only) MODE="sync" ;;
  "" ) ;;
  *) echo "Tham số không hỗ trợ: $1 (chỉ có --sync-only)" >&2; exit 2 ;;
esac

say() { printf '\n== %s ==\n' "$*"; }

export PATH="$VENV/bin:$PATH"

if [ "$MODE" = "install" ]; then
  say "[1/3] Hermes runtime (venv: $VENV)"
  if [ -x "$VENV/bin/hermes" ]; then
    echo "    đã có: $("$VENV/bin/hermes" --version 2>/dev/null || echo 'hermes (không đọc được version)')"
  else
    python3 -m venv "$VENV"
    "$VENV/bin/python" -m pip install --quiet --upgrade pip
    echo "    đang cài agents/hermes (có thể mất 2-5 phút lần đầu)…"
    "$VENV/bin/python" -m pip install --quiet "$REPO_DIR/agents/hermes"
    "$VENV/bin/hermes" --version
  fi

  say "[2/3] Secrets → $HERMES_HOME/.env (mode 600, không in giá trị)"
  mkdir -p "$HERMES_HOME"
  ENV_FILE="$HERMES_HOME/.env"
  if [ -f "$ENV_FILE" ]; then
    echo "    .env đã tồn tại — giữ nguyên"
  else
    : > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    found=0
    for var in OPENROUTER_API_KEY GEMINI_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY \
               TELEGRAM_BOT_TOKEN TELEGRAM_ALLOWED_USERS; do
      val="${!var:-}"
      if [ -n "$val" ]; then
        printf '%s=%s\n' "$var" "$val" >> "$ENV_FILE"
        echo "    + $var (đã nhận từ secret)"
        found=$((found + 1))
      fi
    done
    if [ "$found" -eq 0 ]; then
      echo "    chưa thấy secret nào. Thêm ở: GitHub → Settings → Codespaces → Secrets"
      echo "    rồi mở lại Codespace, hoặc điền tay: nano $ENV_FILE"
    fi
  fi
fi

say "Đồng bộ skill + ngữ cảnh từ repo"
set +e
HERMES_HOME="$HERMES_HOME" bash "$REPO_DIR/scripts/hermes-sync.sh" --with-memory
SYNC_RC=$?
set -e
case "$SYNC_RC" in
  0|10) ;;
  *) echo "CẢNH BÁO: đồng bộ lỗi (mã $SYNC_RC) — Hermes vẫn dùng được bản cũ." >&2 ;;
esac

say "Sẵn sàng"
cat <<EOF
Hermes:  $VENV/bin/hermes
Skill:   $HERMES_HOME/skills  (đã có trong PATH của terminal mới)

Thử ngay:
    hermes --version
    hermes                     # mở TUI
    /skills                    # phải thấy edit-anh, zeus-context, qai-developer-manager…
    /edit-anh                  # mở menu 10 hiệu ứng chỉnh ảnh

Lưu ý: tạo/sửa ảnh cần model ảnh + key (OPENROUTER_API_KEY…) đã điền trong
$HERMES_HOME/.env. Không có key thì Hermes vẫn đọc skill nhưng không gọi được model.
EOF
