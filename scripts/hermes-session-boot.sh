#!/usr/bin/env bash
set -uo pipefail

# ============================================================================
# HỎI THĂM HERMES — TÙY CHỌN, KHÔNG PHẢI BƯỚC 0, KHÔNG BAO GIỜ CHẶN PHIÊN.
#
#   bash scripts/hermes-session-boot.sh              # hỏi thăm (có thể bỏ qua hoàn toàn)
#   bash scripts/hermes-session-boot.sh --json       # kèm JSON máy đọc
#   bash scripts/hermes-session-boot.sh --offline    # không fetch nhánh trạng thái
#   bash scripts/hermes-session-boot.sh --live       # gọi Hermes trực tiếp nếu có binary + key
#   bash scripts/hermes-session-boot.sh --strict     # CHỈ khi Operator yêu cầu chế độ cũ
#
# Mặc định:
#   - Có gợi ý hợp lệ  -> in ra để agent tham khảo; thoát 0.
#   - Không có / hết hạn / seal sai / sai người ban hành / mất mạng / thiếu key
#     -> in "KHÔNG BẮT BUỘC, KHÔNG CHẶN PHIÊN"; thoát 0.
#   Mã 3/4/5/6 chỉ là TÍN HIỆU TRẠNG THÁI (vẫn có trong JSON), không phải lỗi phiên.
#   Chế độ strict (--strict hoặc HERMES_OWNER_STRICT=1) mới trả 3/4/5/6 và yêu cầu dừng.
#
# Quyền cao nhất luôn là Operator / người dùng trong phiên chat. Không AI nào được
# dùng kết quả (hay lỗi) của script này để từ chối hoặc trì hoãn yêu cầu của họ.
# Xem AGENTS.md ĐIỀU 0 · docs/HERMES_OWNER_PROTOCOL.md · docs/HERMES_SESSION_ERROR_RCA.md
# ============================================================================

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2

if ! command -v python3 >/dev/null 2>&1; then
  echo "ℹ️  Không có python3 — bỏ qua kênh Hermes (tùy chọn). Tiếp tục bình thường." >&2
  exit 0
fi

exec python3 "$REPO_DIR/scripts/hermes_owner.py" --repo "$REPO_DIR" boot "$@"
