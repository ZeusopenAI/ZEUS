#!/usr/bin/env bash
set -euo pipefail

SOURCE_REPO="https://github.com/qquy28888-ops/hermes-agent.git"
SOURCE_BRANCH="main"
TARGET_DIR="agents/hermes"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

git clone --depth 1 --branch "$SOURCE_BRANCH" "$SOURCE_REPO" "$TEMP_DIR/hermes"
SOURCE_SHA="$(git -C "$TEMP_DIR/hermes" rev-parse HEAD)"
rm -rf "$TEMP_DIR/hermes/.git"
mkdir -p "$TARGET_DIR"
rsync -a --delete --exclude '.env' "$TEMP_DIR/hermes/" "$TARGET_DIR/"
printf '%s\n' "$SOURCE_SHA" > "$TARGET_DIR/.quang-quy-source-commit"

echo "Hermes snapshot updated to $SOURCE_SHA"
echo "Review git diff, run tests, then commit on a non-main branch."
