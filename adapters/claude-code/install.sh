#!/usr/bin/env bash
#
# adapters/claude-code/install.sh -- Claude Code adapter for ai-team
#
# Installs the ai-team SDD framework into ~/.claude/ for use with Claude Code.
#
# Usage:
#   ./adapters/claude-code/install.sh
#
# Or via the top-level selector:
#   ./scripts/install.sh --adapter=claude-code
#
# What it does:
#   1. Copies SDD skills to ~/.claude/skills/
#   2. Rewrites skill paths in sdd-orchestrator-protocol.md (idempotency-safe)
#   3. Injects orchestrator content inline into ~/.claude/CLAUDE.md
#      between <!-- ai-team:orchestrator --> markers
#
# Re-run to update after pulling new changes from the repo.
# User content outside the markers is never touched.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${AI_TEAM_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
CLAUDE_DIR="${HOME}/.claude"

MARKER_OPEN="<!-- ai-team:orchestrator -->"
MARKER_CLOSE="<!-- /ai-team:orchestrator -->"

# Legacy @reference to clean up
LEGACY_REFERENCE="@ai-team-orchestrator.md"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}[ai-team]${NC} $1"; }
warn() { echo -e "${YELLOW}[ai-team]${NC} $1"; }
die()  { echo -e "${RED}[ai-team]${NC} $1" >&2; exit 1; }

# --- Preflight ---

# Create ~/.claude/ if missing — supports fresh-install scenarios (Claude Code
# installed but never run) and smoke tests against temp HOME directories.
mkdir -p "$CLAUDE_DIR"

# --- 1. Skills ---

info "Installing skills..."
for dir in "$REPO_ROOT/domain/skills/"*/; do
  name=$(basename "$dir")
  mkdir -p "$CLAUDE_DIR/skills/$name"
  cp "$dir"*.md "$CLAUDE_DIR/skills/$name/"
done

skill_count=$(find "$CLAUDE_DIR/skills/sdd-"* -maxdepth 0 -type d 2>/dev/null | wc -l)
info "  -> ~/.claude/skills/ ($skill_count phases + _shared)"

# Rewrite skill paths in the orchestrator protocol for installed location.
# Guard: skip if already-rewritten absolute prefix is present (idempotency fix).
# Evidence: adapted from scripts/install.sh lines 54-61 (original unconditional sed).
SDD_PROTOCOL="$CLAUDE_DIR/skills/_shared/sdd-orchestrator-protocol.md"
if [[ -f "$SDD_PROTOCOL" ]] && ! grep -q '~/.claude/skills/' "$SDD_PROTOCOL"; then
  sed -i \
    -e 's|skills/_shared/|~/.claude/skills/_shared/|g' \
    -e 's|skills/sdd-|~/.claude/skills/sdd-|g' \
    "$SDD_PROTOCOL"
  info "  -> Rewrote skill paths in sdd-orchestrator-protocol.md"
else
  info "  -> Skill paths already rewritten (idempotent re-run)"
fi

# --- 2. Prepare orchestrator content ---

info "Preparing orchestrator content..."

ORCHESTRATOR_CONTENT=$(cat "$REPO_ROOT/adapters/claude-code/templates/CLAUDE.md")

# --- 3. Resolve CLAUDE.md (handle symlinks) ---

CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"

# If CLAUDE.md is a symlink, resolve to the real file so we write to the
# actual target (not replace the symlink with a regular file).
WRITE_TARGET="$CLAUDE_MD"
if [[ -L "$CLAUDE_MD" ]]; then
  WRITE_TARGET="$(readlink -f "$CLAUDE_MD")"
  warn "CLAUDE.md is a symlink -> ${WRITE_TARGET}"
fi

# Create CLAUDE.md if it doesn't exist
if [[ ! -f "$WRITE_TARGET" ]]; then
  touch "$WRITE_TARGET"
  info "Created ${WRITE_TARGET}"
fi

EXISTING=$(cat "$WRITE_TARGET")

# --- 4. Clean up legacy @reference (if present) ---

if grep -qF "$LEGACY_REFERENCE" <<< "$EXISTING"; then
  warn "Removing legacy ${LEGACY_REFERENCE}..."
  EXISTING=$(grep -vF "$LEGACY_REFERENCE" <<< "$EXISTING")
fi

# Also remove the old standalone orchestrator file if it exists
if [[ -f "$CLAUDE_DIR/ai-team-orchestrator.md" ]]; then
  rm "$CLAUDE_DIR/ai-team-orchestrator.md"
  warn "Removed legacy ~/.claude/ai-team-orchestrator.md"
fi

# --- 5. Inject between markers ---

# Build the new section
SECTION="${MARKER_OPEN}
${ORCHESTRATOR_CONTENT}
${MARKER_CLOSE}"

if grep -qF "$MARKER_OPEN" <<< "$EXISTING"; then
  # Markers exist — replace content between them
  info "Updating existing orchestrator section..."

  # Use awk to replace everything between markers (inclusive)
  UPDATED=$(awk -v m_open="$MARKER_OPEN" -v m_close="$MARKER_CLOSE" -v section="$SECTION" '
    BEGIN { printing=1 }
    index($0, m_open) { printing=0; print section; next }
    index($0, m_close) { printing=1; next }
    printing
  ' <<< "$EXISTING")
else
  # No markers — append section at the end
  info "Injecting orchestrator section..."

  if [[ -n "$EXISTING" ]]; then
    UPDATED="${EXISTING}

${SECTION}"
  else
    UPDATED="$SECTION"
  fi
fi

# --- 6. Write back ---

# Write atomically: temp file + move
TMPFILE=$(mktemp "${WRITE_TARGET}.XXXXXX")
echo "$UPDATED" > "$TMPFILE"
mv "$TMPFILE" "$WRITE_TARGET"

info "  -> ${WRITE_TARGET}"

# --- Done ---

echo ""
info "Installation complete! (Claude Code adapter)"
echo ""
echo "  Skills:       ~/.claude/skills/sdd-*/"
echo "  Protocols:    ~/.claude/skills/_shared/"
echo "  Orchestrator: inline in CLAUDE.md (between markers)"
echo ""
echo "  Slash commands: /ai-team new <change>, /ai-team continue, etc."
echo "  Re-run this script to update after pulling new changes."
