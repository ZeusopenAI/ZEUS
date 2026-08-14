#!/usr/bin/env bash
set -euo pipefail

# Clean reinstall of upstream Hermes Agent for the Quang Quý AI Codespace.
# Secrets are read from the process environment and are never printed or persisted.

HERMES_VERSION="0.18.2"
HERMES_ROOT="${HOME}/.hermes"
GEMINI_MODEL="gemini-3.6-flash"
GEMINI_ENDPOINT="https://generativelanguage.googleapis.com/v1beta"

printf '%s\n' "== Hermes clean Gemini rebuild =="

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "ERROR: GEMINI_API_KEY is missing from the current environment." >&2
  exit 1
fi

echo "[1/7] Removing old Hermes package from the active Python environment..."
python -m pip uninstall -y hermes-agent 2>/dev/null || true

echo "[2/7] Preserving old Hermes user state outside the active path..."
if [[ -d "$HERMES_ROOT" ]]; then
  backup="${HERMES_ROOT}.legacy.$(date +%Y%m%d-%H%M%S)"
  mv "$HERMES_ROOT" "$backup"
  echo "Legacy Hermes state preserved at: $backup"
fi

echo "[3/7] Installing upstream Hermes Agent ${HERMES_VERSION}..."
python -m pip install --upgrade "hermes-agent==${HERMES_VERSION}"
command -v hermes >/dev/null 2>&1 || { echo "ERROR: hermes executable not found" >&2; exit 1; }

mkdir -p "$HERMES_ROOT"

# Native Gemini configuration. No API key is written to disk and no OpenRouter
# endpoint or credential is copied. Hermes reads GEMINI_API_KEY from the process.
cat > "${HERMES_ROOT}/config.yaml" <<EOF
model:
  provider: gemini
  default: ${GEMINI_MODEL}
  base_url: ${GEMINI_ENDPOINT}
EOF

# Keep any secret-bearing user env out of the new clean runtime path.
rm -f "${HERMES_ROOT}/.env"

echo "[4/7] Verifying direct Gemini API access without exposing the key..."
status="$(curl -sS -o /tmp/hermes-gemini-smoke.json -w '%{http_code}' \
  -H "x-goog-api-key: ${GEMINI_API_KEY}" \
  -H 'Content-Type: application/json' \
  -X POST \
  "${GEMINI_ENDPOINT}/models/${GEMINI_MODEL}:generateContent" \
  -d '{"contents":[{"parts":[{"text":"Reply with exactly GEMINI_API_OK"}]}]}' || true)"

if [[ "$status" != "200" ]]; then
  echo "ERROR: direct Gemini API smoke test failed (HTTP ${status:-unknown})." >&2
  rm -f /tmp/hermes-gemini-smoke.json
  exit 1
fi
rm -f /tmp/hermes-gemini-smoke.json

echo "Direct Gemini API: OK"

echo "[5/7] Verifying Hermes CLI and provider configuration..."
version="$(hermes --version 2>/dev/null || true)"
echo "Hermes: ${version:-version check unavailable}"
hermes config check

printf 'GEMINI_API_KEY: '
if [[ -n "${GEMINI_API_KEY:-}" ]]; then echo "OK"; else echo "MISSING"; fi
printf 'Provider: gemini\nModel: %s\n' "$GEMINI_MODEL"

echo "[6/7] Running one-shot Hermes → Gemini smoke test..."
set +e
hermes_output="$(hermes chat -q 'Reply with exactly GEMINI_HERMES_OK' --provider gemini --model "$GEMINI_MODEL" --ignore-rules 2>&1)"
hermes_rc=$?
set -e

if [[ $hermes_rc -ne 0 ]] || ! grep -q 'GEMINI_HERMES_OK' <<<"$hermes_output"; then
  echo "ERROR: Hermes → Gemini smoke test failed." >&2
  echo "Exit code: $hermes_rc" >&2
  exit 1
fi

echo "Hermes → Gemini: OK"

echo "[7/7] Clean rebuild completed successfully."
echo "Hermes Agent ${HERMES_VERSION} is configured for native Gemini (${GEMINI_MODEL})."
echo "No API key value was printed or persisted."
