#!/usr/bin/env bash
# Hermes Web Tools Setup — Agent Reach + Browser MCP
# One-command installer + health-check for Hermes web automation.
#
# Usage:
#   bash scripts/hermes-web-tools-setup.sh --install   # cài tất cả (VPS-friendly)
#   bash scripts/hermes-web-tools-setup.sh --check     # chỉ kiểm tra (không cài)
#   bash scripts/hermes-web-tools-setup.sh --help
#
# Idempotent, safe to re-run. Không commit secret.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
CONFIG_YAML="$HERMES_HOME/config.yaml"

# Colors
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓ $*${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $*${NC}"; }
fail() { echo -e "${RED}  ✗ $*${NC}"; }
info() { echo -e "${BLUE}  → $*${NC}"; }
header() { echo -e "\n${BLUE}╔══════════════════════════════════════════════════╗${NC}\n${BLUE}║  $*${NC}\n${BLUE}╚══════════════════════════════════════════════════╝${NC}"; }

DO_CHECK_ONLY=false
DO_INSTALL=false

usage() {
  cat <<'EOF'
Usage: hermes-web-tools-setup.sh [OPTIONS]

Options:
  --install   Cài Agent Reach + Playwright MCP + cấu hình Hermes + đồng bộ skill
  --check     Chỉ kiểm tra trạng thái (không cài gì)
  --help      Hiện trợ giúp

Ví dụ:
  bash scripts/hermes-web-tools-setup.sh --check
  bash scripts/hermes-web-tools-setup.sh --install
  HERMES_HOME=/opt/hermes bash scripts/hermes-web-tools-setup.sh --install

Yêu cầu:
  - Python 3.10+, pip/pipx, Node.js 20+ (cho mcporter/playwright)
  - Trên VPS: không cần Chrome; trên Desktop: cần Chrome để dùng BrowserMCP extension

Tài liệu: docs/HERMES_WEB_AUTOMATION.md
Nghiên cứu: docs/AGENT_REACH_BROWSER_MCP_RESEARCH.md
EOF
}

# Parse args
if [[ $# -eq 0 ]]; then
  usage; exit 0
fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) DO_CHECK_ONLY=true; shift ;;
    --install) DO_INSTALL=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

# ---------- Helpers ----------
has_cmd() { command -v "$1" &>/dev/null; }

get_version() {
  local cmd="$1"
  if has_cmd "$cmd"; then
    "$cmd" --version 2>/dev/null | head -n1 || echo "ok"
  else
    echo "not installed"
  fi
}

check_agent_reach() {
  if has_cmd agent-reach; then
    local ver
    ver="$(agent-reach --version 2>/dev/null | head -n1 || agent-reach --help 2>&1 | head -n1)"
    ok "agent-reach ${ver:-ok} ($(command -v agent-reach))"
    return 0
  else
    fail "agent-reach chưa cài (cần: pipx install https://github.com/Panniantong/agent-reach/archive/main.zip)"
    return 1
  fi
}

check_gh() {
  if has_cmd gh; then
    if gh auth status &>/dev/null 2>&1; then
      ok "gh $(gh --version 2>/dev/null | head -n1) (authenticated)"
    else
      warn "gh $(gh --version 2>/dev/null | head -n1) (chưa login → gh auth login)"
    fi
  else
    warn "gh chưa cài (cần cho GitHub: https://cli.github.com/)"
  fi
}

check_ytdlp() {
  if has_cmd yt-dlp; then
    ok "yt-dlp $(yt-dlp --version 2>/dev/null | head -n1)"
  else
    warn "yt-dlp chưa cài (cần cho YouTube transcript)"
  fi
}

check_mcporter() {
  if has_cmd mcporter; then
    ok "mcporter $(mcporter --version 2>/dev/null | head -n1 || echo ok)"
  else
    warn "mcporter chưa cài (cần cho Exa web search)"
  fi
}

check_playwright_mcp() {
  if npx -y @playwright/mcp@latest --version &>/dev/null 2>&1 || npx -y @executeautomation/playwright-mcp-server --version &>/dev/null 2>&1; then
    ok "playwright-mcp (npx ok)"
  else
    warn "playwright-mcp chưa sẵn (sẽ cài khi --install)"
  fi
}

check_browser_mcp() {
  # Only relevant on desktop with Chrome
  if [[ -n "${DISPLAY:-}" ]] || [[ "$(uname)" == "Darwin" ]]; then
    if curl -sf http://127.0.0.1:12306/mcp &>/dev/null 2>&1 || curl -sf http://127.0.0.1:12306/ &>/dev/null 2>&1; then
      ok "browser-mcp (extension connected on 12306)"
    else
      warn "browser-mcp — desktop only, extension chưa Connect (bỏ qua trên VPS)"
    fi
  else
    info "browser-mcp — bỏ qua trên VPS/headless (chỉ cho desktop Chrome)"
  fi
}

doctor_summary() {
  header "KIỂM TRA HERMES WEB TOOLS"
  echo ""

  local pass=0 total=0
  # Count checks
  if check_agent_reach; then pass=$((pass+1)); fi; total=$((total+1))
  check_gh; total=$((total+1)); if has_cmd gh; then pass=$((pass+1)); fi
  check_ytdlp; total=$((total+1)); if has_cmd yt-dlp; then pass=$((pass+1)); fi
  check_mcporter; total=$((total+1)); if has_cmd mcporter; then pass=$((pass+1)); fi
  check_playwright_mcp; total=$((total+1))
  # browser-mcp is optional, not counted in total for VPS
  check_browser_mcp

  echo ""
  # Agent Reach doctor if available
  if has_cmd agent-reach; then
    echo -e "${BLUE}── Agent Reach doctor ──${NC}"
    agent-reach doctor 2>&1 || true
    echo ""
  fi

  # Hermes MCP catalog
  if has_cmd hermes; then
    echo -e "${BLUE}── Hermes MCP catalog ──${NC}"
    hermes mcp catalog 2>&1 || echo "  (hermes mcp catalog chưa sẵn)"
    echo ""
  else
    warn "hermes CLI chưa trong PATH (bỏ qua mcp catalog)"
  fi

  # Config check
  if [[ -f "$CONFIG_YAML" ]]; then
    if grep -q "mcp_servers" "$CONFIG_YAML" 2>/dev/null; then
      ok "config.yaml có mcp_servers"
      grep -A2 "mcp_servers" "$CONFIG_YAML" | head -n 20
    else
      warn "config.yaml chưa có mcp_servers (chạy --install để thêm)"
    fi
  else
    warn "chưa có $CONFIG_YAML (Hermes chưa khởi tạo)"
  fi

  echo ""
  echo -e "${GREEN}  $pass/$total kênh cốt lõi sẵn sàng${NC}"
  echo -e "  Xem chi tiết: docs/HERMES_WEB_AUTOMATION.md"
}

install_all() {
  header "CÀI ĐẶT HERMES WEB TOOLS"
  echo ""

  # 1. pipx
  if ! has_cmd pipx; then
    info "Cài pipx..."
    if has_cmd pip3; then
      pip3 install --user pipx 2>&1 | tail -n 5 || pip install pipx 2>&1 | tail -n 5
      export PATH="$HOME/.local/bin:$PATH"
    else
      fail "Không tìm thấy pip3 — cần Python 3.10+"
      exit 1
    fi
  fi
  if has_cmd pipx; then
    ok "pipx $(pipx --version 2>/dev/null | head -n1)"
    pipx ensurepath 2>&1 | tail -n 2 || true
    export PATH="$HOME/.local/bin:$PATH"
  fi

  # 2. Agent Reach
  if has_cmd agent-reach; then
    ok "agent-reach đã có — kiểm tra cập nhật"
    agent-reach check-update 2>&1 | head -n 20 || true
  else
    info "Cài agent-reach từ GitHub (main.zip)..."
    if has_cmd pipx; then
      pipx install https://github.com/Panniantong/agent-reach/archive/main.zip 2>&1 | tail -n 10 || \
        pip install https://github.com/Panniantong/agent-reach/archive/main.zip 2>&1 | tail -n 10
    elif has_cmd pip3; then
      pip3 install https://github.com/Panniantong/agent-reach/archive/main.zip 2>&1 | tail -n 10
    else
      pip install https://github.com/Panniantong/agent-reach/archive/main.zip 2>&1 | tail -n 10
    fi
    export PATH="$HOME/.local/bin:$PATH"
    if has_cmd agent-reach; then
      ok "agent-reach đã cài"
    else
      fail "Cài agent-reach thất bại — thử thủ công: pipx install https://github.com/Panniantong/agent-reach/archive/main.zip"
    fi
  fi

  # 3. Agent Reach env auto
  if has_cmd agent-reach; then
    info "Chạy agent-reach install --env=auto (cài Node/mcporter/gh/yt-dlp)..."
    agent-reach install --env=auto 2>&1 | tail -n 30 || warn "agent-reach install --env=auto báo lỗi — kiểm tra thủ công"
  fi

  # 4. Node.js check (cho playwright)
  if has_cmd node; then
    ok "node $(node --version) + npm $(npm --version 2>/dev/null | head -n1)"
  else
    warn "node chưa cài — cần Node 20+ cho playwright-mcp (cài qua nvm hoặc apt)"
  fi

  # 5. Playwright MCP — verify npx works
  if has_cmd npx; then
    info "Kiểm tra playwright-mcp (npx)..."
    # Try both package names (microsoft moved)
    if npx -y @playwright/mcp@latest --version 2>&1 | head -n 5; then
      ok "playwright-mcp (@playwright/mcp) sẵn sàng"
    elif npx -y @executeautomation/playwright-mcp-server --version 2>&1 | head -n 5; then
      ok "playwright-mcp (@executeautomation/playwright-mcp-server) sẵn sàng"
    else
      warn "playwright-mcp chưa tải được — sẽ thử lại khi Hermes kết nối MCP"
    fi
  else
    warn "npx chưa có (cài Node.js trước)"
  fi

  # 6. Configure Hermes mcp_servers.playwright
  if [[ -f "$CONFIG_YAML" ]]; then
    if grep -q "playwright" "$CONFIG_YAML" 2>/dev/null; then
      ok "config.yaml đã có playwright"
    else
      info "Thêm mcp_servers.playwright vào $CONFIG_YAML..."
      # Append or create section — keep it simple: append YAML snippet
      cat >> "$CONFIG_YAML" <<'YAML'

# --- Hermes Web Automation (added by hermes-web-tools-setup.sh) ---
# VPS: Playwright headless (không cần Chrome extension)
mcp_servers:
  playwright:
    command: "npx"
    args: ["-y", "@playwright/mcp@latest"]
YAML
      ok "Đã thêm mcp_servers.playwright (kiểm tra lại file trước khi commit)"
      warn "Nếu file đã có mcp_servers, hãy gộp thủ công — tránh duplicate key"
    fi
  else
    warn "Chưa có $CONFIG_YAML — chạy `hermes chat` một lần để khởi tạo, rồi chạy lại --install"
  fi

  # 7. Sync skills
  if [[ -f "$REPO_ROOT/scripts/hermes-sync.sh" ]]; then
    info "Đồng bộ skills vào Hermes..."
    bash "$REPO_ROOT/scripts/hermes-sync.sh" 2>&1 | tail -n 20 || warn "hermes-sync.sh báo lỗi — đồng bộ thủ công"
  elif [[ -d "$REPO_ROOT/skills/hermes-web-automation" ]]; then
    # Fallback: copy skill directly
    mkdir -p "$HERMES_HOME/skills/hermes-web-automation"
    cp -r "$REPO_ROOT/skills/hermes-web-automation/"* "$HERMES_HOME/skills/hermes-web-automation/" 2>&1 | tail -n 5 || true
    ok "Đã chép skill hermes-web-automation vào $HERMES_HOME/skills/"
  fi

  echo ""
  header "TỔNG KẾT CÀI ĐẶT"
  doctor_summary

  echo ""
  echo -e "${GREEN}Xong! Khởi động lại Hermes để nạp MCP tools:${NC}"
  echo -e "  hermes chat"
  echo -e "  # rồi thử: \"mở https://example.com và chụp màn hình\""
  echo ""
  echo -e "Cấu hình kênh cần login (tùy chọn):"
  echo -e "  gh auth login"
  echo -e "  agent-reach configure twitter-cookies \"auth_token=...; ct0=...\""
  echo -e "  agent-reach configure proxy http://user:pass@ip:port"
}

# ---------- Main ----------
if [[ "$DO_CHECK_ONLY" == true ]]; then
  doctor_summary
  exit 0
fi

if [[ "$DO_INSTALL" == true ]]; then
  install_all
  exit 0
fi

usage
