#!/usr/bin/env bash
set -uo pipefail

# ============================================================================
# Chẩn đoán: Hermes đã có quyền GitHub chưa? (CHỈ ĐỌC — không ghi gì)
#
#   bash scripts/hermes-github-check.sh
#   bash scripts/hermes-github-check.sh --repo ZeusOpenAI/ZEUS --quiet
#
# Kiểm:
#   1. Token có trong môi trường hoặc $HERMES_HOME/.env không (chỉ báo tên + nguồn)
#   2. Token còn sống không, đăng nhập bằng tài khoản nào
#   3. Scopes (classic) hoặc quyền repo (fine-grained)
#   4. Có quyền ghi code trên repo không (admin/maintain/push)
#   5. `git ls-remote` có chạy được không (chứng minh credential helper OK)
#   6. Thiết lập Actions của repo: token mặc định của workflow là read hay write
#
# Mã thoát: 0 = OK, 1 = có vấn đề, 2 = chưa có token
# Không bao giờ in giá trị token.
# ============================================================================

REPO_SLUG="${REPO_SLUG:-ZeusOpenAI/ZEUS}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ENV_FILE="$HERMES_HOME/.env"
API="https://api.github.com"
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) shift; REPO_SLUG="${1:-}" ;;
    --quiet) QUIET=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Tham số không hỗ trợ: $1" >&2; exit 2 ;;
  esac
  shift
done

PROBLEMS=0
WARNINGS=0
ok()   { [ "$QUIET" = "1" ] || printf '  ✓ %s\n' "$*"; }
warn() { WARNINGS=$((WARNINGS+1)); printf '  ⚠ %s\n' "$*"; }
bad()  { PROBLEMS=$((PROBLEMS+1)); printf '  ✗ %s\n' "$*"; }
head_() { [ "$QUIET" = "1" ] || printf '\n== %s ==\n' "$*"; }

# ── 1. Tìm token ────────────────────────────────────────────────────────────
head_ "Token"
# Ưu tiên .env của chính Hermes: đó mới là thứ gateway thực sự nạp.
# (env var trong shell hiện tại có thể là token của công cụ khác — dễ gây kết luận sai.)
TOKEN=""
SRC=""
if [ -f "$ENV_FILE" ]; then
  for var in GITHUB_TOKEN GH_TOKEN; do
    val="$(grep -E "^${var}=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"'"'"'[:space:]')"
    if [ -n "$val" ]; then TOKEN="$val"; SRC="$ENV_FILE"; break; fi
  done
fi

if [ -z "$TOKEN" ]; then
  for var in GITHUB_TOKEN GH_TOKEN; do
    val="$(printenv "$var" 2>/dev/null || true)"
    if [ -n "$val" ]; then TOKEN="$val"; SRC="biến môi trường \$$var"; break; fi
  done
fi

if [ -z "$TOKEN" ]; then
  bad "chưa có GITHUB_TOKEN/GH_TOKEN (không thấy trong env lẫn $ENV_FILE)"
  printf '\nChạy: bash scripts/hermes-github-setup.sh --repo %s\n' "$REPO_SLUG" >&2
  exit 2
fi
ok "có token (nguồn: $SRC, ${#TOKEN} ký tự)"

if [ -f "$ENV_FILE" ]; then
  perm="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE" 2>/dev/null || echo '?')"
  [ "$perm" = "600" ] && ok "$ENV_FILE quyền 600" || warn "$ENV_FILE quyền $perm (nên 600)"
fi

# ── 2. Token còn sống? ──────────────────────────────────────────────────────
head_ "Xác thực"
HDR="$(mktemp)"
BODY="$(curl -sS -m 20 -D "$HDR" -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" "$API/user" -w '\n%{http_code}' 2>/dev/null)"
CODE="$(printf '%s' "$BODY" | tail -1)"
JSON="$(printf '%s' "$BODY" | sed '$d')"

if [ "$CODE" != "200" ]; then
  rm -f "$HDR"
  case "$CODE" in
    401) bad "token không hợp lệ hoặc đã bị thu hồi (401)" ;;
    403) bad "token bị chặn (403) — hết hạn, SSO, hoặc rate limit" ;;
    *)   bad "GitHub trả HTTP $CODE" ;;
  esac
  printf '\nTạo token mới tại: https://github.com/settings/tokens\n' >&2
  exit 1
fi

LOGIN="$(printf '%s' "$JSON" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("login",""))' 2>/dev/null)"
ok "đăng nhập: ${LOGIN:-?}"

