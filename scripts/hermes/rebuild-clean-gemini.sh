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

echo "[1/6] Removing old Hermes installation from the active Python environment..."
python -m pip uninstall -y hermes-agent 2>/dev/null || true

echo "[2/6] Moving old Hermes user state out of the active path..."
if [[ -d "$HERMES_ROOT" ]]; then
  backup="${HERMES_ROOT}.legacy.$(date +%Y%m%d-%H%M%S)"
  mv "$HERMES_ROOT" "$backup"
  echo "Legacy Hermes state preserved at: $backup"
fi

echo "[3/6] Installing upstream Hermes Agent ${HERMES_VERSION}..."
python -m pip install --upgrade "hermes-agent==${HERMES_VERSION}"

if ! command -v hermes >/dev/null 2>&1; then
  echo "ERROR: hermes executable was not installed or is not on PATH." >&2
  exit 1
fi

installed_version="$(hermes --version 2>/dev/null || true)"
echo "Installed: ${installed_version:-version check unavailable}"

echo "[4/6] Configuring native Google Gemini provider..."
hermes config set model.provider gemini
hermes config set model.default gemini-3.6-flash

if [[ -f "${HERMES_ROOT}/.env" ]]; then
  sed -i '/^OPENROUTER_API_KEY=/d; /^OPENROUTER_BASE_URL=/d; /^GEMINI_BASE_URL=/d; /^GOOGLE_API_KEY=/d; /^GEMINI_API_KEY=/d' "${HERMES_ROOT}/.env"
fi

umask 077
printf 'GEMINI_API_KEY=%s\n' "$GEMINI_API_KEY" >> "${HERMES_ROOT}/.env"

mkdir -p "$HERMES_ROOT"
python - <<'PY'
from pathlib import Path

p = Path.home() / ".hermes" / "config.yaml"
p.parent.mkdir(parents=True, exist_ok=True)
text = p.read_text() if p.exists() else ""
lines = text.splitlines()
out = []
in_model = False
model_written = False
for line in lines:
    if line and not line.startswith(" ") and line.startswith("model:"):
        in_model = True
        out.append("model:")
        out.append("  provider: gemini")
        out.append("  default: gemini-3.6-flash")
        model_written = True
        continue
    if in_model and line and not line.startswith(" "):
        in_model = False
    if not in_model:
        out.append(line)

if not model_written:
    if out and out[-1] != "":
        out.append("")
    out.extend(["model:", "  provider: gemini", "  default: gemini-3.6-flash"])

p.write_text("\n".join(out).rstrip() + "\n")
PY

awk '!seen[$0]++ || $0 !~ /^GEMINI_API_KEY=/' "${HERMES_ROOT}/.env" > "${HERMES_ROOT}/.env.tmp"
mv "${HERMES_ROOT}/.env.tmp" "${HERMES_ROOT}/.env"
chmod 600 "${HERMES_ROOT}/.env"

echo "[5/6] Verifying configuration without exposing secrets..."
hermes config check || true
printf 'GEMINI_API_KEY: '
if [[ -n "${GEMINI_API_KEY:-}" ]]; then echo "OK"; else echo "MISSING"; fi
printf 'Hermes executable: '; command -v hermes
printf 'Provider: gemini\nModel: gemini-3.6-flash\n'

echo "[6/6] Ready for live Gemini smoke test."
echo "Run: hermes chat --model gemini-3.6-flash"
echo "No API key is printed by this script."
