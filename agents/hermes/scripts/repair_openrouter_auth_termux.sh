#!/usr/bin/env bash
set -Eeuo pipefail

# Repair OpenRouter authentication for Hermes on Termux/PRoot without ever
# printing or committing the API key. The script normalizes the local
# ~/.hermes/.env entry, validates the key directly against OpenRouter, then
# configures/tests Hermes with openrouter/free.

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ENV_FILE="${HERMES_HOME}/.env"
MODEL="${HERMES_OPENROUTER_MODEL:-openrouter/free}"
OPENROUTER_BASE_URL="${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"
TMP_DIR="${TMPDIR:-/tmp}"
CHECK_BODY="${TMP_DIR}/hermes-openrouter-key-check.$$"
USAGE_FILE="${TMP_DIR}/hermes-openrouter-usage.$$.json"
BACKUP_FILE="${ENV_FILE}.bak.$(date +%Y%m%d-%H%M%S)"

cleanup() {
  rm -f "$CHECK_BODY"
}
trap cleanup EXIT

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ -f "$ENV_FILE" ]] || die "Không tìm thấy $ENV_FILE. Hãy chạy 'hermes model' và nhập OpenRouter API key trước."
command -v python3 >/dev/null 2>&1 || die "Thiếu python3."
command -v curl >/dev/null 2>&1 || die "Thiếu curl."

# Fail closed: this repair utility intentionally supports only the official
# OpenRouter hostname. Paths under that host are allowed; lookalike/custom
# hosts are rejected before the credential is loaded into a curl header.
python3 - "$OPENROUTER_BASE_URL" <<'PY'
from urllib.parse import urlparse
import sys
url = sys.argv[1].strip()
p = urlparse(url)
host = (p.hostname or "").lower().rstrip(".")
if p.scheme != "https" or host != "openrouter.ai":
    raise SystemExit("ERROR: OPENROUTER_BASE_URL phải dùng host chính thức openrouter.ai qua HTTPS")
PY

cp -p "$ENV_FILE" "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE" 2>/dev/null || true
log "[1/6] Đã backup .env (không đưa secret lên GitHub)."

# Normalize only OPENROUTER_API_KEY. Never print the value.
python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import os
import re
import sys

path = Path(sys.argv[1])
raw = path.read_bytes()
text = raw.decode("utf-8-sig", errors="replace").replace("\x00", "")
lines = text.splitlines()

values = []
kept = []
assignment = re.compile(r"^\s*OPENROUTER_API_KEY\s*=\s*(.*)$")
for line in lines:
    match = assignment.match(line)
    if match:
        value = match.group(1).strip().strip("\r")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        for ch in ("\ufeff", "\u200b", "\u200c", "\u200d", "\u2060", "\u00a0"):
            value = value.replace(ch, "")
        value = value.strip()
        if value:
            values.append(value)
    else:
        kept.append(line)

if not values:
    raise SystemExit("ERROR: OPENROUTER_API_KEY đang trống hoặc không đọc được trong .env")

key = values[-1]
try:
    key.encode("ascii")
except UnicodeEncodeError:
    raise SystemExit("ERROR: API key chứa ký tự non-ASCII. Hãy copy lại key trực tiếp từ OpenRouter.")

if not key.startswith("sk-or-v1-"):
    raise SystemExit("ERROR: OPENROUTER_API_KEY không có prefix sk-or-v1-. Hãy nhập lại key bằng 'hermes model'.")

out = "\n".join(kept).rstrip("\n")
if out:
    out += "\n"
out += f"OPENROUTER_API_KEY={key}\n"
path.write_text(out, encoding="utf-8", newline="\n")
os.chmod(path, 0o600)
print(f"KEY_PRESENT=true KEY_LENGTH={len(key)} PREFIX_VALID=true DUPLICATES_REMOVED={max(0, len(values)-1)}")
PY

