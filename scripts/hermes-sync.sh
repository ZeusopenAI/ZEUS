#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Zeus → Hermes: đồng bộ skill + ngữ cảnh mới nhất từ repo vào runtime Hermes
#
# Việc script làm:
#   1. Copy mọi skill trong skills/*/  →  $HERMES_HOME/skills/<tên>/
#      (chỉ ghi khi khác nội dung; bản cũ được backup trước khi ghi đè)
#   2. Sinh skill `zeus-context` từ trạng thái repo hiện tại
#      (git HEAD, Status.md, TODO.md, Roadmap.md, AGENTS.md, bản đồ repo, docs/skills)
#      — phần nội dung do scripts/gen-zeus-context.py đảm nhận
#   3. Tuỳ chọn: thêm 1 dòng trỏ tới skill đó trong $HERMES_HOME/MEMORY.md
#
# Cách dùng:
#   bash scripts/hermes-sync.sh                 # skill + context
#   bash scripts/hermes-sync.sh --dry-run       # chỉ in việc sẽ làm
#   bash scripts/hermes-sync.sh --skills-only
#   bash scripts/hermes-sync.sh --context-only
#   bash scripts/hermes-sync.sh --with-memory   # ghi thêm dòng vào MEMORY.md
#   bash scripts/hermes-sync.sh --prune         # xoá skill repo đã bị gỡ (có backup)
#
# Mã thoát:
#   0  = không có gì thay đổi
#   10 = ĐÃ thay đổi (caller nên restart gateway để nạp lại skill)
#   1+ = lỗi
# ============================================================================

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SKILLS_SRC="$REPO_DIR/skills"
SKILLS_DEST="$HERMES_HOME/skills"
BACKUP_DIR="$HERMES_HOME/skill-backups"
STAMP="$(date +%Y%m%d-%H%M%S)"
CONTEXT_SKILL="zeus-context"
CONTEXT_MAX_CHARS="${CONTEXT_MAX_CHARS:-14000}"

DRY_RUN=0
DO_SKILLS=1
DO_CONTEXT=1
WITH_MEMORY=0
PRUNE=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)      DRY_RUN=1 ;;
    --skills-only)  DO_CONTEXT=0 ;;
    --context-only) DO_SKILLS=0 ;;
    --with-memory)  WITH_MEMORY=1 ;;
    --prune)        PRUNE=1 ;;
    -h|--help)      sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "Tham số không hỗ trợ: $arg" >&2; exit 2 ;;
  esac
done

say()  { printf '\n== %s ==\n' "$*"; }
info() { printf '   %s\n' "$*"; }
run()  { if [ "$DRY_RUN" = "1" ]; then echo "[dry-run] $*"; else "$@"; fi; }

CHANGED=0
mark_changed() { CHANGED=1; info "ĐỔI: $*"; }

if [ ! -d "$SKILLS_SRC" ]; then
  echo "LỖI: không thấy $SKILLS_SRC" >&2
  exit 1
fi

run mkdir -p "$SKILLS_DEST"
run mkdir -p "$BACKUP_DIR"

backup_skill() {
  local name="$1"
  [ -d "$SKILLS_DEST/$name" ] || return 0
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] backup $SKILLS_DEST/$name → $BACKUP_DIR/$STAMP/$name"
    return 0
  fi
  mkdir -p "$BACKUP_DIR/$STAMP"
  cp -a "$SKILLS_DEST/$name" "$BACKUP_DIR/$STAMP/$name"
}

# ---------------------------------------------------------------------------
# 1. Skill từ repo
# ---------------------------------------------------------------------------
sync_skills() {
  say "Skill: $SKILLS_SRC → $SKILLS_DEST"
  local src_dir name
  for src_dir in "$SKILLS_SRC"/*/; do
    [ -d "$src_dir" ] || continue
    [ -f "$src_dir/SKILL.md" ] || continue
    name="$(basename "$src_dir")"

    if [ -d "$SKILLS_DEST/$name" ] && diff -rq "$src_dir" "$SKILLS_DEST/$name" >/dev/null 2>&1; then
      info "không đổi: $name"
      continue
    fi

    mark_changed "$name"
    backup_skill "$name"
    run rm -rf "$SKILLS_DEST/$name"
    run cp -a "$src_dir" "$SKILLS_DEST/$name"
    info "đã cập nhật: $name"
  done

  if [ "$PRUNE" = "1" ]; then
    for dest_dir in "$SKILLS_DEST"/*/; do
      [ -d "$dest_dir" ] || continue
      name="$(basename "$dest_dir")"
      case "$name" in "$CONTEXT_SKILL") continue ;; esac
      if [ ! -d "$SKILLS_SRC/$name" ]; then
        mark_changed "prune $name (không còn trong repo)"
        backup_skill "$name"
        run rm -rf "$SKILLS_DEST/$name"
      fi
    done
  fi
}

