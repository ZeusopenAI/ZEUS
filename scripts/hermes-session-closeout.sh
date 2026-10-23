#!/usr/bin/env bash
set -uo pipefail

# ============================================================================
# KẾT PHIÊN — ghi báo cáo gửi Hermes vào .ai/handoff/OUTBOX.md
#
#   bash scripts/hermes-session-closeout.sh --status DONE \
#        --summary "Đã sửa X, test Y pass" --tests "pytest -q: 12 passed"
#
#   --status        DONE | PARTIAL | BLOCKED   (mặc định DONE)
#   --summary       tóm tắt 1–3 câu (bắt buộc; hoặc --summary-file / stdin)
#   --tests         bằng chứng đã kiểm chứng
#   --questions     câu hỏi cho chủ ở phiên sau
#   --blocker       việc đang chặn
#   --commit        git add + commit .ai/handoff (mặc định không commit)
#
# Xem docs/HERMES_OWNER_PROTOCOL.md
# ============================================================================

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Không có python3 — không chạy được Hermes Owner Protocol." >&2
  exit 2
fi

exec python3 "$REPO_DIR/scripts/hermes_owner.py" --repo "$REPO_DIR" closeout "$@"
