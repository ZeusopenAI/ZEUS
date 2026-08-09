#!/usr/bin/env bash
set -euo pipefail

# Q AI / Hermes Gemini native-auth hotfix
# Goals:
# - never expose API keys
# - recover a WORKING Gemini API key from ~/.hermes/.env and local backups
# - reject keys that Google answers with ACCESS_TOKEN_TYPE_UNSUPPORTED
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
TEST_MODEL="${QAI_GEMINI_TEST_MODEL:-gemini-3.6-flash}"

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

# Throw away inherited values before looking at the on-disk Hermes secrets.
# Provider resolution prioritizes GOOGLE_API_KEY, so an old exported value can
# silently beat a newer GEMINI_API_KEY.
unset GOOGLE_API_KEY GEMINI_API_KEY || true

# Recover a *working* key instead of blindly trusting the last line in .env.
# We test every unique Gemini key found in the current env and local backups,
# newest files first. This is specifically meant to recover from the situation
# where a previously working key was overwritten by a Google key that now
# returns ACCESS_TOKEN_TYPE_UNSUPPORTED. Values are never printed; only a short
# SHA-256 fingerprint, source filename, status, and Google reason are shown.
QAI_GEMINI_TEST_MODEL="$TEST_MODEL" $PYTHON - <<'PY'
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import urllib.error
import urllib.request

HOME = Path('/root/.hermes')
ENV = HOME / '.env'
MODEL = os.environ.get('QAI_GEMINI_TEST_MODEL', 'gemini-3.6-flash').strip() or 'gemini-3.6-flash'
URL = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'


