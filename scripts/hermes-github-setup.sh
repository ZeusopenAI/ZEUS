#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Gắn GitHub token vào Hermes (VPS / Codespace) — có kiểm tra quyền thật
#
# Token KHÔNG bao giờ được truyền qua tham số dòng lệnh (sẽ lộ trong `ps` và
# shell history). Chỉ nhận qua stdin hoặc biến môi trường.
#
# CÁCH DÙNG AN TOÀN (dán token khi được hỏi, không gõ vào lệnh):
#   bash scripts/hermes-github-setup.sh --repo ZeusOpenAI/ZEUS
#     → script hỏi token (ẩn ký tự), hoặc đọc từ $HERMES_GH_TOKEN nếu có
#
# Các cách khác:
#   HERMES_GH_TOKEN=xxx bash scripts/hermes-github-setup.sh        # vẫn lộ trong env của tiến trình
#   bash scripts/hermes-github-setup.sh < token.txt                # đọc từ file
#   bash scripts/hermes-github-setup.sh --dry-run                  # chỉ kiểm, không ghi
#   bash scripts/hermes-github-setup.sh --test-write               # thử tạo/xoá 1 nhánh
#
# Script sẽ:
#   1. Kiểm định dạng token (ghp_ / github_pat_ / gho_ / ghs_)
#   2. Gọi API /user để xác nhận token sống, in login (không in token)
#   3. Đọc quyền thật trên repo (admin/maintain/push/pull)
#   4. Ghi GITHUB_TOKEN + GH_TOKEN vào $HERMES_HOME/.env (mode 600, có backup)
#   5. Cấu hình `gh` làm credential helper để `git push` chạy được
#   6. (tuỳ chọn) thử tạo + xoá 1 nhánh để chứng minh có quyền ghi
#
# Mã thoát: 0 = OK, 1 = token/API lỗi, 2 = tham số sai, 3 = token chỉ đọc (khi dùng --test-write)
# ============================================================================

REPO_SLUG="${REPO_SLUG:-ZeusOpenAI/ZEUS}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
API="https://api.github.com"

DRY_RUN=0
TEST_WRITE=0
SKIP_GH=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)    DRY_RUN=1 ;;
    --test-write) TEST_WRITE=1 ;;
    --no-gh)      SKIP_GH=1 ;;
    --repo)       shift; REPO_SLUG="${1:-}" ;;
    -h|--help)    sed -n '2,30p' "$0"; exit 0 ;;
    *)            echo "Tham số không hỗ trợ: $1" >&2; exit 2 ;;
  esac
  shift
done

say()  { printf '\n== %s ==\n' "$*"; }
info() { printf '   %s\n' "$*"; }
die()  { echo "LỖI: $*" >&2; exit 1; }

command -v curl >/dev/null 2>&1 || die "cần có curl"

# ── 1. Nhận token ───────────────────────────────────────────────────────────
say "Nhận token"
TOKEN="${HERMES_GH_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  if [ -t 0 ]; then
    # Có terminal: hỏi và ẩn ký tự, không lưu history
    printf '   Dán GitHub token (ký tự sẽ bị ẩn): '
    IFS= read -rs TOKEN
    printf '\n'
  else
    # Không có terminal: đọc từ stdin (pipe/file)
    IFS= read -r TOKEN || true
  fi
fi

# Bỏ khoảng trắng/xuống dòng thừa (dán từ clipboard thường dính)
TOKEN="$(printf '%s' "$TOKEN" | tr -d '[:space:]')"

[ -n "$TOKEN" ] || die "không nhận được token (dùng stdin hoặc HERMES_GH_TOKEN)"
[ "${#TOKEN}" -ge 20 ] || die "token quá ngắn (${#TOKEN} ký tự) — kiểm tra lại khi copy"

case "$TOKEN" in
  ghp_*|gho_*|ghu_*|ghs_*|ghr_*) info "loại: classic PAT (${TOKEN:0:4}…)" ;;
  github_pat_*)                   info "loại: fine-grained PAT" ;;
  *)                              info "cảnh báo: không khớp mẫu token GitHub thông dụng — vẫn thử tiếp" ;;
esac
info "độ dài: ${#TOKEN} ký tự (không in giá trị)"

# ── 2. Xác thực token ───────────────────────────────────────────────────────
say "Xác thực với GitHub"
RESP="$(curl -sS -m 20 -D /tmp/gh-hdr.$$ -H "Authorization: Bearer $TOKEN" \
        -H "Accept: application/vnd.github+json" "$API/user" -w '\n%{http_code}' 2>&1)" || {
  rm -f /tmp/gh-hdr.$$
  die "không gọi được api.github.com (mạng bị chặn?)"
}
CODE="$(printf '%s' "$RESP" | tail -1)"
BODY="$(printf '%s' "$RESP" | sed '$d')"

