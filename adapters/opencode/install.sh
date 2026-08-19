#!/usr/bin/env bash
#
# adapters/opencode/install.sh -- OpenCode adapter for ai-team
#
# Installs the ai-team organic evidence-tiered delegation framework into
# ~/.config/opencode/ for use with OpenCode.
#
# Usage:
#   ./adapters/opencode/install.sh
#
# Or via the top-level selector:
#   ./scripts/install.sh --adapter=opencode
#
# What it does:
#   1. Copies skills to ~/.config/opencode/skills/
#   2. Rewrites skill paths in orchestrator-protocol.md (idempotency-safe)
#   3. Copies orchestrator instructions to ~/.config/opencode/AGENTS.md
#   4. Merges agent definitions into ~/.config/opencode/opencode.json (deep-merge)
#
# Requirements:
#   jq (for JSON merge)
#
# Re-run to update after pulling new changes from the repo.
# Existing operator agents not named after this framework's own agents are preserved.

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

# Manifest-based pruning: remove target paths this framework installed on a
# prior run but no longer ships, without touching anything it never listed
# (user-owned skills are never in the manifest, so they are never a pruning
# candidate). No literal retired-name list — driven entirely by the diff
# between the previous manifest and the current source set.
MANIFEST_FILE="$OPENCODE_DIR/.ai-team-manifest"

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

# --- 0. Prune stale framework-managed paths ---

# The current source set this run will install: skill dirs (no agent/command
# files on this adapter — agents live inside the merged opencode.json).
CURRENT_MANAGED_SET=()
for dir in "$REPO_ROOT/domain/skills/"*/; do
  CURRENT_MANAGED_SET+=("skills/$(basename "$dir")")
done

prune_stale_manifest_entries "$OPENCODE_DIR" "$MANIFEST_FILE" "${CURRENT_MANAGED_SET[@]}"

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

skill_count=$(find "$OPENCODE_DIR/skills" -mindepth 1 -maxdepth 1 -type d -not -name '_shared' 2>/dev/null | wc -l)
info "  -> ~/.config/opencode/skills/ ($skill_count skills)"

# Verify every source file landed at the corresponding destination.
verify_install "$OPENCODE_DIR/skills"

# --- 1b. Write install manifest (for next run's pruning) ---

printf '%s\n' "${CURRENT_MANAGED_SET[@]}" > "$MANIFEST_FILE"
info "  -> wrote $MANIFEST_FILE (${#CURRENT_MANAGED_SET[@]} managed paths)"

# Rewrite skill paths in the orchestrator protocol for installed location.
# Anchored pattern (command `bash skills/...`) is idempotent by construction —
# after one rewrite the pattern no longer matches — and it leaves
# `{install_dir}/skills/...` references and prose mentioning skill roots untouched.
ORCHESTRATOR_PROTOCOL="$OPENCODE_DIR/skills/_shared/orchestrator-protocol.md"
if [[ -f "$ORCHESTRATOR_PROTOCOL" ]]; then
  sed -i \
    -e 's|bash skills/_shared/|bash ~/.config/opencode/skills/_shared/|g' \
    "$ORCHESTRATOR_PROTOCOL"
  info "  -> Rewrote skill paths in orchestrator-protocol.md"
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
  # Existing operator agents not named after this framework's own agents are preserved.
  # Note: permission.task is a framework-owned subtree (the orchestrator's allow-list of
  # its own sub-agents) — it is REPLACED wholesale by the overlay's value, not unioned via
  # `*`. A plain recursive merge would union keys and never drop an allow entry for an
  # agent retired from a prior ai-team version, since the overlay has no key to override
  # it with. Wholesale replacement makes every re-install converge on exactly the current
  # agent set. This intentionally does not preserve a hand-added permission.task entry for
  # a non-framework agent under the orchestrator — that subtree belongs to ai-team alone.
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
    | .agent.orchestrator.permission.task = $overlay.agent.orchestrator.permission.task
  ' "$TARGET_JSON" "$OVERLAY_JSON" > "$TMP_JSON"
  mv "$TMP_JSON" "$TARGET_JSON"
  info "  -> ~/.config/opencode/opencode.json (merged, user model pins preserved)"
else
  cp "$OVERLAY_JSON" "$TARGET_JSON"
  info "  -> ~/.config/opencode/opencode.json (created)"
fi

# --- Done ---

echo ""
info "Installation complete! (OpenCode adapter)"
echo ""
echo "  Skills:       ~/.config/opencode/skills/{organic-implementer,organic-reviewer,organic-scout,organic-security,work-unit-commits,organic-retro}/"
echo "  Protocols:    ~/.config/opencode/skills/_shared/"
echo "  Orchestrator: ~/.config/opencode/AGENTS.md"
echo "  Config:       ~/.config/opencode/opencode.json"
echo ""
echo "  Select the 'orchestrator' agent in OpenCode."
echo "  No slash commands — delegation is conversational, driven by AGENTS.md."
echo ""
echo "  Re-run this script to update after pulling new changes."
