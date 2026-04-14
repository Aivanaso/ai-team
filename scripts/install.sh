#!/usr/bin/env bash
#
# install.sh -- Install ai-team framework into ~/.claude/ for Claude Code.
#
# Usage:
#   ./scripts/install.sh
#
# What it does:
#   1. Copies SDD skills to ~/.claude/skills/
#   2. Writes the orchestrator to ~/.claude/ai-team-orchestrator.md
#   3. Adds an @reference in ~/.claude/CLAUDE.md (symlink-safe)
#
# Re-run to update after pulling new changes from the repo.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_DIR="${HOME}/.claude"
ORCHESTRATOR_FILE="ai-team-orchestrator.md"
AT_REFERENCE="@${ORCHESTRATOR_FILE}"

# Legacy markers (migration from old injection approach)
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

# --- 2. Write orchestrator file ---

info "Writing ${ORCHESTRATOR_FILE}..."
sed \
  -e 's|skills/_shared/|~/.claude/skills/_shared/|g' \
  -e 's|skills/sdd-|~/.claude/skills/sdd-|g' \
  "$REPO_ROOT/adapters/claude/CLAUDE.md" > "$CLAUDE_DIR/$ORCHESTRATOR_FILE"

info "  -> ~/.claude/${ORCHESTRATOR_FILE}"

# --- 3. Migrate legacy marker injection (if present) ---

CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"

if [[ -f "$CLAUDE_MD" ]] && grep -qF "$MARKER_START" "$CLAUDE_MD"; then
  warn "Found legacy orchestrator markers — removing inline block..."

  # Resolve symlink target so we write to the actual file, not replace the link
  WRITE_TARGET="$CLAUDE_MD"
  if [[ -L "$CLAUDE_MD" ]]; then
    WRITE_TARGET="$(readlink -f "$CLAUDE_MD")"
    warn "  CLAUDE.md is a symlink -> ${WRITE_TARGET}"
  fi

  awk -v start="$MARKER_START" -v end="$MARKER_END" '
    index($0, start) { skip=1; next }
    index($0, end)   { skip=0; next }
    !skip
  ' "$CLAUDE_MD" > "$CLAUDE_DIR/CLAUDE.md.tmp"
  cp "$CLAUDE_DIR/CLAUDE.md.tmp" "$WRITE_TARGET"
  rm "$CLAUDE_DIR/CLAUDE.md.tmp"

  info "  Legacy markers removed"
fi

# --- 4. Ensure @reference in CLAUDE.md ---

if [[ ! -f "$CLAUDE_MD" ]]; then
  echo "$AT_REFERENCE" > "$CLAUDE_MD"
  info "Created CLAUDE.md with ${AT_REFERENCE}"
elif ! grep -qF "$AT_REFERENCE" "$CLAUDE_MD"; then
  if [[ -L "$CLAUDE_MD" ]]; then
    target="$(readlink -f "$CLAUDE_MD")"
    warn "CLAUDE.md is a symlink -> ${target}"
    warn "  Adding @reference to the symlink target"
  fi

  printf '\n%s\n' "$AT_REFERENCE" >> "$CLAUDE_MD"
  info "Added ${AT_REFERENCE} to CLAUDE.md"
else
  info "${AT_REFERENCE} already in CLAUDE.md — skipping"
fi

# --- Done ---

echo ""
info "Installation complete!"
echo ""
echo "  Skills:        ~/.claude/skills/sdd-*/"
echo "  Protocols:     ~/.claude/skills/_shared/"
echo "  Orchestrator:  ~/.claude/${ORCHESTRATOR_FILE}"
echo "  Reference:     ${AT_REFERENCE} in CLAUDE.md"
echo ""
echo "  Re-run this script to update after pulling new changes."
