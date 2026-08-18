#!/usr/bin/env bash
#
# scripts/install.sh -- ai-team adapter selector
#
# Installs the ai-team organic evidence-tiered delegation framework by
# routing to the chosen adapter installer.
#
# Usage:
#   ./scripts/install.sh --adapter=claude-code
#   ./scripts/install.sh --adapter=opencode
#   ./scripts/install.sh --adapter=both        # installs both adapters
#   ./scripts/install.sh claude-code           # positional argument
#   ./scripts/install.sh                       # interactive prompt (TTY only)
#
# Supported adapters:
#   claude-code   Claude Code adapter
#   opencode      OpenCode adapter
#   both          Both adapters
#
# Each adapter installer lives at adapters/<name>/install.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}[ai-team]${NC} $1"; }
warn() { echo -e "${YELLOW}[ai-team]${NC} $1"; }
die()  { echo -e "${RED}[ai-team]${NC} $1" >&2; exit 1; }

SUPPORTED_ADAPTERS="claude-code opencode"

# Validate adapter name. Returns 0 if valid, 1 if not.
is_valid_adapter() {
  local name="$1"
  for a in $SUPPORTED_ADAPTERS; do
    [[ "$a" == "$name" ]] && return 0
  done
  return 1
}

# Expand "both" to the full adapter list.
expand_adapters() {
  local raw="$1"
  if [[ "$raw" == "both" ]]; then
    echo "$SUPPORTED_ADAPTERS"
  else
    echo "$raw"
  fi
}

# --- Argument parsing (resolution order: flag > positional > TTY prompt > error) ---

ADAPTER_RAW=""

# 1. Parse --adapter=<value> long flag
for arg in "$@"; do
  case "$arg" in
    --adapter=*)
      ADAPTER_RAW="${arg#--adapter=}"
      break
      ;;
  esac
done

# 2. Positional argument fallback
if [[ -z "$ADAPTER_RAW" ]] && [[ $# -gt 0 ]]; then
  case "$1" in
    --*)
      # Unknown flag — skip (will fall through to TTY or error)
      ;;
    *)
      ADAPTER_RAW="$1"
      ;;
  esac
fi

# 3. Interactive TTY prompt (re-prompt up to 3 times)
if [[ -z "$ADAPTER_RAW" ]]; then
  if [[ -t 0 ]]; then
    echo ""
    echo "Supported adapters: claude-code, opencode, both"
    for attempt in 1 2 3; do
      read -r -p "Select adapter: " ADAPTER_RAW
      [[ -n "$ADAPTER_RAW" ]] && break
      warn "No input provided (attempt $attempt/3)"
    done
    if [[ -z "$ADAPTER_RAW" ]]; then
      echo "error: no valid adapter selected after 3 attempts" >&2
      exit 4
    fi
  else
    # 4. No-TTY, no-flag, no-positional
    echo "error: no adapter selected; pass --adapter=<name>" >&2
    exit 1
  fi
fi

# --- Expand and validate ---

ADAPTERS=$(expand_adapters "$ADAPTER_RAW")

for adapter in $ADAPTERS; do
  if ! is_valid_adapter "$adapter"; then
    echo "error: unknown adapter '${adapter}'; supported: claude-code, opencode" >&2
    exit 2
  fi
done

# --- Dispatch ---

export AI_TEAM_ROOT="$REPO_ROOT"

for adapter in $ADAPTERS; do
  ADAPTER_INSTALLER="$REPO_ROOT/adapters/${adapter}/install.sh"

  if [[ ! -f "$ADAPTER_INSTALLER" ]]; then
    echo "error: adapter '${adapter}' has no install.sh at adapters/${adapter}/install.sh" >&2
    exit 3
  fi

  info "Running adapter: ${adapter}"
  rc=0
  "$ADAPTER_INSTALLER" || rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "error: adapter '${adapter}' installer failed (see output above)" >&2
    exit "$rc"
  fi
done
