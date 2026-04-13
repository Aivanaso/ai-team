#!/usr/bin/env bash
#
# install.sh -- Install ai-team framework into ~/.claude/ for Claude Code.
#
# Usage:
#   ./scripts/install.sh
#
# What it does:
#   1. Copies SDD skills to ~/.claude/skills/
#   2. Backs up ~/.claude/CLAUDE.md
#   3. Injects the orchestrator into ~/.claude/CLAUDE.md (idempotent)
#
# Re-run to update after pulling new changes from the repo.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_DIR="${HOME}/.claude"
MARKER_START="<!-- ai-team:orchestrator -->"
MARKER_END="<!-- /ai-team:orchestrator -->"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}[ai-team]${NC} $1"; }
warn() { echo -e "${YELLOW}[ai-team]${NC} $1"; }
die()  { echo -e "${RED}[ai-team]${NC} $1" >&2; exit 1; }

# --- Preflight ---

[[ -d "$CLAUDE_DIR" ]] || die "~/.claude/ not found. Is Claude Code installed?"

# --- 1. Skills ---

info "Installing skills..."
for dir in "$REPO_ROOT/skills/"*/; do
  name=$(basename "$dir")
  mkdir -p "$CLAUDE_DIR/skills/$name"
  cp "$dir"*.md "$CLAUDE_DIR/skills/$name/"
done

skill_count=$(find "$CLAUDE_DIR/skills/sdd-"* -maxdepth 0 -type d 2>/dev/null | wc -l)
info "  -> ~/.claude/skills/ ($skill_count phases + _shared)"

# --- 2. Backup CLAUDE.md ---

if [[ -f "$CLAUDE_DIR/CLAUDE.md" ]]; then
  backup="${CLAUDE_DIR}/CLAUDE.md.bak.$(date +%Y%m%d%H%M%S)"
  cp "$CLAUDE_DIR/CLAUDE.md" "$backup"
  info "Backed up CLAUDE.md -> $(basename "$backup")"
fi

# --- 3. Inject orchestrator ---

# Remove existing section if present (idempotent update)
if [[ -f "$CLAUDE_DIR/CLAUDE.md" ]] && grep -qF "$MARKER_START" "$CLAUDE_DIR/CLAUDE.md"; then
  awk -v start="$MARKER_START" -v end="$MARKER_END" '
    index($0, start) { skip=1; next }
    index($0, end)   { skip=0; next }
    !skip
  ' "$CLAUDE_DIR/CLAUDE.md" > "$CLAUDE_DIR/CLAUDE.md.tmp"
  mv "$CLAUDE_DIR/CLAUDE.md.tmp" "$CLAUDE_DIR/CLAUDE.md"
  warn "Removed previous orchestrator section"
fi

# Append orchestrator with resolved skill paths
# skills/_shared/ -> ~/.claude/skills/_shared/
# skills/sdd-     -> ~/.claude/skills/sdd-
{
  echo ""
  echo "$MARKER_START"
  sed \
    -e 's|skills/_shared/|~/.claude/skills/_shared/|g' \
    -e 's|skills/sdd-|~/.claude/skills/sdd-|g' \
    "$REPO_ROOT/adapters/claude/CLAUDE.md"
  echo "$MARKER_END"
} >> "$CLAUDE_DIR/CLAUDE.md"

info "Orchestrator injected into CLAUDE.md"

# --- Done ---

echo ""
info "Installation complete!"
echo ""
echo "  Skills:       ~/.claude/skills/sdd-*/"
echo "  Protocols:    ~/.claude/skills/_shared/"
echo "  Orchestrator: ~/.claude/CLAUDE.md (between ai-team markers)"
echo ""
echo "  Re-run this script to update after pulling new changes."
