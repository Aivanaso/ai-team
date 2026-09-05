#!/usr/bin/env bash
# check-skill-budgets.sh -- Check that each skill's SKILL.md stays within the 250-line budget
# and each orchestrator card (domain/skills/_shared/cards/*.md) within 60 lines.
#
# Usage:
#   ./scripts/check-skill-budgets.sh
#
# Exit codes:
#   0 -- all SKILL.md files within budget
#   1 -- at least one file over budget (paths and line counts printed to stderr)
#   2 -- invocation error (no files found)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BUDGET=250
CARD_BUDGET=60
over=0
total=0

# Every skill directory has a SKILL.md; _shared holds only shared protocols and
# scripts (no SKILL.md), so the glob excludes it without a separate filter.
shopt -s nullglob
files=("$REPO_ROOT"/domain/skills/*/SKILL.md)
shopt -u nullglob

if (( ${#files[@]} == 0 )); then
  echo "check-skill-budgets: ERROR: no SKILL.md files found under domain/skills/*/" >&2
  exit 2
fi

for f in "${files[@]}"; do
  lines=$(wc -l < "$f")
  total=$((total + 1))
  if (( lines > BUDGET )); then
    echo "OVER BUDGET: $f -- $lines lines (limit: $BUDGET)" >&2
    over=$((over + 1))
  else
    echo "OK: $f -- $lines lines"
  fi
done

shopt -s nullglob
cards=("$REPO_ROOT"/domain/skills/_shared/cards/*.md)
shopt -u nullglob
for f in "${cards[@]}"; do
  lines=$(wc -l < "$f")
  total=$((total + 1))
  if (( lines > CARD_BUDGET )); then
    echo "OVER BUDGET: $f -- $lines lines (limit: $CARD_BUDGET)" >&2
    over=$((over + 1))
  else
    echo "OK: $f -- $lines lines"
  fi
done

if (( over > 0 )); then
  echo "check-skill-budgets: $over file(s) over budget." >&2
  exit 1
else
  echo "check-skill-budgets: all $total files within budget (skills <= $BUDGET lines, cards <= $CARD_BUDGET)."
  exit 0
fi
