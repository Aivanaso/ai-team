#!/usr/bin/env bash
# refresh-skill-registry.sh — regenerate .ai-team/skill-registry.md from on-disk SKILL.md files.
#
# Contract (orchestrator Auto-Init "Skill Registry Refresh"):
# scans project skill roots first, then user roots; indexes frontmatter name + description
# + scope + path of every stack/convention skill; dedupes by name with first-hit-wins, so a
# project skill beats a user/global skill of the same name; excludes the SDD pipeline's own
# skills (sdd-*, work-unit-commits, _shared) — phases are delegated by the DAG, never
# matched by stack. The registry is an INDEX, not a summary: delegators match rows and
# forward exact SKILL.md paths; sub-agents read the full files (author intent preserved).
#
# Freshness: fingerprint cache (schema + path:mtime:size of every SKILL.md found, sha1).
# Unchanged fingerprint + existing registry → "cache-hit" no-op, so the orchestrator runs
# this every session and freshness needs no bookkeeping.
#
# Usage: refresh-skill-registry.sh [--project-root <dir>] [--home <dir>] [--force] [--quiet]
# Exit:  0 ok (regenerated or cache-hit) · 2 usage error
# Output: "regenerated (N skills)" | "cache-hit" (silenced by --quiet)
# Limitations: frontmatter parsed line-oriented (single-line value or folded block for
#              description); skills live one level under each root ({root}/{skill}/SKILL.md);
#              the registry holds absolute paths — machine-local state, keep it gitignored.

set -u

SCHEMA=1
project_root="$PWD"
home_dir="$HOME"
force=0
quiet=0

usage() { echo "usage: $0 [--project-root <dir>] [--home <dir>] [--force] [--quiet]" >&2; exit 2; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-root) shift; [ "$#" -ge 1 ] || usage; project_root="$1" ;;
    --home) shift; [ "$#" -ge 1 ] || usage; home_dir="$1" ;;
    --force) force=1 ;;
    --quiet) quiet=1 ;;
    *) usage ;;
  esac
  shift
done

project_root="$(cd "$project_root" 2>/dev/null && pwd)" || { echo "project root not found" >&2; exit 2; }

# Project roots first: repo-local intent beats user/global skills on name collisions.
scan_roots=(
  "$project_root/skills"
  "$project_root/.claude/skills"
  "$project_root/.opencode/skills"
  "$project_root/.agents/skills"
  "$home_dir/.claude/skills"
  "$home_dir/.config/opencode/skills"
  "$home_dir/.agents/skills"
)

registry_dir="$project_root/.ai-team"
registry="$registry_dir/skill-registry.md"
cache="$registry_dir/.skill-registry.cache"

# ── Collect SKILL.md files in scan order, skipping pipeline skills ──
files=()
sources=()
for root in "${scan_roots[@]}"; do
  [ -d "$root" ] || continue
  sources+=("$root")
  while IFS= read -r f; do
    skill_dir="$(basename "$(dirname "$f")")"
    case "$skill_dir" in
      _shared|skill-registry|work-unit-commits|sdd-*) continue ;;
    esac
    files+=("$f")
  done < <(find "$root" -mindepth 2 -maxdepth 2 -type f -name SKILL.md 2>/dev/null | LC_ALL=C sort)
done

# ── Fingerprint: schema + path:mtime:size, sorted, sha1 ──
fp="$(
  {
    echo "schema:$SCHEMA"
    for f in ${files[@]+"${files[@]}"}; do
      stat -c '%n:%Y:%s' "$f" 2>/dev/null || echo "$f:missing"
    done
  } | LC_ALL=C sort | sha1sum | cut -d' ' -f1
)"

cached=""
[ -f "$cache" ] && cached="$(cat "$cache")"
if [ "$force" -eq 0 ] && [ -n "$cached" ] && [ "$cached" = "$fp" ] && [ -f "$registry" ]; then
  [ "$quiet" -eq 1 ] || echo "cache-hit"
  exit 0
fi

