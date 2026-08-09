#!/usr/bin/env bash
set -euo pipefail

# Q AI / Hermes Gemini native-auth hotfix
# Goals:
# - never expose API keys
# - eliminate inherited/stale GOOGLE_API_KEY/GEMINI_API_KEY ambiguity
# - canonicalize ~/.hermes/.env to exactly one GOOGLE_API_KEY entry
# - harden Gemini native headers so generic Bearer/default auth cannot override x-goog-api-key
# - verify raw Gemini REST and Hermes GeminiNativeClient with the SAME exact key
# - patch the q startup wrapper to clear inherited Gemini env vars before Hermes loads ~/.hermes/.env

BRANCH_URL="https://raw.githubusercontent.com/qquy28888-ops/quangquy-ai/fix/hermes-gemini-auth/scripts/hermes-gemini-hotfix.sh"

if [ ! -d /root/hermes-env ]; then
  if command -v proot-distro >/dev/null 2>&1; then
    echo "[Q AI] Entering Ubuntu PRoot..."
    exec proot-distro login ubuntu -- /bin/bash -lc \
      "curl -fsSL '$BRANCH_URL' | bash"
  fi
  echo "ERROR: /root/hermes-env not found and proot-distro is unavailable." >&2
  exit 1
fi

VENV=/root/hermes-env
HERMES_HOME=/root/.hermes
ENV_FILE="$HERMES_HOME/.env"
CFG_FILE="$HERMES_HOME/config.yaml"
START_FILE=/root/hermes-start.sh
STAMP="$(date +%Y%m%d_%H%M%S)"

source "$VENV/bin/activate"
mkdir -p "$HERMES_HOME/backup"

PYTHON="$(command -v python3)"
SITE="$($PYTHON - <<'PY'
import site
print(site.getsitepackages()[0])
PY
)"
ADAPTER="$SITE/agent/gemini_native_adapter.py"

if [ ! -f "$ADAPTER" ]; then
  echo "ERROR: Gemini adapter not found: $ADAPTER" >&2
  exit 1
fi

cp "$ADAPTER" "$HERMES_HOME/backup/gemini_native_adapter.py.$STAMP.bak"
[ -f "$ENV_FILE" ] && cp "$ENV_FILE" "$HERMES_HOME/backup/env.$STAMP.bak" || true
[ -f "$CFG_FILE" ] && cp "$CFG_FILE" "$HERMES_HOME/backup/config.$STAMP.bak" || true
[ -f "$START_FILE" ] && cp "$START_FILE" "$HERMES_HOME/backup/hermes-start.sh.$STAMP.bak" || true

echo "[Q AI] Backup complete."

# IMPORTANT: throw away inherited values before reading ~/.hermes/.env. This is
# the most subtle failure mode: provider resolution prioritizes GOOGLE_API_KEY,
# so an old exported GOOGLE_API_KEY can silently beat a newer GEMINI_API_KEY.
unset GOOGLE_API_KEY GEMINI_API_KEY || true

# Canonicalize the file using ONLY values physically stored in ~/.hermes/.env.
# If both aliases exist, the final non-empty occurrence wins. Write one
# GOOGLE_API_KEY because Hermes' Gemini provider registry checks it first.
$PYTHON - <<'PY'
from pathlib import Path

p = Path('/root/.hermes/.env')
p.parent.mkdir(parents=True, exist_ok=True)
text = p.read_text(errors='ignore') if p.exists() else ''
secret = ''
kept = []
for raw in text.splitlines():
    line = raw.strip()
    normalized = line[7:].lstrip() if line.startswith('export ') else line
    if normalized.startswith('GOOGLE_API_KEY=') or normalized.startswith('GEMINI_API_KEY='):
        value = normalized.split('=', 1)[1].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if value:
            secret = value
        continue
    kept.append(raw)

if not secret:
    raise SystemExit('ERROR: No Gemini API key found in /root/.hermes/.env')

kept.append(f'GOOGLE_API_KEY={secret}')
p.write_text('\n'.join(kept).rstrip() + '\n')
print('[Q AI] Canonicalized Gemini credentials to one GOOGLE_API_KEY (value hidden).')
PY
chmod 600 "$ENV_FILE"

# Patch the native adapter. Hermes should send exactly one auth mechanism to
# generativelanguage.googleapis.com: x-goog-api-key. Preserve harmless default
# headers, but scrub generic auth headers after merging defaults and set the
# canonical Gemini header last.
$PYTHON - "$ADAPTER" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

