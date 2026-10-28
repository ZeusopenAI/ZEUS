#!/usr/bin/env bash
set -uo pipefail

# ============================================================================
# KẾT PHIÊN — ghi báo cáo gửi Hermes (TÙY CHỌN, không bắt buộc).
#
#   bash scripts/hermes-session-closeout.sh --status DONE \
#        --summary "Đã sửa X, test Y pass" --tests "pytest -q: 12 passed"
#
#   --status        DONE | PARTIAL | BLOCKED   (mặc định DONE)
#   --summary       tóm tắt 1–3 câu (bắt buộc NẾU chạy script này)
#   --tests         bằng chứng đã kiểm chứng
#   --questions     câu hỏi cho chủ ở phiên sau
#   --blocker       việc đang chặn
#   --commit        git add + commit .ai/handoff (mặc định không commit)
#
# Không chạy closeout cũng hoàn toàn bình thường; thiếu báo cáo KHÔNG phải lỗi
# và KHÔNG được dùng để dừng / từ chối yêu cầu của Operator trong phiên sau.
# Xem AGENTS.md ĐIỀU 0 · docs/HERMES_OWNER_PROTOCOL.md
# ============================================================================

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2

if ! command -v python3 >/dev/null 2>&1; then
  echo "ℹ️  Không có python3 — bỏ qua báo cáo Hermes (tùy chọn). Tiếp tục bình thường." >&2
  exit 0
fi

exec python3 "$REPO_DIR/scripts/hermes_owner.py" --repo "$REPO_DIR" closeout "$@"
