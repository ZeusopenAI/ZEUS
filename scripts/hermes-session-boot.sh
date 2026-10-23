#!/usr/bin/env bash
set -uo pipefail

# ============================================================================
# BƯỚC 0 CỦA MỌI PHIÊN AGENT — gọi chủ (Hermes) lấy mệnh lệnh trước khi làm việc.
#
#   bash scripts/hermes-session-boot.sh              # chạy chuẩn
#   bash scripts/hermes-session-boot.sh --json       # kèm JSON máy đọc
#   bash scripts/hermes-session-boot.sh --offline    # không fetch nhánh trạng thái
#   bash scripts/hermes-session-boot.sh --live       # cho phép gọi Hermes trực tiếp
#
# Mã thoát: 0 = có mệnh lệnh | 3 = chưa có | 4 = hết hạn | 5 = seal sai | 6 = sai người ban hành
# Mọi mã khác 0 nghĩa là PHIÊN PHẢI DỪNG (chính sách đã chốt với Operator).
# Xem docs/HERMES_OWNER_PROTOCOL.md
# ============================================================================

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Không có python3 — không chạy được Hermes Owner Protocol." >&2
  exit 2
fi

exec python3 "$REPO_DIR/scripts/hermes_owner.py" --repo "$REPO_DIR" boot "$@"