def fp(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def candidate_files() -> list[Path]:
    paths: list[Path] = []
    if ENV.exists():
        paths.append(ENV)

    extras: list[Path] = []
    extras.extend(HOME.glob('.env.bak*'))
    backup = HOME / 'backup'
    if backup.exists():
        extras.extend(p for p in backup.glob('env*') if p.is_file())

    # newest backup first; current .env remains first overall
    extras = sorted(set(extras), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    for p in extras:
        if p not in paths:
            paths.append(p)
    return paths


def extract(path: Path) -> list[str]:
    out: list[str] = []
    try:
        text = path.read_text(errors='ignore')
    except Exception:
        return out
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith('export '):
            line = line[7:].lstrip()
        if not (line.startswith('GOOGLE_API_KEY=') or line.startswith('GEMINI_API_KEY=')):
            continue
        value = line.split('=', 1)[1].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if value:
            out.append(value)
    return out


def probe(key: str) -> tuple[int, str, str]:
    payload = json.dumps({
        'contents': [{'parts': [{'text': 'Reply with exactly OK'}]}],
        'generationConfig': {'maxOutputTokens': 16},
    }).encode()
    req = urllib.request.Request(
        URL,
        data=payload,
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        text = (((data.get('candidates') or [{}])[0].get('content') or {}).get('parts') or [{}])[0].get('text', '')
        return 200, '', str(text).strip()
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
        return int(exc.code), reason, message[:300]
    except Exception as exc:
        return 0, exc.__class__.__name__, str(exc)[:300]

files = candidate_files()
seen: set[str] = set()
candidates: list[tuple[str, Path]] = []
for path in files:
    for key in extract(path):
        if key not in seen:
            seen.add(key)
            candidates.append((key, path))

if not candidates:
    raise SystemExit('ERROR: No Gemini API key found in ~/.hermes/.env or local Hermes backups.')

print(f'[Q AI] Found {len(candidates)} unique Gemini key candidate(s); testing live without exposing values...')
selected: tuple[str, Path] | None = None
results: list[tuple[str, int, str, str]] = []

for index, (key, source) in enumerate(candidates, 1):
    status, reason, message = probe(key)
    results.append((fp(key), status, reason, source.name))
    reason_text = reason or ('OK' if status == 200 else 'NO_REASON')
    print(f'[Q AI] Candidate {index}: fp={fp(key)} source={source.name} HTTP={status} reason={reason_text}')
    if status == 200:
        selected = (key, source)
        break

if selected is None:
    unsupported = [r for r in results if r[2] == 'ACCESS_TOKEN_TYPE_UNSUPPORTED']
    if unsupported:
        print('[Q AI] Diagnosis: Google rejected one or more stored keys with ACCESS_TOKEN_TYPE_UNSUPPORTED.')
        print('[Q AI] No locally stored Gemini key passed a real generateContent request.')
        print('[Q AI] The Hermes transport is not the blocker at this point; a compatible Gemini API key is required.')
    raise SystemExit('ERROR: No working Gemini API key found in current .env or Hermes backups.')

secret, source = selected
print(f'[Q AI] Selected working key fp={fp(secret)} recovered from {source.name}.')

# Preserve every non-Gemini line from the current env, then write one canonical
# GOOGLE_API_KEY. Do not touch unrelated provider credentials.
current = ENV.read_text(errors='ignore') if ENV.exists() else ''
kept: list[str] = []
for raw in current.splitlines():
    line = raw.strip()
    normalized = line[7:].lstrip() if line.startswith('export ') else line
    if normalized.startswith('GOOGLE_API_KEY=') or normalized.startswith('GEMINI_API_KEY='):
        continue
    kept.append(raw)
kept.append(f'GOOGLE_API_KEY={secret}')
ENV.parent.mkdir(parents=True, exist_ok=True)
ENV.write_text('\n'.join(kept).rstrip() + '\n')
print('[Q AI] Canonicalized ~/.hermes/.env to one live-tested GOOGLE_API_KEY (value hidden).')
PY
chmod 600 "$ENV_FILE"

# Patch the native adapter. Hermes should send exactly one auth mechanism to
# generativelanguage.googleapis.com: x-goog-api-key. Preserve harmless default
# headers, scrub generic auth after merging defaults, and set Google's key last.
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

# Patch launcher: each future `q` starts without stale inherited Gemini aliases.
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
    lines[insert_at:insert_at] = [marker, 'unset GOOGLE_API_KEY GEMINI_API_KEY 2>/dev/null || true']
    p.write_text('\n'.join(lines) + '\n')
    print('[Q AI] hermes-start.sh patched against inherited stale Gemini keys.')
else:
    print('[Q AI] hermes-start.sh already contains env-isolation patch.')
PY
  bash -n "$START_FILE"
  echo "[Q AI] hermes-start.sh syntax: OK"
fi

# Load only the canonical live-tested key.
unset GOOGLE_API_KEY GEMINI_API_KEY || true
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
unset GEMINI_API_KEY || true

$PYTHON - <<'PY'
import hashlib
import os
from hermes_cli.runtime_provider import resolve_runtime_provider

model = os.environ.get('QAI_GEMINI_TEST_MODEL', 'gemini-3.6-flash')
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

# Live test 1: raw REST again using the exact canonical key.
RAW_RESULT="$(QAI_GEMINI_TEST_MODEL="$TEST_MODEL" $PYTHON - <<'PY'
import json, os, urllib.request, urllib.error
model = os.environ.get('QAI_GEMINI_TEST_MODEL', 'gemini-3.6-flash')
key = os.environ['GOOGLE_API_KEY']
url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
payload = json.dumps({'contents': [{'parts': [{'text': 'Reply with exactly OK'}]}], 'generationConfig': {'maxOutputTokens': 16}}).encode()
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json', 'x-goog-api-key': key}, method='POST')
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

# Live test 2: same key through Hermes' native client.
QAI_GEMINI_TEST_MODEL="$TEST_MODEL" $PYTHON - <<'PY'
import os
from hermes_cli.runtime_provider import resolve_runtime_provider
from agent.gemini_native_adapter import GeminiNativeClient

model = os.environ.get('QAI_GEMINI_TEST_MODEL', 'gemini-3.6-flash')
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

# Kill old process only after both live tests succeed.
tmux kill-session -t hermes 2>/dev/null || true
pkill -f '/root/hermes-env/bin/hermes.*--cli' 2>/dev/null || true

echo
echo "[Q AI] HOTFIX + LIVE TESTS COMPLETE"
echo "Return to Termux and run: q"
echo "Then test: Xin chào, hãy trả lời bằng tiếng Việt có dấu."
