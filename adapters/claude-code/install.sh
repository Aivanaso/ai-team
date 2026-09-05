#!/usr/bin/env bash
#
# adapters/claude-code/install.sh -- Claude Code adapter for ai-team
#
# Installs the ai-team organic evidence-tiered delegation framework into
# ~/.claude/ for use with Claude Code.
#
# Usage:
#   ./adapters/claude-code/install.sh
#
# Or via the top-level selector:
#   ./scripts/install.sh --adapter=claude-code
#
# What it does:
#   1. Copies skills to ~/.claude/skills/
#   2. Copies agent files to ~/.claude/agents/
#   3. Rewrites skill paths in every installed skill .md file (idempotency-safe)
#   4. Registers the ai-team machine's hooks (PreToolUse on Agent, SessionStart)
#      in ~/.claude/settings.json via merge-hooks.py -- backup first, foreign
#      hooks untouched, idempotent; `merge-hooks.py <settings> <hooks.json> --remove`
#      undoes it
#   5. Injects orchestrator stub into ~/.claude/CLAUDE.md
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

# Manifest-based pruning: remove target paths this framework installed on a
# prior run but no longer ships, without touching anything it never listed
# (user-owned skills/agents are never in the manifest, so they are never a
# pruning candidate). No literal retired-name list — driven entirely by the
# diff between the previous manifest and the current source set.
MANIFEST_FILE="$CLAUDE_DIR/.ai-team-manifest"

