#!/usr/bin/env bash
set -euo pipefail

# Q AI / Hermes Gemini auth-key recovery
# Purpose:
# - run safely from `curl | bash` in Termux or directly inside Ubuntu PRoot
# - ask for a fresh Gemini API key through /dev/tty (never echo the value)
# - verify the key with a REAL Gemini generateContent request before saving it
# - persist only a verified key to ~/.hermes/.env
# - then run the full Hermes Gemini hotfix/live-test script

SELF_URL="https://raw.githubusercontent.com/qquy28888-ops/quangquy-ai/fix/hermes-gemini-auth/scripts/hermes-gemini-auth-recover.sh"
HOTFIX_URL="https://raw.githubusercontent.com/qquy28888-ops/quangquy-ai/fix/hermes-gemini-auth/scripts/hermes-gemini-hotfix.sh"
MODEL="${QAI_GEMINI_TEST_MODEL:-gemini-3.6-flash}"

if [ ! -d /root/hermes-env ]; then
  if command -v proot-distro >/dev/null 2>&1; then
    echo "[Q AI] Entering Ubuntu PRoot..."
    exec proot-distro login ubuntu -- /bin/bash -lc \
      "curl -fsSL '$SELF_URL' | bash"
  fi
  echo "ERROR: /root/hermes-env not found and proot-distro is unavailable." >&2
  exit 1
fi

if [ ! -r /dev/tty ]; then
  echo "ERROR: No interactive terminal is available. Run this script directly from Termux." >&2
  exit 1
fi

VENV=/root/hermes-env
HERMES_HOME=/root/.hermes
ENV_FILE="$HERMES_HOME/.env"
STAMP="$(date +%Y%m%d_%H%M%S)"

source "$VENV/bin/activate"
PYTHON="$(command -v python3)"
mkdir -p "$HERMES_HOME/backup"

probe_key() {
  local key="$1"
  QAI_PROBE_KEY="$key" QAI_GEMINI_TEST_MODEL="$MODEL" "$PYTHON" - <<'PY'
from __future__ import annotations
import json
import os
import sys
import urllib.error
import urllib.request

key = os.environ.get('QAI_PROBE_KEY', '')
model = os.environ.get('QAI_GEMINI_TEST_MODEL', 'gemini-3.6-flash')
url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
payload = json.dumps({
    'contents': [{'parts': [{'text': 'Reply with exactly OK'}]}],
    'generationConfig': {'maxOutputTokens': 16},
}).encode()
req = urllib.request.Request(
    url,
    data=payload,
    headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    text = (((data.get('candidates') or [{}])[0].get('content') or {}).get('parts') or [{}])[0].get('text', '')
    print('HTTP=200')
    print('REASON=OK')
    print('TEXT=' + str(text).strip()[:100])
    raise SystemExit(0)
except urllib.error.HTTPError as exc:
    body = exc.read().decode(errors='replace')
    reason = ''
    message = ''
    try:
        payload = json.loads(body)
        err = payload.get('error') or {}
        message = str(err.get('message') or '')
        for detail in err.get('details') or []:
            if isinstance(detail, dict) and detail.get('reason'):
                reason = str(detail.get('reason'))
                break
    except Exception:
        message = body[:300]
    print(f'HTTP={exc.code}')
    print('REASON=' + (reason or 'NO_REASON'))
    print('MESSAGE=' + message[:300].replace('\n', ' '))
    raise SystemExit(10)
except Exception as exc:
    print('HTTP=0')
    print('REASON=' + exc.__class__.__name__)
    print('MESSAGE=' + str(exc)[:300].replace('\n', ' '))
    raise SystemExit(11)
PY
}

save_verified_key() {
  local key="$1"
  [ -f "$ENV_FILE" ] && cp "$ENV_FILE" "$HERMES_HOME/backup/env.auth-recover.$STAMP.bak" || true
  QAI_VERIFIED_KEY="$key" "$PYTHON" - <<'PY'
from pathlib import Path
import os

p = Path('/root/.hermes/.env')
p.parent.mkdir(parents=True, exist_ok=True)
secret = os.environ['QAI_VERIFIED_KEY']
current = p.read_text(errors='ignore') if p.exists() else ''
kept = []
for raw in current.splitlines():
    line = raw.strip()
    normalized = line[7:].lstrip() if line.startswith('export ') else line
    if normalized.startswith('GOOGLE_API_KEY=') or normalized.startswith('GEMINI_API_KEY='):
        continue
    kept.append(raw)
kept.append(f'GOOGLE_API_KEY={secret}')
p.write_text('\n'.join(kept).rstrip() + '\n')
print('[Q AI] Verified key saved as the only Gemini credential in ~/.hermes/.env (value hidden).')
PY
  chmod 600 "$ENV_FILE"
}

cat <<'TXT'
[Q AI] No locally stored Gemini key is currently accepted by Google.
[Q AI] Google now distinguishes Standard keys from Authorization/Auth keys.
[Q AI] In Google AI Studio -> API Keys, create/copy a key whose Key Type is Auth/Authorization.
[Q AI] Do NOT paste the key into chat or GitHub. Paste it only into the hidden prompt below.
TXT

attempt=1
while [ "$attempt" -le 3 ]; do
  printf '[Q AI] Paste fresh Gemini Auth API key (attempt %s/3, Enter to cancel): ' "$attempt" >/dev/tty
  IFS= read -r -s NEWKEY </dev/tty || true
  printf '\n' >/dev/tty
  NEWKEY="${NEWKEY//$'\r'/}"

  if [ -z "$NEWKEY" ]; then
    echo "[Q AI] Cancelled. No credential changed."
    exit 2
  fi

  echo "[Q AI] Testing the supplied key directly against Gemini generateContent..."
  set +e
  PROBE_OUTPUT="$(probe_key "$NEWKEY" 2>&1)"
  PROBE_RC=$?
  set -e

  # Print only status/reason/message emitted by the probe; the key is never printed.
  printf '%s\n' "$PROBE_OUTPUT"

  if [ "$PROBE_RC" -eq 0 ]; then
    save_verified_key "$NEWKEY"
    unset NEWKEY
    echo "[Q AI] Key accepted by Google. Running full Hermes hotfix + native-client live test..."
    QAI_GEMINI_TEST_MODEL="$MODEL" bash -c "curl -fsSL '$HOTFIX_URL' | bash"
    exit $?
  fi

  if printf '%s\n' "$PROBE_OUTPUT" | grep -q 'REASON=ACCESS_TOKEN_TYPE_UNSUPPORTED'; then
    echo "[Q AI] This credential type is rejected by Gemini (ACCESS_TOKEN_TYPE_UNSUPPORTED)."
    echo "[Q AI] In AI Studio, check the Key Type column and use an Auth/Authorization key, not an old Standard/unrestricted key or OAuth token."
  else
    echo "[Q AI] Google did not accept this key. It was NOT saved."
  fi

  unset NEWKEY
  attempt=$((attempt + 1))
done

echo "ERROR: Three supplied keys failed a real Gemini request. No new key was saved." >&2
exit 3