if 'Q AI hotfix: native Gemini must receive exactly one authentication' not in s:
    s = s.replace('self.api_key = api_key\n', 'self.api_key = (api_key or "").strip()\n', 1)
    needle = '''        headers.update(self._default_headers)\n        return headers\n'''
    replacement = '''        headers.update(self._default_headers)\n\n        # Q AI hotfix: native Gemini must receive exactly one authentication\n        # mechanism. Generic/OpenAI defaults can contain Authorization or a\n        # stale API-key header; remove them, then set Google's key last.\n        _auth_header_names = {\n            "authorization", "api-key", "x-api-key", "apikey",\n            "x-auth-token", "x-access-token", "x-goog-api-key",\n        }\n        for _name in list(headers):\n            if _name.lower() in _auth_header_names:\n                headers.pop(_name, None)\n        headers["x-goog-api-key"] = self.api_key\n        return headers\n'''
    if needle not in s:
        raise SystemExit('ERROR: Expected Gemini _headers() block was not found; refusing unsafe patch.')
    s = s.replace(needle, replacement, 1)
    p.write_text(s)
    print('[Q AI] Gemini native header path patched.')
else:
    print('[Q AI] Gemini native header path already patched.')
PY

$PYTHON -m py_compile "$ADAPTER"
echo "[Q AI] Gemini adapter syntax: OK"

# Patch the launcher so every future `q` session starts without stale inherited
# Gemini env vars. Hermes itself will then load the canonical key from
# ~/.hermes/.env. This edit is idempotent.
if [ -f "$START_FILE" ]; then
  $PYTHON - "$START_FILE" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()
marker = '# Q AI: clear inherited Gemini aliases before Hermes loads ~/.hermes/.env'
if marker not in s:
    lines = s.splitlines()
    insert_at = 1 if lines and lines[0].startswith('#!') else 0
    lines[insert_at:insert_at] = [
        marker,
        'unset GOOGLE_API_KEY GEMINI_API_KEY 2>/dev/null || true',
    ]
    p.write_text('\n'.join(lines) + '\n')
    print('[Q AI] hermes-start.sh patched against inherited stale Gemini keys.')
else:
    print('[Q AI] hermes-start.sh already contains env-isolation patch.')
PY
  bash -n "$START_FILE"
  echo "[Q AI] hermes-start.sh syntax: OK"
fi

# Now load ONLY the canonical on-disk key for tests.
unset GOOGLE_API_KEY GEMINI_API_KEY || true
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Force one-key invariant in this test process too.
unset GEMINI_API_KEY || true

$PYTHON - <<'PY'
import hashlib
import os
from hermes_cli.runtime_provider import resolve_runtime_provider

model = 'gemini-3.6-flash'
r = resolve_runtime_provider(requested='gemini', target_model=model)
runtime_key = str(r.get('api_key') or '')
env_key = str(os.getenv('GOOGLE_API_KEY') or '')

def fp(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12] if value else 'NONE'

print('[Q AI] Runtime provider :', r.get('provider'))
print('[Q AI] Runtime api_mode :', r.get('api_mode'))
print('[Q AI] Runtime base_url :', r.get('base_url'))
print('[Q AI] Runtime key fp   :', fp(runtime_key))
print('[Q AI] Env key fp       :', fp(env_key))
print('[Q AI] Key match        :', runtime_key == env_key)

if r.get('provider') != 'gemini':
    raise SystemExit('ERROR: runtime resolver did not select gemini.')
if not runtime_key:
    raise SystemExit('ERROR: runtime resolver returned an empty Gemini key.')
if runtime_key != env_key:
    raise SystemExit('ERROR: runtime resolver key differs from canonical ~/.hermes/.env key.')
PY

# Live test 1: raw REST using the exact canonical GOOGLE_API_KEY.
# Do not print response headers or credentials.
RAW_RESULT="$($PYTHON - <<'PY'
import json, os, urllib.request, urllib.error
key = os.environ['GOOGLE_API_KEY']
url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent'
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
except urllib.error.HTTPError as exc:
    body = exc.read().decode(errors='replace')[:1000]
    raise SystemExit(f'RAW_GEMINI_HTTP_{exc.code}: {body}')
text = (((data.get('candidates') or [{}])[0].get('content') or {}).get('parts') or [{}])[0].get('text', '')
print(text.strip())
PY
)"
echo "[Q AI] Raw Gemini REST test: ${RAW_RESULT:0:200}"

# Live test 2: the same key through Hermes' own native client.
$PYTHON - <<'PY'
from hermes_cli.runtime_provider import resolve_runtime_provider
from agent.gemini_native_adapter import GeminiNativeClient

model = 'gemini-3.6-flash'
r = resolve_runtime_provider(requested='gemini', target_model=model)
client = GeminiNativeClient(api_key=r['api_key'], base_url=r['base_url'])
try:
    response = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': 'Reply with exactly OK'}],
        max_tokens=16,
    )
    text = response.choices[0].message.content or ''
    print('[Q AI] GeminiNativeClient test:', text.strip()[:200])
finally:
    client.close()
PY

# Kill old processes only after both live tests succeed.
tmux kill-session -t hermes 2>/dev/null || true
pkill -f '/root/hermes-env/bin/hermes.*--cli' 2>/dev/null || true

echo
echo "[Q AI] HOTFIX + LIVE TESTS COMPLETE"
echo "Return to Termux and run: q"
echo "Then test: Xin chào, hãy trả lời bằng tiếng Việt có dấu."
