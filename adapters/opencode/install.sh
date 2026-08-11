#!/usr/bin/env bash
#
# adapters/opencode/install.sh -- OpenCode adapter for ai-team
#
# Installs the ai-team SDD framework into ~/.config/opencode/ for use with OpenCode.
#
# Usage:
#   ./adapters/opencode/install.sh
#
# Or via the top-level selector:
#   ./scripts/install.sh --adapter=opencode
#
# What it does:
#   1. Copies SDD skills to ~/.config/opencode/skills/
#   2. Rewrites skill paths in sdd-orchestrator-protocol.md (idempotency-safe)
#   3. Copies orchestrator instructions to ~/.config/opencode/AGENTS.md
#   4. Merges agent definitions into ~/.config/opencode/opencode.json (deep-merge)
#   5. Copies slash command files to ~/.config/opencode/commands/
#
# Requirements:
#   jq (for JSON merge)
#
# Re-run to update after pulling new changes from the repo.
# Existing operator agents not named sdd-* are preserved in opencode.json.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${AI_TEAM_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
OPENCODE_DIR="${HOME}/.config/opencode"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}[ai-team]${NC} $1"; }
warn() { echo -e "${YELLOW}[ai-team]${NC} $1"; }
die()  { echo -e "${RED}[ai-team]${NC} $1" >&2; exit 1; }

verify_install() {
  local missing=0
  local target_dir="$1"
  while IFS= read -r -d '' src; do
    rel="${src#$REPO_ROOT/domain/skills/}"
    dst="$target_dir/$rel"
    if [[ ! -f "$dst" ]]; then
      echo "[ai-team] missing: $src -> $dst" >&2
      missing=$((missing + 1))
    fi
  done < <(find "$REPO_ROOT/domain/skills" -type f -print0)

  if (( missing > 0 )); then
    die "verify-install: $missing file(s) failed to copy. See errors above."
  fi
  info "  -> verify-install: all $(find "$REPO_ROOT/domain/skills" -type f | wc -l) source files present"
}

# --- Preflight ---

command -v jq >/dev/null 2>&1 || die "jq required for OpenCode adapter. Install it (brew install jq / apt install jq) and retry."

# Create ~/.config/opencode/ if it doesn't exist yet — this is fine for first-time installs.
mkdir -p "$OPENCODE_DIR"

# --- 1. Skills ---

info "Installing skills..."
for dir in "$REPO_ROOT/domain/skills/"*/; do
  name=$(basename "$dir")
  dest="$OPENCODE_DIR/skills/$name"

  # Wipe destination first to avoid stale files from prior installs.
  rm -rf "$dest"
  mkdir -p "$dest"

  # Recursive copy: includes references/ subdirectories.
  if ! cp -R "$dir." "$dest/" 2>/dev/null; then
    die "skill $name: failed to copy from $dir to $dest"
  fi
done

skill_count=$(find "$OPENCODE_DIR/skills/sdd-"* -maxdepth 0 -type d 2>/dev/null | wc -l)
info "  -> ~/.config/opencode/skills/ ($skill_count phases + _shared)"

# Verify every source file landed at the corresponding destination.
verify_install "$OPENCODE_DIR/skills"

# Rewrite skill paths in the orchestrator protocol for installed location.
# Anchored patterns (command `bash skills/...` and inline-code `` `skills/sdd-... ``) are
# idempotent by construction — after one rewrite neither pattern matches again — and they
# leave `{install_dir}/skills/...` references and prose mentioning skill roots untouched.
SDD_PROTOCOL="$OPENCODE_DIR/skills/_shared/sdd-orchestrator-protocol.md"
if [[ -f "$SDD_PROTOCOL" ]]; then
  sed -i \
    -e 's|bash skills/_shared/|bash ~/.config/opencode/skills/_shared/|g' \
    -e 's|`skills/sdd-|`~/.config/opencode/skills/sdd-|g' \
    "$SDD_PROTOCOL"
  info "  -> Rewrote skill paths in sdd-orchestrator-protocol.md"
fi

# --- 2. AGENTS.md ---

info "Installing AGENTS.md..."
cp "$REPO_ROOT/adapters/opencode/templates/AGENTS.md" "$OPENCODE_DIR/AGENTS.md"
info "  -> ~/.config/opencode/AGENTS.md"

# --- 3. opencode.json (deep-merge) ---

info "Merging opencode.json..."
OVERLAY_JSON="$REPO_ROOT/adapters/opencode/templates/opencode.json"
TARGET_JSON="$OPENCODE_DIR/opencode.json"

if [[ -f "$TARGET_JSON" ]]; then
  # Deep-merge: right-side (overlay) keys override left-side (existing).
  # Existing operator agents not named sdd-* are preserved.
  # Note: permission.task is merged — stale allow entries may persist on re-installs,
  # which is safe for ai-team's own re-installs (the overlay always rewrites the full
  # permission.task allow set, so ai-team's own re-installs converge).
  # Model pins are user-owned: the template ships provider-agnostic placeholders
  # (opus/sonnet/haiku), so .model and .agent[*].model from the existing config
  # take precedence over the overlay — a re-install must never downgrade the
  # operator's provider mapping back to placeholders.
  TMP_JSON=$(mktemp)
  jq -s '
    .[0] as $existing | .[1] as $overlay |
    ($existing * $overlay)
    | .model = ($existing.model // $overlay.model)
    | (if .model == null then del(.model) else . end)
    | .agent = (.agent | with_entries(
        .value.model = ((($existing.agent // {})[.key] // {}).model // .value.model)
      ))
  ' "$TARGET_JSON" "$OVERLAY_JSON" > "$TMP_JSON"
  mv "$TMP_JSON" "$TARGET_JSON"
  info "  -> ~/.config/opencode/opencode.json (merged, user model pins preserved)"
else
  cp "$OVERLAY_JSON" "$TARGET_JSON"
  info "  -> ~/.config/opencode/opencode.json (created)"
fi

# --- 4. Slash command files ---

info "Installing slash commands..."
mkdir -p "$OPENCODE_DIR/commands"
cp "$REPO_ROOT/adapters/opencode/templates/commands/"*.md "$OPENCODE_DIR/commands/"
cmd_count=$(ls "$OPENCODE_DIR/commands/"*.md 2>/dev/null | wc -l)
info "  -> ~/.config/opencode/commands/ ($cmd_count commands)"

# --- Done ---

echo ""
info "Installation complete! (OpenCode adapter)"
echo ""
echo "  Skills:       ~/.config/opencode/skills/sdd-*/"
echo "  Protocols:    ~/.config/opencode/skills/_shared/"
echo "  Orchestrator: ~/.config/opencode/AGENTS.md"
echo "  Config:       ~/.config/opencode/opencode.json"
echo "  Commands:     ~/.config/opencode/commands/sdd-*.md"
echo ""
echo "  Select the 'sdd-orchestrator' agent in OpenCode, then:"
echo "  /sdd-new <change-name>    Start a new SDD change"
echo "  /sdd-continue [change]    Resume an active change"
echo "  /sdd-status [change]      Show change progress"
echo ""
echo "  Re-run this script to update after pulling new changes."
