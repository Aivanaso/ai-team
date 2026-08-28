#!/usr/bin/env bash
# scripts/tests/run-script-tests.sh -- fixture-based regression tests for
# domain/skills/_shared/scripts/check-receipt.py.
#
# This is the Rule 7 calibration suite (domain/skills/_shared/evidence-protocol.md
# Rule 7: "a check that has never been observed to fail is not verified to
# test anything"). It MUST be run before any commit that touches
# domain/skills/_shared/scripts/ -- there is no CI hook for it (dev-only, see
# below), so this is a manual gate the orchestrator's Citation-audit paragraph
# names as a duty ("Orchestrator duty — the gate's own calibration",
# orchestrator-protocol.md → Citation audit).
#
# Fixture citation policy: fixtures cite README.md (a real tracked file) or a
# guaranteed-absent path, with THREE declared exceptions, each necessary to
# isolate one guard: receipt-file-is-directory.json cites the live directory
# domain/skills (isfile branch); receipt-file-absolute.json and
# receipt-file-traversal.json cite /etc/passwd (present on every POSIX system,
# so the absolute/traversal guards are exercised against a path that DOES exist
# -- a non-existent target would trip the existence check instead); and
# receipt-file-nul.json cites a path with an escaped NUL, isolating the
# realpath "unusable path" arm rather than any named guard. Every negative
# FULL-receipt fixture carries one valid verification row so that it fails for
# the rule it names and nothing else (calibration isolation) -- except the two
# fixtures whose rule under test IS the verification field
# (receipt-verification-empty.json, receipt-verification-garbage.json).
#
# Runs known-NEGATIVE fixtures FIRST (must exit 1) and known-EXIT-2 fixtures
# next (must exit 2 -- usage/parse failures that prevent validation from
# running at all, never a shape violation), THEN known-POSITIVE fixtures LAST
# (must exit 0) -- calibration order per Rule 7: never trust a green before
# you've proven the same check can fail.
#
# Dev-only: never referenced from any adapter install.sh, never installed
# alongside the shipped skills. Exercises check-receipt.py directly from this
# framework repo's own checkout.
#
# Usage: ./scripts/tests/run-script-tests.sh
# Exit:  0 every fixture behaved as expected / 1 at least one mismatch

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATOR="$REPO_ROOT/domain/skills/_shared/scripts/check-receipt.py"
FIXTURES="$SCRIPT_DIR/fixtures"

TMP_WORKDIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_WORKDIR"; }
trap cleanup EXIT

fail_count=0
total=0

assert_exit() {
  local label="$1" expected="$2"
  shift 2
  local out actual=0
  out="$(mktemp)"
  python3 "$@" >"$out" 2>&1 || actual=$?
  total=$((total + 1))
  if [[ "$actual" -eq "$expected" ]]; then
    echo "PASS: $label (exit $actual, expected $expected)"
  else
    echo "FAIL: $label (exit $actual, expected $expected)"
    sed 's/^/    /' "$out"
    fail_count=$((fail_count + 1))
  fi
  rm -f "$out"
}

# --- Known-negative fixtures FIRST: each must exit 1 -- proving the check
#     CAN fail before its green counts as evidence (Rule 7). ---

assert_exit "receipt-missing-file" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-missing-file.json" "$REPO_ROOT"
assert_exit "receipt-line-as-string" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-line-as-string.json" "$REPO_ROOT"
assert_exit "receipt-trigger-missing-major-read" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-trigger-missing-major-read.json" "$REPO_ROOT"
assert_exit "receipt-verdict-mismatch" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-verdict-mismatch.json" "$REPO_ROOT"
assert_exit "receipt-history-mismatch" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-history-mismatch.json" "$REPO_ROOT"
assert_exit "receipt-duplicate-ids" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-duplicate-ids.json" "$REPO_ROOT"
assert_exit "receipt-unknown-severity" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-unknown-severity.json" "$REPO_ROOT"
assert_exit "receipt-file-not-on-disk" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-file-not-on-disk.json" "$REPO_ROOT"
assert_exit "receipt-not-json" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-not-json.json" "$REPO_ROOT"
assert_exit "ledger-bad-sum" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-bad-sum.json"
assert_exit "ledger-tokens-string" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-tokens-string.json"
assert_exit "ledger-missing-commits-row" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-missing-commits-row.json"