# Read the normalized value without sourcing the whole .env as shell code.
OPENROUTER_API_KEY="$(python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import sys
for line in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines():
    if line.startswith('OPENROUTER_API_KEY='):
        print(line.split('=', 1)[1], end='')
        break
PY
)"

[[ -n "$OPENROUTER_API_KEY" ]] || die "Không nạp được OPENROUTER_API_KEY sau khi normalize."
export OPENROUTER_API_KEY
log "[2/6] Đã nạp key an toàn vào process (không in key)."

python3 - <<'PY'
import os
k = os.environ.get("OPENROUTER_API_KEY", "")
if not k:
    raise SystemExit("ERROR: process không có OPENROUTER_API_KEY")
print(f"AUTH_HEADER_READY=true BEARER_VALUE_LENGTH={len(k)}")
PY
log "[3/6] Authorization header đã sẵn sàng ở local process."

HTTP_CODE="$(curl -sS -o "$CHECK_BODY" -w '%{http_code}' \
  -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
  "${OPENROUTER_BASE_URL%/}/key" || true)"

if [[ "$HTTP_CODE" != "200" ]]; then
  ERROR_SUMMARY="$(python3 - "$CHECK_BODY" <<'PY'
import json
import re
import sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text(encoding='utf-8', errors='replace'))
    err = data.get('error', {})
    msg = err.get('message') if isinstance(err, dict) else str(err)
    code = err.get('code') if isinstance(err, dict) else None
    msg = str(msg or "")
    msg = re.sub(r"sk-or-v1-[A-Za-z0-9_-]+", "[REDACTED]", msg)
    print(f"code={code} message={msg}")
except Exception:
    print("response body không đọc được")
PY
)"
  die "DIRECT_OPENROUTER_AUTH_FAILED HTTP=${HTTP_CODE}; ${ERROR_SUMMARY}. Hermes core chưa được kết luận có lỗi. Hãy tạo/copy lại OpenRouter key rồi chạy script lại."
fi
log "[4/6] DIRECT_OPENROUTER_AUTH_SUCCESS HTTP=200. Key hợp lệ."

if ! command -v hermes >/dev/null 2>&1; then
  for activate in /root/hermes-env/bin/activate "$HOME/hermes-env/bin/activate"; do
    if [[ -f "$activate" ]]; then
      # shellcheck disable=SC1090
      source "$activate"
      break
    fi
  done
fi
command -v hermes >/dev/null 2>&1 || die "Không tìm thấy lệnh hermes / hermes-env."

hermes config set model.provider openrouter >/dev/null
hermes config set model.default "$MODEL" >/dev/null
log "[5/6] Hermes model: provider=openrouter, default=${MODEL}."

set +e
OPENROUTER_API_KEY="$OPENROUTER_API_KEY" hermes -z \
  "Chỉ trả lời đúng câu này: OpenRouter Free hoạt động." \
  --provider openrouter \
  --model "$MODEL" \
  --usage-file "$USAGE_FILE"
HERMES_RC=$?
set -e

if [[ $HERMES_RC -ne 0 ]]; then
  die "DIRECT_OPENROUTER_AUTH_SUCCESS nhưng HERMES_SMOKE_TEST_FAILED exit=${HERMES_RC}. Đây mới là điều kiện để trace/patch runtime_provider; giữ usage tại ${USAGE_FILE}."
fi

log "[6/6] THÀNH CÔNG: OpenRouter auth + Hermes ${MODEL} đều hoạt động."
if [[ -f "$USAGE_FILE" ]]; then
  python3 - "$USAGE_FILE" <<'PY'
import json
import sys
from pathlib import Path
try:
    d = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
except Exception:
    raise SystemExit(0)
for k in ('provider', 'model', 'estimated_cost_usd', 'input_tokens', 'output_tokens', 'failed'):
    if k in d:
        print(f"{k}={d[k]}")
PY
fi

log "Backup local: ${BACKUP_FILE}"
