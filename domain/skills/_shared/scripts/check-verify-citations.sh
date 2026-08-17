#!/usr/bin/env bash
# check-verify-citations.sh — mechanical resolution check for review report citations.
#
# Contract (orchestrator-protocol.md "Evidence-Tier Review" → Citation audit):
# two independent, additive checks run over the same report file.
#
# 1. Legacy table-row check (kept working, cheap — no live producer requires this shape,
#    but a report using it is still validated the same way):
#    every table row whose State/Result cell starts with COMPLIANT or FAILING (bold or
#    annotated variants included, e.g. **COMPLIANT** or "FAILING (re-run)") must carry at
#    least one backticked citation token:
#      `path::test_name`   path repo-relative; test_name a verbatim string in that file.
#                           When test-output.log exists, the path or test name must ALSO
#                           appear in it — existence on disk plus execution evidence.
#      `checklist:C-{N}`   Bash criterion — the criterion ID must exist in tasks-md when
#                           given and found; skipped otherwise (no live producer emits this
#                           token; the branch is inert unless a report uses it).
#    A citation that does not resolve on disk is treated as fabricated. A citation that
#    resolves on disk but is absent from the execution log names a test that never ran.
#
# 2. Receipt-shaped findings check (organic-reviewer / organic-security report-format.md):
#    a finding is anchored by its stable `F-<n>` id; the finding's block runs from that
#    marker to the next `F-<n>` marker or the next markdown heading (##/###), whichever
#    comes first. Any such block that carries a CRITICAL/MAJOR/MINOR severity token MUST
#    also carry a `path/to/file:line`-shaped citation somewhere in the block — presence
#    only, no on-disk resolution (the citation's line-level claim is opaque to this script).
#    Limitation: a Suppression Tally mention of an `F-<n>` id that does NOT restate a
#    severity token is not treated as a finding row (avoids false positives on suppressed
#    references) — do not rely on this to skip citing an actual finding.
#
# Usage: check-verify-citations.sh <report.md> [repo-root] [tasks-md] [test-log]
#        tasks-md defaults to tasks.md next to the report;
#        test-log defaults to test-output.log next to the report (skip check if absent).
# Exit:  0 all citations resolve · 1 unresolved citations (listed on stdout) · 2 usage error
# Limitations: test_name cannot contain a literal '|' or backtick (markdown table cell);
#              checklist IDs match as substrings (uniformly zero-padded IDs avoid collisions).

set -u

usage() { echo "usage: $0 <verification-report.md> [repo-root] [tasks-md] [test-log]" >&2; exit 2; }
[ "$#" -ge 1 ] || usage
report="$1"
root="${2:-.}"
tasks_md="${3:-}"
test_log="${4:-}"
[ -f "$report" ] || { echo "ERROR: report not found: $report" >&2; exit 2; }
[ -d "$root" ] || { echo "ERROR: repo root not found: $root" >&2; exit 2; }
[ -n "$tasks_md" ] || tasks_md="$(dirname "$report")/tasks.md"
[ -n "$test_log" ] || test_log="$(dirname "$report")/test-output.log"

checked=0
checklist_checked=0
skipped=0
exec_checked=0
exec_skipped=0
violations=0

# Rows whose cell starts with COMPLIANT or FAILING (tolerates **bold**/_emphasis_ and
# trailing annotations inside the cell — a bare substring elsewhere in a cell does not count).
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
        cid="${tok#checklist:}"
        if [ -f "$tasks_md" ]; then
          checklist_checked=$((checklist_checked + 1))
          if ! grep -qF -- "$cid" "$tasks_md"; then
            echo "UNRESOLVED $report:$lineno — \`$tok\` — criterion $cid not found in $tasks_md"
            violations=$((violations + 1))
          fi
        else
          skipped=$((skipped + 1))
        fi
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
    elif [ -f "$test_log" ]; then
      exec_checked=$((exec_checked + 1))
      if ! grep -qF -- "$path" "$test_log" && ! grep -qF -- "$name" "$test_log"; then
        echo "UNRESOLVED $report:$lineno — \`$tok\` — neither path nor test name appears in $test_log (cited test may not have run)"
        violations=$((violations + 1))
      fi
    else
      exec_skipped=$((exec_skipped + 1))
    fi
  done <<EOF
$tokens
EOF
done <<EOF
$(grep -nE '\|[[:space:]]*([*_]{1,2})?(COMPLIANT|FAILING)\b[^|]*\|' "$report" || true)
EOF

# --- Receipt-shaped findings: each F-<n> block carrying CRITICAL/MAJOR/MINOR must cite file:line ---
finding_checked=0
finding_violations=0
total_report_lines="$(wc -l < "$report")"

mapfile -t bound_lines < <(grep -nE '(^#{1,6}[[:space:]]|\bF-[0-9]+\b)' "$report" | cut -d: -f1 | LC_ALL=C sort -n -u)
mapfile -t fmarker_lines < <(grep -nE '\bF-[0-9]+\b' "$report" | cut -d: -f1 | LC_ALL=C sort -n -u)

for lineno in ${fmarker_lines[@]+"${fmarker_lines[@]}"}; do
  block_end="$total_report_lines"
  for b in ${bound_lines[@]+"${bound_lines[@]}"}; do
    if [ "$b" -gt "$lineno" ]; then
      block_end=$((b - 1))
      break
    fi
  done
  block="$(sed -n "${lineno},${block_end}p" "$report")"
  if printf '%s\n' "$block" | grep -qE '\b(CRITICAL|MAJOR|MINOR)\b'; then
    finding_checked=$((finding_checked + 1))
    if ! printf '%s\n' "$block" | grep -qE '([A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+:[0-9]+|[A-Za-z0-9_-]+\.[A-Za-z0-9]+:[0-9]+'; then
      echo "UNRESOLVED $report:$lineno — finding carries a severity (CRITICAL/MAJOR/MINOR) with no resolvable file:line citation in its block"
      violations=$((violations + 1))
      finding_violations=$((finding_violations + 1))
    fi
  fi
done

echo "citation-audit: $checked test refs checked, $exec_checked exec-evidence checked, $exec_skipped exec-evidence skipped (no test-output.log), $checklist_checked checklist refs checked, $skipped checklist refs skipped (no tasks.md), $finding_checked severity findings checked, $finding_violations findings missing citation, $violations unresolved"
[ "$violations" -eq 0 ]