prune_stale_manifest_entries() {
  local target_dir="$1" manifest_file="$2"; shift 2
  local -a current_set=("$@")
  [[ -f "$manifest_file" ]] || return 0
  local entry still_present cur
  while IFS= read -r entry; do
    [[ -z "$entry" ]] && continue
    [[ "$entry" == /* || "$entry" == *..* ]] && continue
    still_present=0
    for cur in "${current_set[@]}"; do
      if [[ "$cur" == "$entry" ]]; then still_present=1; break; fi
    done
    if [[ "$still_present" -eq 0 ]]; then
      rm -rf "${target_dir:?}/${entry:?}"
      info "  -> pruned stale $entry (no longer shipped by this framework)"
    fi
  done < "$manifest_file"
}

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
  done < <(find "$REPO_ROOT/domain/skills" -type f -not -path '*/__pycache__/*' -print0)

  if (( missing > 0 )); then
    die "verify-install: $missing file(s) failed to copy. See errors above."
  fi
  info "  -> verify-install: all $(find "$REPO_ROOT/domain/skills" -type f -not -path '*/__pycache__/*' | wc -l) source files present"
}

# --- Preflight ---

# The ai-team machine (skills/_shared/scripts/ai-team, Python stdlib only) is what
# the hooks and the orchestrator run — fail fast without a python3 on PATH rather
# than let every hook silently error out mid-task.
command -v python3 >/dev/null 2>&1 || die "python3 required (used by skills/_shared/scripts/ai-team)."

# Create ~/.claude/ if missing — supports fresh-install scenarios (Claude Code
# installed but never run) and smoke tests against temp HOME directories.
mkdir -p "$CLAUDE_DIR"

# --- 0. Prune stale framework-managed paths ---

# The current source set this run will install: skill dirs + agent files.
# Computed before any copy so pruning runs against last run's manifest, not this one.
CURRENT_MANAGED_SET=()
for dir in "$REPO_ROOT/domain/skills/"*/; do
  CURRENT_MANAGED_SET+=("skills/$(basename "$dir")")
done
for agent_file in "$REPO_ROOT/adapters/claude-code/templates/agents/"*.md; do
  CURRENT_MANAGED_SET+=("agents/$(basename "$agent_file")")
done

prune_stale_manifest_entries "$CLAUDE_DIR" "$MANIFEST_FILE" "${CURRENT_MANAGED_SET[@]}"

# --- 1. Skills ---

info "Installing skills..."
for dir in "$REPO_ROOT/domain/skills/"*/; do
  name=$(basename "$dir")
  dest="$CLAUDE_DIR/skills/$name"

  # Wipe destination first to avoid stale files from prior installs.
  rm -rf "$dest"
  mkdir -p "$dest"

  # Recursive copy: includes references/ subdirectories.
  # cp -R (POSIX) not cp -r (GNU). Trailing /. copies directory contents into $dest.
  if ! cp -R "$dir." "$dest/" 2>/dev/null; then
    die "skill $name: failed to copy from $dir to $dest"
  fi
  # Never ship Python byte-cache from the checkout (py_compile leaves it behind).
  find "$dest" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
done

skill_count=$(find "$CLAUDE_DIR/skills" -mindepth 1 -maxdepth 1 -type d -not -name '_shared' 2>/dev/null | wc -l)
info "  -> ~/.claude/skills/ ($skill_count skills)"

# The machine's launcher must stay executable: the hooks call it by path.
chmod +x "$CLAUDE_DIR/skills/_shared/scripts/ai-team" "$CLAUDE_DIR/skills/_shared/scripts/ai_team/cli.py"
"$CLAUDE_DIR/skills/_shared/scripts/ai-team" --help >/dev/null || die "the installed ai-team launcher does not run"

# Verify every source file landed at the corresponding destination.
verify_install "$CLAUDE_DIR/skills"

# Rewrite skill paths for the installed location, across every .md file of the
# skills THIS installer ships (the same set the copy loop above wrote), never
# third-party skills under ~/.claude/skills. Three invocation prefixes need the
# rewrite: `bash skills/_shared/...` (refresh-skill-registry.sh), `python3
# skills/_shared/...`, and the machine `skills/_shared/scripts/ai-team` (anchored
# on a non-slash predecessor so a rewritten path is never rewritten again).
# Idempotent by construction; `{install_dir}/skills/...` references and prose
# mentioning skill roots are left untouched.
while IFS= read -r -d '' md_file; do
  if grep -qE 'bash skills/_shared/|python3 skills/_shared/|(^|[^/])skills/_shared/scripts/ai-team' "$md_file"; then
    sed -i -E \
      -e 's|bash skills/_shared/|bash ~/.claude/skills/_shared/|g' \
      -e 's|python3 skills/_shared/|python3 ~/.claude/skills/_shared/|g' \
      -e 's#(^|[^/])skills/_shared/scripts/ai-team#\1~/.claude/skills/_shared/scripts/ai-team#g' \
      "$md_file"
    info "  -> Rewrote skill paths in ${md_file#"$CLAUDE_DIR"/}"
  fi
done < <(
  # Scope: ONLY the skill directories this run installs (mirrors the copy loop
  # above) — never the whole ~/.claude/skills tree, which may hold third-party
  # skills whose docs legitimately mention these prefixes.
  for src_dir in "$REPO_ROOT/domain/skills/"*/; do
    find "$CLAUDE_DIR/skills/$(basename "$src_dir")" -type f -name '*.md' -print0 2>/dev/null
  done
)

# --- 2. Agents ---

info "Installing agents..."
mkdir -p "$CLAUDE_DIR/agents"

for agent_file in "$REPO_ROOT/adapters/claude-code/templates/agents/"*.md; do
  name=$(basename "$agent_file")
  cp "$agent_file" "$CLAUDE_DIR/agents/$name"
done

agent_count=$(ls "$REPO_ROOT/adapters/claude-code/templates/agents/"*.md 2>/dev/null | wc -l)
info "  -> ~/.claude/agents/ ($agent_count agent files)"

# --- 2b. Write install manifest (for next run's pruning) ---

printf '%s\n' "${CURRENT_MANAGED_SET[@]}" > "$MANIFEST_FILE"
info "  -> wrote $MANIFEST_FILE (${#CURRENT_MANAGED_SET[@]} managed paths)"

# --- 2c. Register the machine's hooks in settings.json ---

info "Registering hooks in ~/.claude/settings.json..."
python3 "$SCRIPT_DIR/merge-hooks.py" "$CLAUDE_DIR/settings.json" "$SCRIPT_DIR/templates/hooks.json" \
  || die "hook registration failed -- settings.json left unchanged (see the message above)"

# --- 3. Prepare orchestrator content ---

info "Preparing orchestrator content..."

ORCHESTRATOR_CONTENT=$(cat "$REPO_ROOT/adapters/claude-code/templates/CLAUDE.md")

# --- 4. Resolve CLAUDE.md (handle symlinks) ---

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

# --- 5. Clean up legacy @reference (if present) ---

if grep -qF "$LEGACY_REFERENCE" <<< "$EXISTING"; then
  warn "Removing legacy ${LEGACY_REFERENCE}..."
  EXISTING=$(grep -vF "$LEGACY_REFERENCE" <<< "$EXISTING")
fi

# Also remove the old standalone orchestrator file if it exists
if [[ -f "$CLAUDE_DIR/ai-team-orchestrator.md" ]]; then
  rm "$CLAUDE_DIR/ai-team-orchestrator.md"
  warn "Removed legacy ~/.claude/ai-team-orchestrator.md"
fi

# --- 6. Inject between markers ---

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

# --- 7. Write back ---

# Write atomically: temp file + move
TMPFILE=$(mktemp "${WRITE_TARGET}.XXXXXX")
echo "$UPDATED" > "$TMPFILE"
mv "$TMPFILE" "$WRITE_TARGET"

info "  -> ${WRITE_TARGET}"

# --- Done ---

echo ""
info "Installation complete! (Claude Code adapter)"
echo ""
echo "  Skills:       ~/.claude/skills/{organic-implementer,organic-reviewer,organic-scout,organic-security,organic-retro}/"
echo "  Agents:       ~/.claude/agents/*.md"
echo "  Shared:       ~/.claude/skills/_shared/ (machine.md, cards/, scripts/ai-team)"
echo "  Hooks:        PreToolUse(Agent) + SessionStart in ~/.claude/settings.json (backup written beside it)"
echo "  Orchestrator: stub in CLAUDE.md (between markers)"
echo ""
echo "  The machine: ~/.claude/skills/_shared/scripts/ai-team status"
echo "  Uninstall hooks: python3 adapters/claude-code/merge-hooks.py ~/.claude/settings.json adapters/claude-code/templates/hooks.json --remove"
echo "  Re-run this script to update after pulling new changes."