if [ "$CODE" != "200" ]; then
  rm -f /tmp/gh-hdr.$$
  case "$CODE" in
    401) die "token không hợp lệ hoặc đã bị thu hồi (401). Tạo token mới rồi chạy lại." ;;
    403) die "token bị chặn (403) — có thể hết hạn, bị SSO chặn, hoặc bị rate-limit." ;;
    *)   die "GitHub trả HTTP $CODE" ;;
  esac
fi

LOGIN="$(printf '%s' "$BODY" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("login",""))' 2>/dev/null || echo "")"
[ -n "$LOGIN" ] || die "không đọc được login từ phản hồi API"
info "đăng nhập với tư cách: $LOGIN"

SCOPES="$(grep -i '^x-oauth-scopes:' /tmp/gh-hdr.$$ | cut -d: -f2- | tr -d ' \r' || true)"
rm -f /tmp/gh-hdr.$$
if [ -n "$SCOPES" ]; then
  info "scopes (classic): $SCOPES"
  case ",$SCOPES," in
    *,repo,*) info "có scope 'repo' → đọc/ghi code được" ;;
    *)        info "KHÔNG có scope 'repo' → chỉ đọc được repo public" ;;
  esac
  case ",$SCOPES," in
    *,workflow,*) info "có scope 'workflow' → sửa được file .github/workflows/" ;;
    *)            info "thiếu scope 'workflow' → KHÔNG sửa được .github/workflows/" ;;
  esac
else
  info "fine-grained PAT: không có header scope — quyền xác định theo repo bên dưới"
fi

# ── 3. Quyền thật trên repo ─────────────────────────────────────────────────
say "Quyền trên repo $REPO_SLUG"
PERM_RESP="$(curl -sS -m 20 -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" "$API/repos/$REPO_SLUG" -w '\n%{http_code}' 2>&1)"
PCODE="$(printf '%s' "$PERM_RESP" | tail -1)"
PBODY="$(printf '%s' "$PERM_RESP" | sed '$d')"

WRITABLE=0
if [ "$PCODE" = "200" ]; then
  # Ghi body ra file rồi đọc bằng python — không dùng pipe vì heredoc đã chiếm stdin.
  REPO_JSON="$(mktemp)"
  printf '%s' "$PBODY" > "$REPO_JSON"
  set +e
  python3 - "$REPO_JSON" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
p = d.get("permissions") or {}
print(f"   private={d.get('private')}  default_branch={d.get('default_branch')}")
print(f"   admin={p.get('admin')} maintain={p.get('maintain')} push={p.get('push')} triage={p.get('triage')} pull={p.get('pull')}")
if p.get("admin") or p.get("maintain") or p.get("push"):
    print("   → CÓ quyền ghi (push/commit/PR)")
    sys.exit(0)
print("   → CHỈ ĐỌC: token không ghi được code (cần Contents: Read and write)")
sys.exit(1)
PY
  WRITABLE=$?
  set -e
  rm -f "$REPO_JSON"
else
  info "không đọc được repo (HTTP $PCODE) — token có thể không được cấp quyền repo này"
  PBODY_MSG="$(printf '%s' "$PBODY" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("message",""))' 2>/dev/null || true)"
  [ -n "$PBODY_MSG" ] && info "GitHub nói: $PBODY_MSG"
fi

# ── 4. Ghi vào .env của Hermes ──────────────────────────────────────────────
say "Ghi vào $HERMES_HOME/.env"
ENV_FILE="$HERMES_HOME/.env"

if [ "$DRY_RUN" = "1" ]; then
  info "[dry-run] sẽ ghi GITHUB_TOKEN + GH_TOKEN vào $ENV_FILE (mode 600), có backup"
else
  mkdir -p "$HERMES_HOME"
  chmod 700 "$HERMES_HOME" 2>/dev/null || true

  if [ -f "$ENV_FILE" ]; then
    cp -a "$ENV_FILE" "$ENV_FILE.bak-$(date +%Y%m%d-%H%M%S)"
    info "đã backup .env cũ"
    # Xoá dòng cũ của 2 biến này rồi thêm dòng mới (không đụng biến khác)
    grep -vE '^(GITHUB_TOKEN|GH_TOKEN)=' "$ENV_FILE" > "$ENV_FILE.tmp" || true
  else
    : > "$ENV_FILE.tmp"
    printf '# Hermes runtime secrets — KHÔNG commit file này\n' >> "$ENV_FILE.tmp"
  fi

  printf 'GITHUB_TOKEN=%s\n' "$TOKEN" >> "$ENV_FILE.tmp"
  printf 'GH_TOKEN=%s\n'     "$TOKEN" >> "$ENV_FILE.tmp"
  mv "$ENV_FILE.tmp" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  chown "$(id -u):$(id -g)" "$ENV_FILE" 2>/dev/null || true
  info "đã ghi (mode 600): GITHUB_TOKEN, GH_TOKEN"
fi

# ── 5. Cấu hình git dùng token ──────────────────────────────────────────────
say "Cấu hình git credentials"
if [ "$SKIP_GH" = "1" ]; then
  info "bỏ qua theo --no-gh"
