#!/usr/bin/env bash
# ============================================================================
# Chẩn đoán 1 lệnh cho Hermes Owner Protocol — TRẢ LỜI "vì sao phiên nào cũng bị chặn?"
#
#   bash scripts/hermes-owner-status.sh
#
# Chỉ ĐỌC: không commit, không gọi LLM, không tốn credit, không sửa file nào.
# Mã thoát: 0 = có mệnh lệnh hiệu lực | 3 = chưa có (kèm việc cần làm) | 2 = lỗi môi trường
# ============================================================================
set -uo pipefail

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2

HANDOFF=".ai/handoff"
REPO_SLUG="${GITHUB_REPOSITORY:-ZeusopenAI/ZEUS}"
HAVE_GH=0
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && HAVE_GH=1

line() { printf '%s\n' "────────────────────────────────────────────────────────────────────────"; }
say()  { printf '%s\n' "$*"; }

say ""
say "ZEUS · Hermes Owner Protocol — chẩn đoán"
line

# ── 1. INBOX + STATE ────────────────────────────────────────────────────────
if [ -f "$HANDOFF/INBOX.md" ]; then
  first_line=$(head -n 1 "$HANDOFF/INBOX.md")
  if [ "$first_line" = "---" ]; then
    say "INBOX.md   : ✅ có front matter"
  else
    say "INBOX.md   : ❌ KHÔNG có front matter (dòng đầu: ${first_line:0:40})"
  fi
else
  say "INBOX.md   : ❌ không có file"
fi

python3 - "$HANDOFF/STATE.json" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
try:
    state = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"STATE.json : ❌ không đọc được ({exc})")
    raise SystemExit(0)
active = state.get("active_directive") or {}
history = state.get("history") or []
if active:
    print(f"STATE.json : active_directive #{active.get('number', '?')} "
          f"(hết hạn {active.get('valid_until', '?')}), {len(history)} mục lịch sử")
elif history:
    print(f"STATE.json : chưa có directive hiện hành, {len(history)} mục lịch sử")
else:
    print("STATE.json : ❌ CHƯA TỪNG có mệnh lệnh nào "
          f"(updated_by={state.get('updated_by')!r})")
PY

# ── 2. Nhánh trạng thái do workflow ghi ─────────────────────────────────────
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  remote_state=$(git ls-remote --heads origin 'hermes-owner/state' 2>/dev/null | head -n 1)
  if [ -n "$remote_state" ]; then
    say "Nhánh state: ✅ origin/hermes-owner/state tồn tại (${remote_state%%$'\t'*})"
  else
    say "Nhánh state: ❌ origin/hermes-owner/state CHƯA có ⇒ workflow chưa ghi được mệnh lệnh lần nào"
  fi
fi

# ── 3. Cờ tự động + secret + run gần nhất (cần gh) ─────────────────────────
if [ "$HAVE_GH" -eq 1 ]; then
  if auto_json=$(gh api "repos/$REPO_SLUG/actions/variables" 2>/dev/null); then
    auto=$(printf '%s' "$auto_json" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print("")
    raise SystemExit(0)
for item in data.get("variables", []):
    if item.get("name") == "HERMES_OWNER_AUTO":
        print(item.get("value", ""))
        break
' 2>/dev/null)
    if [ -z "$auto" ]; then
      say "Tự động    : ❌ HERMES_OWNER_AUTO chưa đặt ⇒ mọi run theo lịch bị SKIPPED"
    elif [ "$auto" = "on" ]; then
      say "Tự động    : ✅ HERMES_OWNER_AUTO=on (chạy mỗi 6 giờ + khi OUTBOX.md đổi)"
    else
      say "Tự động    : ❌ HERMES_OWNER_AUTO=$auto (phải là 'on')"
    fi
  else
    say "Tự động    : ?  không đọc được biến — token thiếu quyền Actions (cần admin/actions:read)"
  fi

  say ""
  say "5 run gần nhất của workflow:"
  gh run list --workflow "Hermes owner loop" --limit 5 \
    --json createdAt,event,conclusion \
    -q '.[] | "  \(.createdAt[0:16])  \(.event)  \(.conclusion // "đang chạy")"' 2>/dev/null \
    || say "  (không đọc được danh sách run)"
else
  say "Tự động    : ?  bỏ qua (không có gh hoặc chưa đăng nhập)"
fi

# ── 4. Kết luận ─────────────────────────────────────────────────────────────
say ""
line
if bash scripts/hermes-session-boot.sh --offline --quiet >/tmp/hop-boot.$$ 2>&1; then
  say "KẾT LUẬN: ✅ Có mệnh lệnh hiệu lực — phiên agent được phép làm việc."
  rm -f /tmp/hop-boot.$$
  exit 0
fi
rm -f /tmp/hop-boot.$$

say "KẾT LUẬN: ⛔ Chưa có mệnh lệnh ⇒ mọi phiên agent bị chặn ở BƯỚC 0."
say ""
say "Nguyên nhân thường gặp (theo thứ tự hay gặp):"
say "  1. Chưa từng bấm chạy workflow sau khi merge bản sửa tách mệnh lệnh."
say "  2. Bấm chạy nhưng chọn branch main (còn bug) thay vì branch đã sửa."
say "  3. Thiếu secret OPENROUTER_API_KEY ⇒ workflow fail ngay bước đầu."
say "  4. HERMES_OWNER_AUTO != on ⇒ run theo lịch bị skipped (không ai được báo)."
say ""
say "Việc cần làm:"
say "  Actions → “Hermes owner loop” → Run workflow"
say "    • branch: chọn nhánh chứa bản sửa (vd. arena/419e6e23-zeus) hoặc main SAU khi merge"
say "    • operator_note: ưu tiên của bạn cho lượt này"
say "  Rồi chạy lại: bash scripts/hermes-session-boot.sh"
say ""
say "Muốn khỏi lặp: đặt biến repo HERMES_OWNER_AUTO=on (Settings → Secrets and variables → Actions → Variables)."
say ""
exit 3