# ---------------------------------------------------------------------------
# 2. Sinh skill zeus-context
# ---------------------------------------------------------------------------
repo_meta() {
  local git_sha git_branch git_date
  git_sha="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  git_branch="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  git_date="$(git -C "$REPO_DIR" log -1 --format=%cs 2>/dev/null || echo unknown)"
  printf '%s|%s|%s' "$git_sha" "$git_branch" "$git_date"
}

build_context_skill() {
  local target_dir="$SKILLS_DEST/$CONTEXT_SKILL"
  local tmp meta git_sha
  meta="$(repo_meta)"
  git_sha="${meta%%|*}"

  tmp="$(mktemp)"
  if ! python3 "$REPO_DIR/scripts/gen-zeus-context.py" \
        --repo "$REPO_DIR" --out "$tmp" --max-chars "$CONTEXT_MAX_CHARS"; then
    echo "CẢNH BÁO: không sinh được $CONTEXT_SKILL — giữ bản cũ." >&2
    rm -f "$tmp"
    return 0
  fi

  if [ -f "$target_dir/SKILL.md" ] && diff -q "$tmp" "$target_dir/SKILL.md" >/dev/null 2>&1; then
    info "không đổi: $CONTEXT_SKILL"
    rm -f "$tmp"
    return 0
  fi

  mark_changed "$CONTEXT_SKILL ($git_sha, $(wc -c < "$tmp" | tr -d ' ') bytes)"
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] ghi $target_dir/SKILL.md"
  else
    mkdir -p "$target_dir"
    cp "$tmp" "$target_dir/SKILL.md"
  fi
  rm -f "$tmp"
}

# ---------------------------------------------------------------------------
# 3. Trỏ Hermes tới snapshot trong MEMORY.md (tuỳ chọn)
# ---------------------------------------------------------------------------
UPDATE_MEMORY_MARK="ZEUS context snapshot (auto)"
update_memory() {
  local mem="$HERMES_HOME/MEMORY.md"
  local meta entry
  meta="$(repo_meta)"
  entry="§ ${UPDATE_MEMORY_MARK}: repo ZeusopenAI/ZEUS @ ${meta%%|*} — xem skill \`zeus-context\` để biết trạng thái mới nhất trước khi lập kế hoạch."

  say "MEMORY.md: $mem"
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] ghi/ghi đè dòng: $entry"
    return 0
  fi

  touch "$mem"
  if grep -qF "$UPDATE_MEMORY_MARK" "$mem"; then
    if grep -qF "$entry" "$mem"; then
      info "không đổi"
      return 0
    fi
    grep -vF "$UPDATE_MEMORY_MARK" "$mem" > "$mem.tmp" || true
    printf '%s\n' "$entry" >> "$mem.tmp"
    mv "$mem.tmp" "$mem"
  else
    printf '%s\n' "$entry" >> "$mem"
  fi
  chmod 600 "$mem" 2>/dev/null || true
  mark_changed "MEMORY.md"
}

# ---------------------------------------------------------------------------

[ "$DO_SKILLS" = "1" ] && sync_skills
[ "$DO_CONTEXT" = "1" ] && build_context_skill
[ "$WITH_MEMORY" = "1" ] && update_memory

say "Kết quả"
if [ "$CHANGED" = "1" ]; then
  if [ "$DRY_RUN" = "1" ]; then
    echo "Có thay đổi (dry-run, chưa ghi gì)."
    exit 0
  fi
  echo "Đã cập nhật Hermes. Restart gateway để nạp skill mới:"
  echo "    hermes gateway restart"
  exit 10
fi
echo "Không có thay đổi — Hermes đã ở bản mới nhất."
exit 0
