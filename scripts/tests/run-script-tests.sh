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
# FOURTH exception (ledger close.inline_closures[]): ledger-inline-closures-*.json
# fixtures cite scripts/tests/fixtures/receipt-findings-addressed-good.json as
# their receipt -- a sibling fixture, not README.md or a guaranteed-absent
# path -- because the inline_closures.receipt field must resolve to a real,
# parseable receipt JSON whose findings_addressed[].finding_id covers the
# entry's finding_ids; README.md would fail JSON-parse for reasons unrelated to
# the rule under test. Every negative ledger-inline-closures-*.json fixture
# still isolates to exactly one rule (calibration isolation) by keeping this
# sibling-fixture receipt reference valid except in the fixtures whose rule
# under test lives in the coverage comparison itself
# (ledger-inline-closures-{missing-receipt,id-not-covered,unhashable-id,receipt-not-string,
# id-not-string,receipt-not-object,receipt-not-json,receipt-not-json-ext}.json).
#
# FOURTH exception, extended (re-brief): two more citation classes reuse
# existing or new sibling fixtures where the rule under test IS the cited
# receipt's own shape -- ledger-inline-closures-receipt-not-object.json cites
# the already-existing receipt-top-level-array.json (a JSON array, not an
# object) and ledger-inline-closures-receipt-not-json.json cites the
# already-existing receipt-not-json.json (invalid JSON syntax), isolating the
# "cited receipt top-level must be object" and "cited receipt parse failure"
# rules respectively without inventing redundant fixtures. A THIRD new sibling,
# inline-closure-receipt-good.txt (a valid receipt-shaped JSON body, non-.json
# extension), isolates the ".json"-extension rule in
# ledger-inline-closures-receipt-not-json-ext.json -- it is a `.txt` file
# deliberately, since the rule under test IS the extension itself.
# receipt-findings-addressed-nfc-id.json is a further sibling (NFD-decomposed
# finding_id -- "e" + combining acute U+0301, not the precomposed U+00E9)
# isolating the Unicode-normalization rule in ledger-inline-closures-nfc-id.json.
#
# FIFTH exception (F-6 receipt-mode degenerate-root short-circuit,
# receipt-degenerate-root-single-violation.json): cites a guaranteed-absent
# path (domain/skills/does-not-exist-anywhere-degenerate.xyz) so that running
# it against a HEALTHY root produces a second (containment) violation, while
# the degenerate-root short-circuit keeps a degenerate-root run at exactly
# one violation -- the same distinguishing shape as the ledger-mode
# short-circuit fixture below (SEC F-5), mirrored on the receipt side (F-6).
#
# SIXTH exception (F-7 findings_addressed cross-check, and the new
# receipt-citation containment fixtures for close.inline_closures[].receipt):
# receipt-findings-addressed-unknown-id.json and
# -critical-id.json are full valid receipts whose findings_addressed[0]
# cites, respectively, an id absent from both lenses and a CRITICAL finding's
# id -- each isolates to exactly the one new F-7 violation it names.
# receipt-findings-addressed-nfc-composed-id.json is a further sibling, cited
# only from ledger-inline-closures-mixed-nfd-nfc.json (never receipt-validated
# directly): its finding_id is genuinely NFC-precomposed (U+00E9), pairing
# with that ledger fixture's NFD-decomposed (U+0301) id to exercise BOTH
# normalization call sites at once -- the pre-existing nfc-id pair below is
# NFD on both sides (byte-identical already), so it alone would still match
# even with normalization removed entirely; this mixed pair is what actually
# proves the normalization calls are load-bearing.
#
# SEVENTH exception (REV F-1/F-8/F-6, re-brief 1/2 -- close.inline_closures[].
# receipt containment, all THREE shapes now GENERATED at test time, no static
# fixture): the prior static fixtures cited a fixed, never-created
# /tmp path, so deleting _check_containment fell through to FileNotFoundError
# -- which still appends ONE violation, hiding the mutant the absolute and
# traversal assertions exist to catch (REV F-1 CRITICAL: "1/76 red" instead of
# 3/76). ESCAPE_TARGET (below) is a single covering receipt this runner writes
# once into TMP_WORKDIR (never a fixed/predictable path -- REV F-8) with a
# findings_addressed entry covering "F-1"; all three escape shapes cite THIS
# SAME file, generated as a ledger JSON via _build_inline_closure_ledger(): an
# absolute path to it (isabs guard), a REPO_ROOT-relative "../" chain reaching
# it (os.path.relpath, traversal guard), and a symlink named escape-link.json
# inside the throwaway FAKE_ROOT (built below for the receipt-mode symlink
# case and reused here) pointing at it (symlink-escape guard). Because the
# cited file genuinely exists, parses, and covers the closed id, deleting
# _check_containment now makes all three fall through to a clean exit 0 (0
# violations) -- the discriminating mutant REV F-1 asked for. No fixture ever
# lives under scripts/tests/fixtures/ for these three shapes, and no symlink
# is ever created inside the tracked fixtures directory (REV F-6): the ledger
# JSON bodies and the symlink both live under TMP_WORKDIR / FAKE_ROOT, cleaned
# up by the existing trap on TMP_WORKDIR alone -- no separate ESCAPE_LINK
# variable or cleanup step is needed anymore.
#
# EIGHTH exception (SEC F-1, REV F-7, re-brief 1/2 -- findings_addressed[]
# .finding_id and overrides[].finding_id/finding_ids[] type/identity
# cross-checks): receipt-findings-addressed-id-not-string.json cites a
# numeric (non-string) finding_id against a CRITICAL finding, isolating the
# tightened "must be a non-empty string" predicate (which now also rejects a
# truthy non-string id that used to dodge both the old "is required" check
# and the F-7 cross-check in one move). receipt-overrides-unknown-id.json
# cites an id absent from lenses.*.findings[].id via the singular
# overrides[].finding_id form, isolating the new SEC F-4 cross-check (which
# reuses the same known_findings map F-7 builds, and deliberately does not
# examine severity -- that is the protocol's own F-9 gate, not this
# validator's).
#
# NINTH exception (ledger `plan[]`, the Brief File's machine-checkable mirror
# of `## Plan`/`## Phases`): ledger-plan-*.json fixtures cite nothing on disk
# at all -- no new citation exception is needed, since every rule the `plan`
# field adds is a pure shape/arithmetic check over already-parsed JSON (no
# filesystem access). Each negative fixture is derived from ledger-good.json's
# ledger/close shape (a few extended to carry a second commit-step row and a
# second commit, so `plan`'s two-entry fixtures have enough commits to
# satisfy the at-Close count rule on their own) and isolates to exactly one
# rule: ledger-plan-not-list (plan not a list), ledger-plan-entry-not-object
# (an entry that is not an object), ledger-plan-n-gap (n skips a value),
# ledger-plan-n-not-int (n is the float 1.0 -- the one non-int shape the n-sequence rule alone cannot catch, so the strict-int guard is the sole rule that rejects it), ledger-plan-title-empty,
# ledger-plan-done-not-bool, ledger-plan-not-done-at-close (an entry not done
# when close is present) and ledger-plan-fewer-commits (fewer close.commits
# entries than plan entries -- the sole at-Close count rule; the orchestrator
# creates at least one commit per done plan entry, orchestrator-protocol.md
# -> "Commit creation"). ledger-plan-good and ledger-plan-null are the two
# positives -- plan absent/null validates as before, EXCEPT the unconditional
# close.commits >= 1 floor, which applies plan or no plan (D-D).
#
# TENTH exception (the Markdown container, receipt-md-*.md and
# ledger-inline-closures-receipt-md-good.md): the .md fixtures are report/Brief
# File shaped -- prose plus the object in one fenced ```json block -- so their
# JSON bodies keep the ordinary citation policy above (receipt-md-block-good.md
# and every other .md receipt cite README.md, a real tracked file). The
# exception is the CONTAINER citation itself:
# ledger-inline-closures-receipt-md-good.md cites the sibling fixture
# receipt-md-block-good.md as its close.inline_closures[0].receipt -- the same
# reasoning as the FOURTH exception (the cited path must resolve to a real,
# parseable receipt whose findings_addressed covers the closed id; README.md
# would fail for reasons unrelated to the rule under test), extended to the .md
# form the widened extension guard now accepts. That positive is also the
# assertion that pins the CITED-receipt loader's fence extraction itself: a
# cited-receipt loader still running raw json.loads (the pre-container code)
# turns it, and only it, red. Two further ledgers are GENERATED at test time
# (never static fixtures) citing receipt-md-no-block.md and
# receipt-md-two-blocks.md; those pin the FAILURE SHAPE of an unextractable
# cited container -- exit 1 with exactly one VIOLATION, never the exit-2
# catch-all -- and deliberately claim nothing about the extraction wiring,
# since a raw json.loads would also fail them by one JSON syntax error. A
# third generated case (receipt-md-unterminated-fence, written into
# TMP_WORKDIR for the same reason the SEVENTH exception generates its
# escapes: the fixture list is closed) covers the opened-but-never-closed
# fence arm, which no static fixture exercises. Each negative
# .md fixture isolates to exactly one rule (calibration isolation):
# receipt-md-no-block.md carries no fence of any label; wrong-fence-label.md
# carries only ```JSON / ```jsonc fences over valid bodies (label exactness,
# case sensitivity); two-blocks.md carries two blocks that are each a valid
# receipt on their own (uniqueness, never "first wins"/"last wins");
# malformed-block.md carries exactly one block whose body has a trailing comma
# (malformed block = the exit-1 class, not exit 2). receipt-md-prose-fence-
# string.md is a positive: the literal text ```json appears mid-sentence in its
# prose alongside one real block, pinning "a fence is a whole line".
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

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
# VALIDATOR_OVERRIDE lets a mutation probe point this suite at a scratchpad
# COPY of check-receipt.py without touching the repo file -- never set in
# normal use, where it defaults to the candidate validator in place.
VALIDATOR="${VALIDATOR_OVERRIDE:-$REPO_ROOT/domain/skills/_shared/scripts/check-receipt.py}"
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
  out="$(mktemp -p "$TMP_WORKDIR")"
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

