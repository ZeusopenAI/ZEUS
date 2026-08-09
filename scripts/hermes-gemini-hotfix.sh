#!/usr/bin/env bash
set -euo pipefail

# Q AI / Hermes Gemini native-auth hotfix
# Safe goals:
# 1) back up the installed adapter and ~/.hermes/.env
# 2) normalize duplicate Gemini key entries without printing the secret
# 3) harden native Gemini headers so default headers cannot override x-goog-api-key
#    and no stray Bearer/API-key auth headers are sent alongside it
# 4) verify the exact runtime resolver key fingerprint matches the configured key
# 5) call Gemini through Hermes' own GeminiNativeClient before restarting tmux

if [ ! -d /root/hermes-env ]; then
  if command -v proot-distro >/dev/null 2>&1; then
    echo "[Q AI] Entering Ubuntu PRoot..."
    exec proot-distro login ubuntu -- /bin/bash -lc \
      "curl -fsSL https://raw.githubusercontent.com/qquy28888-ops/quangquy-ai/fix/hermes-gemini-auth/scripts/hermes-gemini-hotfix.sh | bash"
  fi
  echo "ERROR: /root/hermes-env not found and proot-distro is unavailable." >&2
  exit 1
fi

VENV=/root/hermes-env
HERMES_HOME=/root/.hermes
ENV_FILE="$HERMES_HOME/.env"
CFG_FILE="$HERMES_HOME/config.yaml"
STAMP="$(date +%Y%m%d_%H%M%S)"

source "$VENV/bin/activate"
mkdir -p "$HERMES_HOME/backup"

PYTHON="$(command -v python3)"
SITE="$($PYTHON - <<'PY'
import site
paths = site.getsitepackages()
print(paths[0])
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

echo "[Q AI] Backup complete."

# Normalize duplicate GOOGLE_API_KEY/GEMINI_API_KEY entries. The last configured
# value wins, matching shell-source behavior. The actual key is never printed.
$PYTHON - <<'PY'
from pathlib import Path

p = Path('/root/.hermes/.env')
p.parent.mkdir(parents=True, exist_ok=True)
text = p.read_text(errors='ignore') if p.exists() else ''
lines = text.splitlines()

secret = ''
kept = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith('GOOGLE_API_KEY=') or stripped.startswith('GEMINI_API_KEY='):
        value = line.split('=', 1)[1].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if value:
            secret = value
        continue
    kept.append(line)

if not secret:
    raise SystemExit('ERROR: No GOOGLE_API_KEY/GEMINI_API_KEY found in /root/.hermes/.env')

kept.append(f'GEMINI_API_KEY={secret}')
p.write_text('\n'.join(kept).rstrip() + '\n')
print('[Q AI] Gemini key entries normalized: one canonical GEMINI_API_KEY (value hidden).')
PY
chmod 600 "$ENV_FILE"

# Harden the native Gemini transport. Native Gemini should authenticate only
# with x-goog-api-key. default_headers are still honored for harmless headers,
# but cannot inject/override auth credentials.
$PYTHON - "$ADAPTER" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()
original = s

s = s.replace('self.api_key = api_key\n', 'self.api_key = (api_key or "").strip()\n', 1)

needle = '''        headers.update(self._default_headers)\n        return headers\n'''
replacement = '''        headers.update(self._default_headers)\n\n        # Q AI hotfix: native Gemini must receive exactly one authentication\n        # mechanism. Remove any auth headers inherited from generic/OpenAI\n        # client defaults, then set the canonical Gemini key last so a stale\n        # default header cannot override it.\n        _auth_header_names = {\n            "authorization", "api-key", "x-api-key", "apikey",\n            "x-auth-token", "x-access-token", "x-goog-api-key",\n        }\n        for _name in list(headers):\n            if _name.lower() in _auth_header_names:\n                headers.pop(_name, None)\n        headers["x-goog-api-key"] = self.api_key\n        return headers\n'''

if needle not in s:
    if 'Q AI hotfix: native Gemini must receive exactly one authentication' in s:
        print('[Q AI] Adapter already patched.')
        raise SystemExit(0)
    raise SystemExit('ERROR: Expected Gemini _headers() block was not found; refusing unsafe patch.')

s = s.replace(needle, replacement, 1)
p.write_text(s)
print('[Q AI] Gemini native header path patched.')
PY

$PYTHON -m py_compile "$ADAPTER"
echo "[Q AI] Python syntax check: OK"

# Load ~/.hermes/.env into this process without echoing values.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Verify the exact key that runtime resolution returns. Fingerprints are SHA-256
# prefixes only; no secret is printed.
$PYTHON - <<'PY'
import hashlib
import os
from hermes_cli.runtime_provider import resolve_runtime_provider

model = 'gemini-3.6-flash'
r = resolve_runtime_provider(requested='gemini', target_model=model)
runtime_key = str(r.get('api_key') or '')
env_key = str(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or '')

def fp(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12] if value else 'NONE'

print('[Q AI] Runtime provider :', r.get('provider'))
print('[Q AI] Runtime api_mode :', r.get('api_mode'))
print('[Q AI] Runtime base_url :', r.get('base_url'))
print('[Q AI] Runtime key fp   :', fp(runtime_key))
print('[Q AI] Env key fp       :', fp(env_key))
print('[Q AI] Key match        :', runtime_key == env_key)

if not runtime_key:
    raise SystemExit('ERROR: Hermes runtime resolver returned an empty Gemini key.')
if runtime_key != env_key:
    raise SystemExit('ERROR: Hermes runtime resolver is using a different key than ~/.hermes/.env; not starting Hermes.')
PY

# Test the same code path Hermes should use: runtime resolver -> GeminiNativeClient
# -> native :generateContent. This is stronger than a raw curl test.
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
    text = ''
    try:
        text = response.choices[0].message.content or ''
    except Exception:
        text = str(response)
    print('[Q AI] GeminiNativeClient test:', text[:200])
finally:
    client.close()
PY

# Remove any old tmux process so the next q launch loads the patched module/key.
tmux kill-session -t hermes 2>/dev/null || true
pkill -f '/root/hermes-env/bin/hermes.*--cli' 2>/dev/null || true

echo
echo "[Q AI] HOTFIX COMPLETE"
echo "Now return to Termux and run: q"
echo "Then test: Xin chào, hãy trả lời bằng tiếng Việt có dấu."
