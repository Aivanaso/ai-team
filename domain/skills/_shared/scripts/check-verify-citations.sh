#!/usr/bin/env bash
# check-verify-citations.sh — mechanical resolution check for verification-report.md citations.
#
# Contract (sdd-verify Step 15b + orchestrator Post-Verify Citation Audit):
# every table row whose State/Result cell is COMPLIANT or FAILING must carry at
# least one backticked citation token:
#   `path::test_name`   path repo-relative; test_name a verbatim string in that file
#   `checklist:C-{N}`   meta-project Bash criterion (proof = pasted command output)
# A citation that does not resolve on disk is treated as fabricated.
#
# Usage: check-verify-citations.sh <verification-report.md> [repo-root]
# Exit:  0 all citations resolve · 1 unresolved citations (listed on stdout) · 2 usage error
# Limitation: test_name cannot contain a literal '|' or backtick (markdown table cell).

set -u

usage() { echo "usage: $0 <verification-report.md> [repo-root]" >&2; exit 2; }
[ "$#" -ge 1 ] || usage
report="$1"
root="${2:-.}"
[ -f "$report" ] || { echo "ERROR: report not found: $report" >&2; exit 2; }
[ -d "$root" ] || { echo "ERROR: repo root not found: $root" >&2; exit 2; }

checked=0
skipped=0
violations=0

# Rows declaring COMPLIANT or FAILING as a standalone table cell.
while IFS= read -r row; do
  [ -n "$row" ] || continue
  lineno="${row%%:*}"
  line="${row#*:}"

  tokens="$(printf '%s\n' "$line" | grep -oE '`[^`]+`' | sed 's/^`//; s/`$//' | grep -E '::|^checklist:' || true)"

  if [ -z "$tokens" ]; then
    echo "UNRESOLVED $report:$lineno — missing citation token (\`path::test_name\` or \`checklist:C-{N}\`)"
    violations=$((violations + 1))
    continue
  fi

  while IFS= read -r tok; do
    [ -n "$tok" ] || continue
    case "$tok" in
      checklist:*)
        skipped=$((skipped + 1))
        continue
        ;;
    esac
    path="${tok%%::*}"
    name="${tok#*::}"
    checked=$((checked + 1))
    if [ ! -f "$root/$path" ]; then
      echo "UNRESOLVED $report:$lineno — \`$tok\` — file not found: $path"
      violations=$((violations + 1))
    elif ! grep -qF -- "$name" "$root/$path"; then
      echo "UNRESOLVED $report:$lineno — \`$tok\` — test name not found in $path"
      violations=$((violations + 1))
    fi
  done <<EOF
$tokens
EOF
done <<EOF
$(grep -nE '\|[[:space:]]*(COMPLIANT|FAILING)[[:space:]]*\|' "$report" || true)
EOF

echo "citation-audit: $checked test refs checked, $skipped checklist refs skipped, $violations unresolved"
[ "$violations" -eq 0 ]