# assert_violation_count -- like assert_exit, but additionally asserts the
# exact number of "VIOLATION " lines printed. Needed for the degenerate-root
# short-circuit rule (SEC F-5): assert_exit alone cannot distinguish "the
# short-circuit skipped close.inline_closures" from "it ran and happened to
# find nothing wrong" -- both exit 1 via the degenerate-root violation alone,
# but only the short-circuited run stays at exactly one VIOLATION line.
assert_violation_count() {
  local label="$1" expected_exit="$2" expected_count="$3"
  shift 3
  local out actual_exit=0 actual_count
  out="$(mktemp -p "$TMP_WORKDIR")"
  python3 "$@" >"$out" 2>&1 || actual_exit=$?
  actual_count="$(grep -c '^VIOLATION ' "$out" || true)"
  total=$((total + 1))
  if [[ "$actual_exit" -eq "$expected_exit" && "$actual_count" -eq "$expected_count" ]]; then
    echo "PASS: $label (exit $actual_exit, $actual_count violation(s), expected $expected_exit/$expected_count)"
  else
    echo "FAIL: $label (exit $actual_exit, $actual_count violation(s), expected $expected_exit/$expected_count)"
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

# --- F-6 receipt-mode degenerate-root SHORT-CIRCUIT (mirrors ledger mode's
#     own SEC F-5 short-circuit below): receipt-degenerate-root-single-
#     violation.json cites a guaranteed-absent file. Under a degenerate root
#     the per-finding containment probe never runs, so only the degenerate-
#     root violation itself is printed (count 1); under a healthy root the
#     probe DOES run and the guaranteed-absent citation fails it (still count
#     1, but a DIFFERENT violation) -- assert_violation_count pins both
#     shapes so a short-circuit that fired unconditionally (even under a
#     healthy root) or not at all (even under "/") would turn one of these
#     red. ---

assert_violation_count "receipt-degenerate-root-single-violation (degenerate root)" 1 1 "$VALIDATOR" receipt "$FIXTURES/receipt-degenerate-root-single-violation.json" "/"
assert_violation_count "receipt-degenerate-root-single-violation (healthy root)" 1 1 "$VALIDATOR" receipt "$FIXTURES/receipt-degenerate-root-single-violation.json" "$REPO_ROOT"

assert_exit "receipt-not-reverified-garbage" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-not-reverified-garbage.json" "$REPO_ROOT"
assert_exit "receipt-file-nul" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-file-nul.json" "$REPO_ROOT"
assert_exit "receipt-verification-reason-with-entries" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-verification-reason-with-entries.json" "$REPO_ROOT"
assert_exit "ledger-commits-garbage" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-commits-garbage.json"
assert_exit "receipt-fragment-with-omitted-reason" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-fragment-with-omitted-reason.json" "$REPO_ROOT"

# --- findings_addressed calibration (4 existing per-entry rules, each
#     isolated to one fixture): finding_id required, files non-empty list,
#     fix_evidence required, gate_results required -- plus the top-level
#     "must be a list" guard. Every fixture is otherwise a full valid receipt
#     (calibration isolation). ---

assert_exit "receipt-findings-addressed-not-list" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-findings-addressed-not-list.json" "$REPO_ROOT"
assert_exit "receipt-findings-addressed-no-id" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-findings-addressed-no-id.json" "$REPO_ROOT"
assert_exit "receipt-findings-addressed-empty-files" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-findings-addressed-empty-files.json" "$REPO_ROOT"
assert_exit "receipt-findings-addressed-no-evidence" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-findings-addressed-no-evidence.json" "$REPO_ROOT"
assert_exit "receipt-findings-addressed-no-gate" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-findings-addressed-no-gate.json" "$REPO_ROOT"

# --- F-7 findings_addressed[].finding_id cross-check (unconditional): the
#     cited id must resolve, after NFC normalization, against the union of
#     lenses.correctness/security findings[].id, and the resolved finding
#     must not be CRITICAL. Each fixture is otherwise a full valid receipt
#     isolating to exactly the one new violation. ---

assert_exit "receipt-findings-addressed-unknown-id" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-findings-addressed-unknown-id.json" "$REPO_ROOT"
assert_exit "receipt-findings-addressed-critical-id" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-findings-addressed-critical-id.json" "$REPO_ROOT"

# --- ledger close.inline_closures[] calibration (new field): not-a-list,
#     missing/unreadable receipt, finding_ids not covered by the cited
#     receipt's findings_addressed, empty finding_ids -- each isolated to one
#     fixture (calibration isolation, FOURTH citation-policy exception above). ---

assert_exit "ledger-inline-closures-not-list" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-not-list.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-missing-receipt" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-missing-receipt.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-id-not-covered" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-id-not-covered.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-empty-ids" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-empty-ids.json" "$REPO_ROOT"

# --- ledger close.inline_closures[] calibration, re-brief additions: the five
#     rules REV F-2 found surviving deletion (entry-must-be-object,
#     receipt-must-be-string, finding_ids[j]-must-be-string, cited-receipt-
#     top-level-must-be-object, cited-receipt-parse-failure), plus the
#     unhashable finding_ids element (REV F-1 / SEC F-4 -- must fail closed at
#     exit 1, never exit 2) and the .json extension check (REV F-5 / SEC F-2)
#     -- each isolated to one fixture (calibration isolation). ---

assert_exit "ledger-inline-closures-unhashable-id" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-unhashable-id.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-entry-not-object" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-entry-not-object.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-receipt-not-string" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-receipt-not-string.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-id-not-string" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-id-not-string.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-receipt-not-object" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-receipt-not-object.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-receipt-not-json" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-receipt-not-json.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-receipt-not-json-ext" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-receipt-not-json-ext.json" "$REPO_ROOT"

# --- ledger mode's own degenerate-root guard, isolated: ledger-good.json (no
#     inline_closures at all) is otherwise a fully valid ledger sidecar, so
#     the ONLY violation a "/" project_root can produce here is the
#     degenerate-root rule itself (mirrors receipt-degenerate-root above,
#     generated inline there because it needs a throwaway file under "/";
#     here the existing positive fixture already carries no inline_closures,
#     so no new fixture file is needed). ---

assert_exit "ledger-degenerate-root" 1 "$VALIDATOR" ledger "$FIXTURES/ledger-good.json" "/"

# --- degenerate-root SHORT-CIRCUIT (SEC F-5, re-brief): ledger-inline-closures-
#     good.json's inline_closures entry is fully valid, so a naive
#     "record the violation but keep going" implementation would ALSO run
#     _check_inline_closures against the degenerate root "/" and append a
#     second (spurious, filesystem-touching) violation. assert_exit alone
#     cannot detect that regression -- both exit 1 either way -- so this uses
#     assert_violation_count to pin the count at exactly 1. ---

assert_violation_count "ledger-inline-closures-good-degenerate-root-short-circuit" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-good.json" "/"

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

# --- F-6-style containment on close.inline_closures[].receipt itself (the
#     citation slot, not the cited receipt's own content): absolute path,
#     relative traversal, and a real symlink each escape project_root and
#     must fail the SAME containment guard as receipt-mode file citations.
#     REV F-1/F-8 (re-brief): all three cite ESCAPE_TARGET, a single covering
#     receipt this runner writes into TMP_WORKDIR (never a fixed/predictable
#     path) with a findings_addressed entry that covers "F-1" -- so a
#     mutant that deletes _check_containment makes all three fall through to
#     a REAL, parseable, covering receipt (0 violations, red) rather than a
#     FileNotFoundError that would still (wrongly) count as 1 violation and
#     hide the mutant. The symlink case reuses FAKE_ROOT (built above for the
#     receipt-mode symlink test) rather than the tracked fixtures/ directory
#     (REV F-6) -- no symlink is ever created outside TMP_WORKDIR. Each ledger
#     body is generated at test time (SEVENTH exception above), never a
#     static fixture; each fails by exactly one rule (calibration isolation);
#     assert_violation_count pins the count at 1. ---

ESCAPE_TARGET="$TMP_WORKDIR/escape-target.json"
cat > "$ESCAPE_TARGET" <<'EOF'
{"findings_addressed": [{"finding_id": "F-1"}]}
EOF

_build_inline_closure_ledger() {
  # $1 = the close.inline_closures[0].receipt citation to embed, $2 = destination path.
  python3 - "$1" "$2" <<'PY'
import json, sys
receipt, dst = sys.argv[1:3]
ledger = {
    "ledger": [
        {"n": 1, "agent": "organic-implementer", "model": "sonnet", "tokens": 50000, "tool_uses": 12, "duration_s": 300, "outcome": "ok"},
        {"n": 2, "agent": "organic-reviewer", "model": "opus", "tokens": 30000, "tool_uses": 8, "duration_s": 200, "outcome": "review-clear"},
        {"n": 3, "agent": "commit-step", "model": "sonnet", "tokens": 5000, "tool_uses": 3, "duration_s": 60, "outcome": "ok"},
    ],
    "close": {
        "delegations": 3,
        "subagent_tokens": 85000,
        "commits": ["a1b2c3d"],
        "re_briefs": 0,
        "inline_closures": [{"receipt": receipt, "finding_ids": ["F-1"]}],
    },
}
json.dump(ledger, open(dst, "w"))
PY
}

ABSOLUTE_LEDGER="$TMP_WORKDIR/ledger-inline-closures-receipt-absolute.json"
_build_inline_closure_ledger "$ESCAPE_TARGET" "$ABSOLUTE_LEDGER"
assert_violation_count "ledger-inline-closures-receipt-absolute (generated)" 1 1 "$VALIDATOR" ledger "$ABSOLUTE_LEDGER" "$REPO_ROOT"

TRAVERSAL_RECEIPT_REL="$(python3 -c "import os, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$ESCAPE_TARGET" "$REPO_ROOT")"
TRAVERSAL_LEDGER="$TMP_WORKDIR/ledger-inline-closures-receipt-traversal.json"
_build_inline_closure_ledger "$TRAVERSAL_RECEIPT_REL" "$TRAVERSAL_LEDGER"
assert_violation_count "ledger-inline-closures-receipt-traversal (generated)" 1 1 "$VALIDATOR" ledger "$TRAVERSAL_LEDGER" "$REPO_ROOT"

ln -sf "$ESCAPE_TARGET" "$FAKE_ROOT/escape-link.json"
SYMLINK_LEDGER="$TMP_WORKDIR/ledger-inline-closures-receipt-symlink.json"
_build_inline_closure_ledger "escape-link.json" "$SYMLINK_LEDGER"
assert_violation_count "ledger-inline-closures-receipt-symlink (generated)" 1 1 "$VALIDATOR" ledger "$SYMLINK_LEDGER" "$FAKE_ROOT"

# --- Markdown container, CITED-receipt loader FAIL-CLOSED shape (TENTH
#     exception above): each generated ledger cites a real, contained .md
#     receipt that deliberately cannot be extracted (no block / two blocks),
#     with a valid finding_ids list so the ONLY thing that can fail is the load
#     (calibration isolation). What these two pin is the FAILURE SHAPE: an
#     unextractable cited container stays exit 1 with exactly one VIOLATION and
#     never escalates to the exit-2 catch-all. They do NOT discriminate whether
#     the cited-receipt loader extracts fences at all -- a loader that ran raw
#     json.loads over the markdown would still produce one violation here (a
#     JSON syntax error) and keep both green. The assertion that DOES pin the
#     wiring is the positive ledger-inline-closures-receipt-md-good below:
#     under a raw-json.loads cited-receipt loader it is the one that turns red. ---

MD_NO_BLOCK_LEDGER="$TMP_WORKDIR/ledger-inline-closures-receipt-md-no-block.json"
_build_inline_closure_ledger "scripts/tests/fixtures/receipt-md-no-block.md" "$MD_NO_BLOCK_LEDGER"
assert_violation_count "ledger-inline-closures-receipt-md-no-block (generated)" 1 1 "$VALIDATOR" ledger "$MD_NO_BLOCK_LEDGER" "$REPO_ROOT"

MD_TWO_BLOCKS_LEDGER="$TMP_WORKDIR/ledger-inline-closures-receipt-md-two-blocks.json"
_build_inline_closure_ledger "scripts/tests/fixtures/receipt-md-two-blocks.md" "$MD_TWO_BLOCKS_LEDGER"
assert_violation_count "ledger-inline-closures-receipt-md-two-blocks (generated)" 1 1 "$VALIDATOR" ledger "$MD_TWO_BLOCKS_LEDGER" "$REPO_ROOT"

# --- REV F-5 (re-brief): the os.path.isabs arm of findings[].file is a pure
#     string check and must keep running under a degenerate root, unlike the
#     filesystem-touching containment probe it used to live inside of --
#     /etc/passwd under project_root "/" must print BOTH the degenerate-root
#     violation AND the absolute-path violation (2 total), never just the
#     one. No static fixture exists for this combination anywhere above
#     (receipt-degenerate-root-single-violation.json cites a RELATIVE path,
#     so isabs never fires there), so this is generated here to give the
#     rule its own assertion. ---

DEGENERATE_ABS_FILE="$TMP_WORKDIR/receipt-degenerate-abs.json"
python3 - "$FIXTURES/receipt-good.json" "$DEGENERATE_ABS_FILE" <<'PY'
import json, sys
src, dst = sys.argv[1:3]
d = json.load(open(src))
d["lenses"]["correctness"]["findings"][0]["file"] = "/etc/passwd"
json.dump(d, open(dst, "w"))
PY
assert_violation_count "receipt-degenerate-root-absolute-file-still-checked (generated)" 1 2 "$VALIDATOR" receipt "$DEGENERATE_ABS_FILE" "/"

# --- SEC F-1 / REV F-4 findings_addressed[].finding_id predicate tightening,
#     and SEC F-4 overrides[].finding_id cross-check (re-brief additions):
#     each isolated to one fixture (calibration isolation, EIGHTH exception
#     above). ---

assert_exit "receipt-findings-addressed-id-not-string" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-findings-addressed-id-not-string.json" "$REPO_ROOT"
assert_exit "receipt-overrides-unknown-id" 1 "$VALIDATOR" receipt "$FIXTURES/receipt-overrides-unknown-id.json" "$REPO_ROOT"

# --- ledger `plan[]` calibration (NINTH exception above): each negative
#     fixture isolates to exactly one rule -- assert_violation_count pins both
#     the exit code and the single VIOLATION line, proving calibration
#     isolation the same way the degenerate-root short-circuit assertions do. ---

assert_violation_count "ledger-plan-not-list" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-not-list.json" "$REPO_ROOT"
assert_violation_count "ledger-plan-entry-not-object" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-entry-not-object.json" "$REPO_ROOT"
assert_violation_count "ledger-plan-n-gap" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-n-gap.json" "$REPO_ROOT"
assert_violation_count "ledger-plan-n-not-int" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-n-not-int.json" "$REPO_ROOT"
assert_violation_count "ledger-plan-title-empty" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-title-empty.json" "$REPO_ROOT"
assert_violation_count "ledger-plan-done-not-bool" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-done-not-bool.json" "$REPO_ROOT"
assert_violation_count "ledger-plan-not-done-at-close" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-not-done-at-close.json" "$REPO_ROOT"
assert_violation_count "ledger-plan-fewer-commits" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-fewer-commits.json" "$REPO_ROOT"

# --- close.commits unconditional >= 1 floor (RG-1, tier-2 security F-1,
#     re-brief 2/2): the plan-based rule above (close.commits >= len(plan))
#     only fires when plan is a populated list, so it alone never catches a
#     Close recorded with zero commits when plan is absent, null, or an empty
#     list. Each fixture isolates to exactly the one new floor violation
#     (calibration isolation, same assert_violation_count pattern as the
#     ledger-plan-* block above) across the three plan shapes the finding
#     named: absent, explicit null, and an empty list. ---

assert_violation_count "ledger-close-zero-commits-no-plan" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-close-zero-commits-no-plan.json" "$REPO_ROOT"
assert_violation_count "ledger-close-zero-commits-plan-null" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-close-zero-commits-plan-null.json" "$REPO_ROOT"
assert_violation_count "ledger-close-zero-commits-plan-empty" 1 1 "$VALIDATOR" ledger "$FIXTURES/ledger-close-zero-commits-plan-empty.json" "$REPO_ROOT"

# --- Markdown container, CLI-argument loader (TENTH exception above): each
#     negative isolates to exactly one container rule, so assert_violation_count
#     pins the single VIOLATION line as well as the exit code. The malformed
#     block asserts exit 1, NOT exit 2 -- a container whose block is bad is
#     structurally invalid, the same class as a malformed legacy .json. ---

assert_violation_count "receipt-md-no-block" 1 1 "$VALIDATOR" receipt "$FIXTURES/receipt-md-no-block.md" "$REPO_ROOT"
assert_violation_count "receipt-md-two-blocks" 1 1 "$VALIDATOR" receipt "$FIXTURES/receipt-md-two-blocks.md" "$REPO_ROOT"
assert_violation_count "receipt-md-malformed-block" 1 1 "$VALIDATOR" receipt "$FIXTURES/receipt-md-malformed-block.md" "$REPO_ROOT"
assert_violation_count "receipt-md-wrong-fence-label" 1 1 "$VALIDATOR" receipt "$FIXTURES/receipt-md-wrong-fence-label.md" "$REPO_ROOT"

# The fourth container arm -- a fence opened and never closed -- is GENERATED
# here rather than committed as a fixture (TENTH exception above): it is a
# two-line file whose whole point is the missing closing fence, and a static
# fixture of a deliberately unterminated code fence is a trap for every tool
# that renders this directory. Without this assertion the rule would ship
# never having been observed red (Rule 7).
UNTERMINATED_MD="$TMP_WORKDIR/receipt-md-unterminated-fence.md"
printf '# Report\n\n## Receipt\n\n```json\n{"tier": 1}\n' > "$UNTERMINATED_MD"
assert_violation_count "receipt-md-unterminated-fence (generated)" 1 1 "$VALIDATOR" receipt "$UNTERMINATED_MD" "$REPO_ROOT"

# --- Known-positive fixtures LAST: each must exit 0. ---

assert_exit "receipt-good" 0 "$VALIDATOR" receipt "$FIXTURES/receipt-good.json" "$REPO_ROOT"
assert_exit "receipt-verification-omitted-with-reason" 0 "$VALIDATOR" receipt "$FIXTURES/receipt-verification-omitted-with-reason.json" "$REPO_ROOT"
assert_exit "receipt-security-fragment-good" 0 "$VALIDATOR" receipt "$FIXTURES/receipt-security-fragment-good.json" "$REPO_ROOT"
assert_exit "ledger-good" 0 "$VALIDATOR" ledger "$FIXTURES/ledger-good.json"
assert_exit "receipt-findings-addressed-good" 0 "$VALIDATOR" receipt "$FIXTURES/receipt-findings-addressed-good.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-good" 0 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-good.json" "$REPO_ROOT"

# --- ledger close.inline_closures[] calibration, re-brief positives:
#     null-tolerance (REV F-7 -- inline_closures: null mirrors
#     findings_addressed's own null-tolerance) and Unicode NFC coverage
#     matching (REV F-4 -- both the ledger id and the cited receipt's id are
#     NFD-decomposed and already byte-identical, so this pair alone would
#     still match even with normalization removed entirely; see D-3 below for
#     the pair that actually requires normalizing both sides). ---

assert_exit "ledger-inline-closures-nfc-id" 0 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-nfc-id.json" "$REPO_ROOT"
assert_exit "ledger-inline-closures-null" 0 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-null.json" "$REPO_ROOT"

# --- D-3: a genuinely MIXED pair -- ledger-inline-closures-mixed-nfd-nfc.json
#     carries its finding_id NFD-decomposed, receipt-findings-addressed-
#     nfc-composed-id.json's matching finding_id is genuinely NFC-precomposed
#     -- byte-different on both sides, so this is the pair that actually
#     exercises both unicodedata.normalize("NFC", ...) call sites in
#     _check_inline_closures (the pre-existing nfc-id pair above does not,
#     since it is NFD/NFD and already byte-identical). ---

assert_exit "ledger-inline-closures-mixed-nfd-nfc" 0 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-mixed-nfd-nfc.json" "$REPO_ROOT"

# --- ledger `plan[]` positives: plan absent OR explicit null validates as
#     before, EXCEPT the unconditional close.commits >= 1 floor (plan or no
#     plan); ledger-plan-good.json is a fully populated, all-done plan
#     consistent with its ledger/close rows. ---

assert_exit "ledger-plan-good" 0 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-good.json" "$REPO_ROOT"
assert_exit "ledger-plan-null" 0 "$VALIDATOR" ledger "$FIXTURES/ledger-plan-null.json" "$REPO_ROOT"

# --- Markdown container positives (TENTH exception above): a report-shaped
#     receipt whose single fenced ```json block is a full valid receipt; the
#     same, with the literal text ```json also present mid-sentence in the
#     prose (a fence is a whole line, never a substring); and a .md LEDGER
#     citing a .md RECEIPT, which exercises the widened
#     close.inline_closures[].receipt extension guard and the cited-receipt
#     loader's own fence extraction in one run. ---

assert_exit "receipt-md-block-good" 0 "$VALIDATOR" receipt "$FIXTURES/receipt-md-block-good.md" "$REPO_ROOT"
assert_exit "receipt-md-prose-fence-string" 0 "$VALIDATOR" receipt "$FIXTURES/receipt-md-prose-fence-string.md" "$REPO_ROOT"
assert_exit "ledger-inline-closures-receipt-md-good" 0 "$VALIDATOR" ledger "$FIXTURES/ledger-inline-closures-receipt-md-good.md" "$REPO_ROOT"

echo ""
if (( fail_count > 0 )); then
  echo "run-script-tests: $fail_count/$total fixture assertion(s) FAILED."
  exit 1
else
  echo "run-script-tests: all $total fixture assertions passed."
  exit 0
fi