# --- New negatives: containment (SEC-F-1/F-2), empty-but-passing
#     (REV-F-1/F-2/F-13/F-14, SEC-F-5), type strictness (REV-F-5/F-6/F-7),
#     identity (SEC-F-3/F-8), history coverage (SEC-F-6). ---

assert_exit "receipt-file-absolute" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-file-absolute.json" "$REPO_ROOT"
assert_exit "receipt-file-traversal" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-file-traversal.json" "$REPO_ROOT"
assert_exit "receipt-file-is-directory" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-file-is-directory.json" "$REPO_ROOT"
assert_exit "receipt-correctness-null" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-correctness-null.json" "$REPO_ROOT"
assert_exit "receipt-truncated-no-correctness" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-truncated-no-correctness.json" "$REPO_ROOT"
assert_exit "receipt-security-fragment-bad-verdict" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-security-fragment-bad-verdict.json" "$REPO_ROOT"
assert_exit "receipt-lens-status-incoherent" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-lens-status-incoherent.json" "$REPO_ROOT"
assert_exit "receipt-tier-bool" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-tier-bool.json" "$REPO_ROOT"
assert_exit "receipt-duplicate-ids-unicode" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-duplicate-ids-unicode.json" "$REPO_ROOT"
assert_exit "receipt-history-garbage-entry" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-history-garbage-entry.json" "$REPO_ROOT"
assert_exit "ledger-no-close" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-no-close.json"
assert_exit "ledger-close-bool" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-close-bool.json"
assert_exit "ledger-negative-tokens" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-negative-tokens.json"
assert_exit "ledger-duplicate-n" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-duplicate-n.json"
assert_exit "ledger-fake-commits-agent" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-fake-commits-agent.json"

# --- Pass-2 negatives: kind enum, fragment/correctness exclusivity, verification
#     shape + non-empty (zero-work class), absolute path INSIDE the root (isolates
#     the isabs guard from containment -- generated, since the value is the checkout path).
assert_exit "receipt-kind-unknown" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-kind-unknown.json" "$REPO_ROOT"
assert_exit "receipt-fragment-with-correctness" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-fragment-with-correctness.json" "$REPO_ROOT"
assert_exit "receipt-verification-empty" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-verification-empty.json" "$REPO_ROOT"
assert_exit "receipt-verification-garbage" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-verification-garbage.json" "$REPO_ROOT"
ABS_INSIDE_FILE="$TMP_WORKDIR/receipt-abs-inside.json"
python3 - "$FIXTURES/receipt-good.json" "$REPO_ROOT/README.md" "$ABS_INSIDE_FILE" <<'PY'
import json, sys
src, abs_path, dst = sys.argv[1:4]
d = json.load(open(src))
d["lenses"]["correctness"]["findings"][0]["file"] = abs_path
json.dump(d, open(dst, "w"))
PY
assert_exit "receipt-file-absolute-inside-root (generated)" 1 "$VALIDATOR" receipt "$ABS_INSIDE_FILE" "$REPO_ROOT"
# Degenerate root isolation: cite a file that DOES exist under "/" (etc/passwd,
# present on every POSIX system) so containment passes and ONLY the
# degenerate-root guard can produce the violation.
DEGENERATE_FILE="$TMP_WORKDIR/receipt-degenerate.json"
python3 - "$FIXTURES/receipt-good.json" "$DEGENERATE_FILE" <<'PY'
import json, sys
src, dst = sys.argv[1:3]
d = json.load(open(src))
d["lenses"]["correctness"]["findings"][0]["file"] = "etc/passwd"
json.dump(d, open(dst, "w"))
PY
assert_exit "receipt-degenerate-root (generated)" 1 "$VALIDATOR" receipt "$DEGENERATE_FILE" "/"
assert_exit "receipt-not-reverified-garbage" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-not-reverified-garbage.json" "$REPO_ROOT"
assert_exit "receipt-file-nul" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-file-nul.json" "$REPO_ROOT"
assert_exit "receipt-verification-reason-with-entries" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-verification-reason-with-entries.json" "$REPO_ROOT"
assert_exit "ledger-commits-garbage" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-commits-garbage.json"
assert_exit "receipt-fragment-with-omitted-reason" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-fragment-with-omitted-reason.json" "$REPO_ROOT"