# ── Parse frontmatter (name + description; folded blocks joined) ──
parse_frontmatter() {
  awk '
    NR==1 { if ($0 !~ /^---[[:space:]]*$/) exit; next }
    /^---[[:space:]]*$/ { exit }
    /^name:/        { v=$0; sub(/^name:[[:space:]]*/, "", v); name=v; folded=0; next }
    /^description:/ {
      v=$0; sub(/^description:[[:space:]]*/, "", v)
      if (v ~ /^[>|][+-]?[[:space:]]*$/) { desc=""; folded=1 } else { desc=v; folded=0 }
      next
    }
    /^[A-Za-z_-]+:/ { folded=0; next }
    folded==1 && /^[[:space:]]+[^[:space:]]/ {
      line=$0; gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
      desc = (desc=="" ? line : desc " " line); next
    }
    END { print name; print desc }
  ' "$1"
}

strip_quotes() {
  local s="$1"
  s="${s#\"}"; s="${s%\"}"
  s="${s#\'}"; s="${s%\'}"
  printf '%s' "$s"
}

names=(); descs=(); scopes=(); paths=()
for f in ${files[@]+"${files[@]}"}; do
  fm="$(parse_frontmatter "$f")"
  name="$(strip_quotes "$(printf '%s\n' "$fm" | sed -n 1p)")"
  desc="$(strip_quotes "$(printf '%s\n' "$fm" | sed -n 2p)")"
  [ -n "$name" ] || name="$(basename "$(dirname "$f")")"
  dup=0
  for n in ${names[@]+"${names[@]}"}; do
    [ "$n" = "$name" ] && { dup=1; break; }
  done
  [ "$dup" -eq 1 ] && continue
  case "$f" in
    "$project_root"/*) scope="project" ;;
    *) scope="user" ;;
  esac
  desc="${desc//|/\\|}"
  names+=("$name"); descs+=("$desc"); scopes+=("$scope"); paths+=("$f")
done

# ── Render registry (atomic write) ──
mkdir -p "$registry_dir"
tmp="$(mktemp "$registry_dir/.skill-registry.XXXXXX")"
{
  echo "# Skill Registry — $(basename "$project_root")"
  echo
  echo "<!-- Auto-generated by refresh-skill-registry.sh; regenerate with --force. Machine-local derived state (absolute paths) — keep gitignored. -->"
  echo
  echo "Last updated: $(date -u +%F)"
  echo
  echo "## Sources scanned"
  echo
  for src in ${sources[@]+"${sources[@]}"}; do
    echo "- $src"
  done
  echo
  echo "## Contract"
  echo
  echo "**Delegator use only.** This registry is an index, not a summary. The orchestrator matches rows against the task's stack and target file paths, then forwards the matching \`Path\` values under \`## Skills to load before work\`; the sub-agent reads those exact SKILL.md files in full before work. SKILL.md stays the source of truth — paths travel, summaries stay home, so author intent survives delegation."
  echo
  echo "## Skills"
  echo
  echo "| Skill | Trigger / description | Scope | Path |"
  echo "| --- | --- | --- | --- |"
  i=0
  while [ "$i" -lt "${#names[@]}" ]; do
    echo "| \`${names[$i]}\` | ${descs[$i]} | ${scopes[$i]} | \`${paths[$i]}\` |"
    i=$((i + 1))
  done
  [ "${#names[@]}" -eq 0 ] && echo "| — | (no stack skills found in the scanned roots) | — | — |"
  echo
  echo "## Loading protocol"
  echo
  echo "1. Match task context and target files against the \`Trigger / description\` column."
  echo "2. Forward only the matching \`Path\` values under \`## Skills to load before work\`."
  echo "3. The sub-agent reads those exact SKILL.md files before reading, writing, reviewing, or testing artifacts."
  echo "4. Zero matching rows → delegate without a skills block; the sub-agent reports \`skill_resolution: none\`."
} > "$tmp"
mv "$tmp" "$registry"
printf '%s\n' "$fp" > "$cache"

[ "$quiet" -eq 1 ] || echo "regenerated (${#names[@]} skills)"
exit 0
