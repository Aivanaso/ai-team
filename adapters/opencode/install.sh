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
#   1. Copies skills to ~/.config/opencode/skills/ (pruning any __pycache__ left
#      behind by py_compile in the checkout)
#   2. Rewrites skill paths in every installed skill .md file (idempotency-safe)
#   3. Copies orchestrator instructions to ~/.config/opencode/AGENTS.md
#   4. Merges agent definitions into ~/.config/opencode/opencode.json (deep-merge)
#
# Requirements:
#   python3 (runs skills/_shared/scripts/ai-team, the task state machine)
#   jq      (for the opencode.json deep-merge only)
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
  done < <(find "$REPO_ROOT/domain/skills" -type f -not -path '*/__pycache__/*' -print0)

  if (( missing > 0 )); then
    die "verify-install: $missing file(s) failed to copy. See errors above."
  fi
  info "  -> verify-install: all $(find "$REPO_ROOT/domain/skills" -type f -not -path '*/__pycache__/*' | wc -l) source files present"
}

# --- Preflight ---

# The ai-team machine (skills/_shared/scripts/ai-team, Python stdlib) is
# Python-stdlib-only but still needs a python3 interpreter on PATH — fail
# fast rather than let the gate silently error out mid-task.
command -v python3 >/dev/null 2>&1 || die "python3 required (used by skills/_shared/scripts/ai-team)."

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
  # Never ship Python byte-cache from the checkout (py_compile leaves it behind).
  find "$dest" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
done

skill_count=$(find "$OPENCODE_DIR/skills" -mindepth 1 -maxdepth 1 -type d -not -name '_shared' 2>/dev/null | wc -l)
info "  -> ~/.config/opencode/skills/ ($skill_count skills)"

# Verify every source file landed at the corresponding destination.
verify_install "$OPENCODE_DIR/skills"

# --- 1b. Write install manifest (for next run's pruning) ---

printf '%s\n' "${CURRENT_MANAGED_SET[@]}" > "$MANIFEST_FILE"
info "  -> wrote $MANIFEST_FILE (${#CURRENT_MANAGED_SET[@]} managed paths)"

# The machine's launcher must stay executable.
chmod +x "$OPENCODE_DIR/skills/_shared/scripts/ai-team" "$OPENCODE_DIR/skills/_shared/scripts/ai_team/cli.py"
"$OPENCODE_DIR/skills/_shared/scripts/ai-team" --help >/dev/null || die "the installed ai-team launcher does not run"

# Rewrite skill paths for the installed location, across every .md file of the
# skills THIS installer ships (the same set the copy loop above wrote), never
# third-party skills under ~/.config/opencode/skills. Three invocation prefixes
# need the rewrite: `bash skills/_shared/...` (refresh-skill-registry.sh),
# `python3 skills/_shared/...`, and the machine `skills/_shared/scripts/ai-team`
# (anchored on a non-slash predecessor so a rewritten path is never rewritten
# again). Idempotent by construction.
while IFS= read -r -d '' md_file; do
  if grep -qE 'bash skills/_shared/|python3 skills/_shared/|(^|[^/])skills/_shared/scripts/ai-team' "$md_file"; then
    sed -i -E \
      -e 's|bash skills/_shared/|bash ~/.config/opencode/skills/_shared/|g' \
      -e 's|python3 skills/_shared/|python3 ~/.config/opencode/skills/_shared/|g' \
      -e 's#(^|[^/])skills/_shared/scripts/ai-team#\1~/.config/opencode/skills/_shared/scripts/ai-team#g' \
      "$md_file"
    info "  -> Rewrote skill paths in ${md_file#"$OPENCODE_DIR"/}"
  fi
done < <(
  # Scope: ONLY the skill directories this run installs (mirrors the copy loop
  # above) — never the whole ~/.config/opencode/skills tree, which may hold
  # third-party skills whose docs legitimately mention these prefixes.
  for src_dir in "$REPO_ROOT/domain/skills/"*/; do
    find "$OPENCODE_DIR/skills/$(basename "$src_dir")" -type f -name '*.md' -print0 2>/dev/null
  done
)

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
  #
  # Stale-agent pruning (mirrors step 0's manifest-based pruning, same "no
  # literal retired-name list" discipline): a plain deep-merge (`*`) UNIONS
  # object keys, so an existing `.agent` entry this framework installed on a
  # prior run survives forever once its own skill is retired — the overlay
  # has no key left to override it with. Every framework-installed agent's
  # `prompt` field references its own skill file
  # (`.../skills/<name>/SKILL.md`, see the overlay template); an entry whose
  # prompt carries that pattern is dropped when <name> is not one of the
  # skill directories THIS run just installed (CURRENT_MANAGED_SET, computed
  # in step 0) — an entry whose prompt carries no such pattern (a genuine
  # operator-defined custom agent, including "orchestrator" itself, whose
  # prompt is a `{file:...}` reference) is never touched, preserving the
  # guarantee in the comment above.
  VALID_SKILL_NAMES_JSON=$(
    printf '%s\n' "${CURRENT_MANAGED_SET[@]}" | sed 's|^skills/||' | jq -R . | jq -s .
  )
  TMP_JSON=$(mktemp)
  jq -s --argjson valid_skills "$VALID_SKILL_NAMES_JSON" '
    .[0] as $existing | .[1] as $overlay |
    ($existing
      | .agent |= ((. // {}) | with_entries(
          select(
            (.value.prompt // "") as $p |
            if ($p | test("skills/[A-Za-z0-9_-]+/SKILL\\.md")) then
              (($p | capture("skills/(?<name>[A-Za-z0-9_-]+)/SKILL\\.md")).name) as $name
              | ($valid_skills | index($name)) != null
            else
              true
            end
          )
        ))
    ) as $existing_pruned |
    ($existing_pruned * $overlay)
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
echo "  Skills:       ~/.config/opencode/skills/{organic-implementer,organic-reviewer,organic-scout,organic-security,organic-retro}/"
echo "  Protocols:    ~/.config/opencode/skills/_shared/"
echo "  Orchestrator: ~/.config/opencode/AGENTS.md"
echo "  Config:       ~/.config/opencode/opencode.json"
echo ""
echo "  Select the 'orchestrator' agent in OpenCode."
echo "  No slash commands — delegation is conversational, driven by AGENTS.md."
echo ""
echo "  Re-run this script to update after pulling new changes."