# --- Exit-2 fixtures: anything that prevents validation from running at all
#     (REV-F-16, SEC-F-4) -- fixed-content fixtures plus one generated at test
#     time (a pathologically deep JSON that would otherwise crash with a raw
#     RecursionError traceback). Never confuse this with the exit-1 shape
#     violations above (REV-F-11: the runner must assert exit 2 explicitly). ---

assert_exit "receipt-not-utf8" 2 "$VALIDATOR" receipt "$FIXTURES/receipt-not-utf8.json" "$REPO_ROOT"
assert_exit "receipt-top-level-array" 2 "$VALIDATOR" receipt "$FIXTURES/receipt-top-level-array.json" "$REPO_ROOT"

DEEP_NESTING_FILE="$TMP_WORKDIR/deep-nesting.json"
python3 -c "open('$DEEP_NESTING_FILE', 'w').write('[' * 200000 + ']' * 200000)"
assert_exit "receipt-deep-nesting (generated)" 2 "$VALIDATOR" receipt "$DEEP_NESTING_FILE" "$REPO_ROOT"

# --- Generated containment negative: a symlink inside a throwaway fake
#     project root resolving OUTSIDE that root (SEC-F-2's third shape --
#     the fixed fixtures above cover absolute + traversal; a real symlink
#     needs a filesystem object built at test time, not a committed fixture). ---

FAKE_ROOT="$TMP_WORKDIR/fake-root"
OUTSIDE_ROOT="$TMP_WORKDIR/outside-root"
mkdir -p "$FAKE_ROOT" "$OUTSIDE_ROOT"
touch "$OUTSIDE_ROOT/secret.txt"
ln -s "$OUTSIDE_ROOT/secret.txt" "$FAKE_ROOT/escape-link"
cat > "$FAKE_ROOT/receipt.json" <<'EOF'
{
  "tier": 1,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-clear",
  "lenses": {
    "correctness": {
      "status": "findings",
      "findings": [
        { "id": "F-1", "severity": "MINOR", "confidence": "medium", "evidence": "read", "file": "escape-link", "line": 1, "claim": "symlink escapes the fake project root" }
      ]
    }
  },
  "verification": [{"command": "true", "exit_code": 0, "outcome": "pass"}]
}
EOF
assert_exit "receipt-symlink-escape (generated)" 1 "$VALIDATOR" receipt "$FAKE_ROOT/receipt.json" "$FAKE_ROOT"

# --- Known-positive fixtures LAST: each must exit 0. ---

assert_exit "receipt-good" 0 "$VALIDATOR" receipt "$FIXTURES/receipt-good.json" "$REPO_ROOT"
assert_exit "receipt-verification-omitted-with-reason" 0 "$VALIDATOR" receipt "$FIXTURES/receipt-verification-omitted-with-reason.json" "$REPO_ROOT"
assert_exit "receipt-security-fragment-good" 0 "$VALIDATOR" receipt "$FIXTURES/receipt-security-fragment-good.json" "$REPO_ROOT"
assert_exit "ledger-good" 0 "$VALIDATOR" ledger "$FIXTURES/ledger-good.json"

echo ""
if (( fail_count > 0 )); then
  echo "run-script-tests: $fail_count/$total fixture assertion(s) FAILED."
  exit 1
else
  echo "run-script-tests: all $total fixture assertions passed."
  exit 0
fi
