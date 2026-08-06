#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
echo "update-hermes-snapshot.sh is deprecated; using the history-preserving subtree updater." >&2
exec "$SCRIPT_DIR/update-hermes-subtree.sh" "$@"