SCOPES="$(grep -i '^x-oauth-scopes:' "$HDR" | cut -d: -f2- | tr -d ' \r')"
rm -f "$HDR"
if [ -n "$SCOPES" ]; then
  ok "classic PAT · scopes: $SCOPES"
  case ",$SCOPES," in *,repo,*) ok "có 'repo' (ghi code)" ;; *) warn "thiếu 'repo' → không ghi code được" ;; esac
  case ",$SCOPES," in *,workflow,*) ok "có 'workflow' (sửa .github/workflows/)" ;; *) warn "thiếu 'workflow' → không sửa được workflow" ;; esac
else
  ok "fine-grained PAT (không có scope header — xét quyền theo repo bên dưới)"
fi

# ── 3. Quyền trên repo ──────────────────────────────────────────────────────
head_ "Repo $REPO_SLUG"
RBODY="$(curl -sS -m 20 -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" "$API/repos/$REPO_SLUG" -w '\n%{http_code}' 2>/dev/null)"
RCODE="$(printf '%s' "$RBODY" | tail -1)"
RJSON="$(printf '%s' "$RBODY" | sed '$d')"
TMPJ="$(mktemp)"; printf '%s' "$RJSON" > "$TMPJ"

if [ "$RCODE" = "200" ]; then
  set +e
  python3 - "$TMPJ" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
p = d.get("permissions") or {}
print(f"  · private={d.get('private')} default_branch={d.get('default_branch')} archived={d.get('archived')}")
print(f"  · admin={p.get('admin')} maintain={p.get('maintain')} push={p.get('push')} pull={p.get('pull')}")
sys.exit(0 if (p.get("admin") or p.get("maintain") or p.get("push")) else 1)
PY
  RC=$?
  set -e
  [ "$RC" -eq 0 ] && ok "có quyền GHI trên repo" || bad "chỉ ĐỌC trên repo (cần Contents: Read and write)"
else
  MSG="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("message",""))' "$TMPJ" 2>/dev/null)"
  bad "không truy cập được repo (HTTP $RCODE)${MSG:+ — $MSG}"
fi
rm -f "$TMPJ"

# ── 4. git leo thang ────────────────────────────────────────────────────────
head_ "git credential"
GITDIR="${ZEUS_HOME:-}"
if [ -z "$GITDIR" ]; then
  if git -C "$(dirname "$0")/.." rev-parse --git-dir >/dev/null 2>&1; then
    GITDIR="$(cd "$(dirname "$0")/.." && pwd)"
  fi
fi
if [ -n "$GITDIR" ]; then
  if GIT_TERMINAL_PROMPT=0 timeout 20 git -C "$GITDIR" ls-remote --heads origin >/dev/null 2>&1; then
    ok "git ls-remote origin OK ($GITDIR)"
  else
    warn "git ls-remote thất bại — credential helper chưa đúng (chạy lại setup, hoặc gh auth setup-git)"
  fi
else
  warn "không xác định được thư mục repo để test git"
fi

# ── 5. Thiết lập Actions của repo ───────────────────────────────────────────
head_ "GitHub Actions (quyền của GITHUB_TOKEN)"
ARESP="$(curl -sS -m 20 -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "$API/repos/$REPO_SLUG/actions/permissions/workflow" -w '\n%{http_code}' 2>/dev/null)"
ACODE="$(printf '%s' "$ARESP" | tail -1)"
ABODY="$(printf '%s' "$ARESP" | sed '$d')"
if [ "$ACODE" = "200" ]; then
  DEF="$(printf '%s' "$ABODY" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("default_workflow_permissions",""))' 2>/dev/null)"
  if [ "$DEF" = "write" ]; then
    ok "default_workflow_permissions = write (workflow được commit/push)"
  else
    bad "default_workflow_permissions = ${DEF:-?} → workflow KHÔNG push được, sửa tại:
         Settings → Actions → General → Workflow permissions → Read and write"
  fi
  CANPR="$(printf '%s' "$ABODY" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("can_approve_pull_request_reviews",""))' 2>/dev/null)"
  [ -n "$CANPR" ] && [ "$QUIET" = "0" ] && printf '  · can_approve_pull_request_reviews=%s\n' "$CANPR"
else
  warn "không đọc được thiết lập Actions (HTTP $ACODE) — token cần quyền Administration: Read"
fi

# ── Kết luận ────────────────────────────────────────────────────────────────
printf '\n'
if [ "$PROBLEMS" -gt 0 ]; then
  printf 'KẾT LUẬN: %d lỗi, %d cảnh báo.\n' "$PROBLEMS" "$WARNINGS"
  printf 'Xem docs/HERMES_GITHUB_TOKEN.md để cấp đúng quyền.\n'
  exit 1
fi
[ "$WARNINGS" -gt 0 ] && { printf 'KẾT LUẬN: OK, %d cảnh báo.\n' "$WARNINGS"; exit 0; }
printf 'KẾT LUẬN: Hermes có token hợp lệ và đủ quyền.\n'
exit 0