elif ! command -v gh >/dev/null 2>&1; then
  info "chưa có gh CLI → cấu hình git credential store trực tiếp"
  if [ "$DRY_RUN" = "1" ]; then
    info "[dry-run] git config --global credential.helper store + ~/.git-credentials"
  else
    git config --global credential.helper store
    CRED="$HOME/.git-credentials"
    touch "$CRED" && chmod 600 "$CRED"
    grep -v 'github.com' "$CRED" > "$CRED.tmp" 2>/dev/null || true
    printf 'https://x-access-token:%s@github.com\n' "$TOKEN" >> "$CRED.tmp"
    mv "$CRED.tmp" "$CRED"
    chmod 600 "$CRED"
    info "đã ghi ~/.git-credentials (mode 600) — lưu ý: đây là plaintext, chỉ dùng trên máy tin cậy"
  fi
else
  if [ "$DRY_RUN" = "1" ]; then
    info "[dry-run] gh auth login --with-token; gh auth setup-git"
  else
    if printf '%s' "$TOKEN" | gh auth login --with-token 2>/dev/null; then
      gh auth setup-git >/dev/null 2>&1 && info "gh auth login OK + git credential helper đã bật"
      gh auth status 2>&1 | sed 's/^/   /' | head -6
    else
      info "gh auth login thất bại — dùng fallback credential store"
      git config --global credential.helper store
      CRED="$HOME/.git-credentials"; touch "$CRED"; chmod 600 "$CRED"
      grep -v 'github.com' "$CRED" > "$CRED.tmp" 2>/dev/null || true
      printf 'https://x-access-token:%s@github.com\n' "$TOKEN" >> "$CRED.tmp"
      mv "$CRED.tmp" "$CRED"; chmod 600 "$CRED"
      info "đã dùng fallback ~/.git-credentials"
    fi
  fi
fi

# ── 6. Thử ghi thật (tuỳ chọn) ──────────────────────────────────────────────
if [ "$TEST_WRITE" = "1" ]; then
  say "Thử quyền ghi (tạo + xoá 1 nhánh test)"
  BR="hermes-token-test-$(date +%s)"
  SHA_MAIN="$(curl -sS -m 20 -H "Authorization: Bearer $TOKEN" \
    "$API/repos/$REPO_SLUG/git/ref/heads/$(printf '%s' "$PBODY" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("default_branch","main"))' 2>/dev/null || echo main)" \
    | python3 -c 'import json,sys;print(json.load(sys.stdin).get("object",{}).get("sha",""))' 2>/dev/null || echo "")"

  if [ -z "$SHA_MAIN" ]; then
    info "không đọc được SHA của nhánh mặc định → bỏ qua test"
  elif [ "$DRY_RUN" = "1" ]; then
    info "[dry-run] sẽ tạo nhánh $BR từ $SHA_MAIN rồi xoá"
  else
    CREATE="$(curl -sS -m 20 -X POST -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/vnd.github+json" "$API/repos/$REPO_SLUG/git/refs" \
      -d "{\"ref\":\"refs/heads/$BR\",\"sha\":\"$SHA_MAIN\"}" -w '\n%{http_code}')"
    CCODE="$(printf '%s' "$CREATE" | tail -1)"
    if [ "$CCODE" = "201" ]; then
      info "✓ TẠO được nhánh → token CÓ quyền ghi"
      curl -sS -m 20 -X DELETE -H "Authorization: Bearer $TOKEN" \
        "$API/repos/$REPO_SLUG/git/refs/heads/$BR" >/dev/null && info "đã xoá nhánh test"
      WRITABLE=0
    else
      info "✗ KHÔNG tạo được nhánh (HTTP $CCODE) → token chỉ đọc hoặc thiếu quyền Contents: write"
      WRITABLE=1
    fi
  fi
fi

# ── Kết luận ────────────────────────────────────────────────────────────────
say "Xong"
info "Token đã lưu ở: $ENV_FILE (mode 600, KHÔNG commit)"
info "Áp dụng cho tiến trình đang chạy cần restart: hermes gateway restart"

if [ "$WRITABLE" -ne 0 ]; then
  cat >&2 <<'EOF'

CẢNH BÁO: token hiện tại CHỈ ĐỌC. Muốn Hermes tự commit/push/sửa workflow:
  → Tạo lại token với quyền ghi. Xem docs/HERMES_GITHUB_TOKEN.md (bảng quyền).
EOF
  exit 3
fi

cat <<EOF

Kiểm tra nhanh:
    bash scripts/hermes-github-check.sh
    cd /opt/zeus && git ls-remote origin >/dev/null && echo "git OK"

Lưu ý bảo mật:
  • Không dán token vào chat, issue, PR, hay commit.
  • Không đặt token trong biến của workflow dưới dạng chữ — dùng secrets.
  • Token bị lộ = thu hồi ngay tại https://github.com/settings/tokens
EOF
