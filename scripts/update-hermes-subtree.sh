#!/usr/bin/env bash
set -euo pipefail

SOURCE_REPO="${HERMES_SOURCE_REPO:-https://github.com/qquy28888-ops/hermes-agent.git}"
SOURCE_REF="${1:-${HERMES_SOURCE_REF:-main}}"
TARGET_DIR="agents/hermes"
MARKER="$TARGET_DIR/.quang-quy-source-commit"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree must be clean before updating the Hermes subtree." >&2
  exit 1
fi

BRANCH="$(git branch --show-current)"
if [ -z "$BRANCH" ] || [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "Run this script on a dedicated integration branch, not $BRANCH." >&2
  exit 1
fi

if [ ! -d "$TARGET_DIR" ] || [ ! -f "$MARKER" ]; then
  echo "Hermes subtree or source marker is missing." >&2
  exit 1
fi

git fetch --no-tags "$SOURCE_REPO" "$SOURCE_REF"
SOURCE_SHA="$(git rev-parse FETCH_HEAD)"
CURRENT_SHA="$(tr -d '\r\n' < "$MARKER")"

if [ "$SOURCE_SHA" = "$CURRENT_SHA" ] && git merge-base --is-ancestor "$SOURCE_SHA" HEAD; then
  echo "Hermes subtree is already at $SOURCE_SHA"
  exit 0
fi

git subtree pull \
  --prefix="$TARGET_DIR" \
  "$SOURCE_REPO" "$SOURCE_REF" \
  -m "chore(hermes): update subtree to ${SOURCE_SHA:0:12}"

printf '%s\n' "$SOURCE_SHA" > "$MARKER"
git add "$MARKER"
if ! git diff --cached --quiet; then
  git commit -m "chore(hermes): record source revision ${SOURCE_SHA:0:12}"
fi

echo "Hermes subtree updated to $SOURCE_SHA"
echo "Review the commits, run validation, then open a pull request."
