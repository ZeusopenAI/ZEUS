#!/usr/bin/env bash
set -euo pipefail

# Clean reinstall of upstream Hermes Agent for the Quang Quý AI Codespace.
# Secrets are read from the process environment and are never printed.

HERMES_VERSION="0.18.2"
HERMES_ROOT="${HOME}/.hermes"

printf '%s\n' "== Hermes clean Gemini rebuild =="

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "ERROR: GEMINI_API_KEY is missing from the current environment." >&2
  exit 1
fi

python -m pip uninstall -y hermes-agent 2>/dev/null || true

if [[ -d "$HERMES_ROOT" ]]; then
  backup="${HERMES_ROOT}.legacy.$(date +%Y%m%d-%H%M%S)"
  mv "$HERMES_ROOT" "$backup"
  echo "Legacy Hermes state preserved at: $backup"
fi

python -m pip install --upgrade "hermes-agent==${HERMES_VERSION}"

command -v hermes >/dev/null 2>&1 || { echo "ERROR: hermes executable not found" >&2; exit 1; }

hermes config set model.provider gemini
hermes config set model.default gemini-3.6-flash

mkdir -p "$HERMES_ROOT"
if [[ -f "${HERMES_ROOT}/.env" ]]; then
  sed -i '/^OPENROUTER_API_KEY=/d; /^OPENROUTER_BASE_URL=/d; /^GEMINI_BASE_URL=/d; /^GOOGLE_API_KEY=/d; /^GEMINI_API_KEY=/d' "${HERMES_ROOT}/.env"
fi

umask 077
printf 'GEMINI_API_KEY=%s\n' "$GEMINI_API_KEY" >> "${HERMES_ROOT}/.env"
chmod 600 "${HERMES_ROOT}/.env"

printf 'GEMINI_API_KEY: '
if [[ -n "${GEMINI_API_KEY:-}" ]]; then echo "OK"; else echo "MISSING"; fi
printf 'Hermes executable: '; command -v hermes
printf 'Provider: gemini\nModel: gemini-3.6-flash\n'

echo "Clean install complete. Run: hermes chat --model gemini-3.6-flash"
echo "The API key value is never printed."
