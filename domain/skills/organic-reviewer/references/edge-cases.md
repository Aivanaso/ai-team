# Edge Cases — organic-reviewer

> Handling for non-happy-path situations. Load when an unexpected condition arises.

## No Candidate Changes to Review

**Condition:** `group_files` is empty, or none of the declared files exist on disk (and
`git diff HEAD -- <group_files>` also shows no changes to tracked files).

**Behavior:** Return `status: ok`, `verdict: review-clear`, `lenses.correctness.findings: []`,
`verification: []` WITH `verification_omitted_reason: "no candidate changes to review"` — the
receipt gate (`ai-team receipt check`, run against the report itself) rejects an empty `verification`
that carries no reason. Note in executive summary: "no candidate changes to review — gate passes
with no findings".

Rationale: an empty change set is a valid state (e.g., the phase declared a file the
implementer did not need to touch). The gate must not block on a clean slate.

## All Findings Low-Confidence

**Condition:** Every finding identified across the five correctness lenses carries
`confidence: low`.

**Behavior:** Record every one of them — coverage never filters by confidence (Hard Rules).
The verdict follows the standard iff unchanged: `review-blocked` if any of them is CRITICAL,
`review-clear` otherwise, regardless of confidence. Note in executive summary: "All {N}
findings reported at low confidence — none suppressed; verdict follows the standard iff."
Nothing is hidden from the orchestrator: low confidence is visible per-finding for its own
triage.

**Evidence axis vs. confidence axis — precedence.** These are two independent axes; do not
conflate low confidence with `evidence: read`. The evidence cap applies at emission, before the
verdict is computed: a `read` finding without a named `trigger` is emitted at MINOR as maximum.
The confidence rule then applies unchanged to the severity actually emitted — low confidence
never downgrades an emitted severity, and a CRITICAL at any confidence still blocks.
Consequently a CRITICAL or MAJOR with `evidence: read` always carries a `trigger`. A finding can
be simultaneously `confidence: low` and `evidence: executed` (an uncertain interpretation of a
demonstrated result) — that finding's severity is never capped by the evidence rule, only by
whatever the lens itself judges the defect to warrant.

## Missing group_files (not injectable)

**Condition:** `group_files` is absent from injected context.

**Behavior:** Return `status: blocked`, executive summary names the missing field. Do NOT
widen scope to "all changed files" — reviewing outside the declared candidate produces
findings the orchestrator cannot route back to the phase.

## Large File Set (read budget)

**Condition:** The union of `group_files` contains more files than fit one context window
alongside 1-hop callers.

**Behavior:** Read files in the order `group_files` lists them; prioritise CREATE over MODIFY
(new code is more likely to carry defects). Note in the report's Scope section: "read budget
reached after {N}/{total} files; {M} files not reviewed". Return the partial verdict; unreviewed
files produce no findings at all (they were never read) — the Scope section's read-budget note
is the only trace of the gap, not a finding count.

## Verification Check Cannot Be Re-Run

**Condition:** A declared `acceptance_checks` command, a `config.yaml`-declared build/lint
command, or a `review_gates` entry cannot be executed in this environment (missing runner, no
network, sandboxed tool).

**Behavior:** Omit that command from `verification` — never fabricate `pass` or `fail` for a
command that did not run. If EVERY declared check is unrunnable and `verification` is left empty,
set `verification_omitted_reason: "every declared check unrunnable in this environment"` — the
receipt gate rejects an unexplained empty list. Note the gap in `risks`: "verification check
'{command}' could not be re-run in this environment" (for an unrunnable `review_gates` entry, name the gate:
"review gate '{name}' ('{command}') could not be re-run in this environment"). This does not
by itself block the verdict (the correctness lenses still resolve normally); it does mean the
receipt's verification evidence is partial — record that plainly rather than padding the list.

## Failing Non-Blocking Gate

**Condition:** A `review_gates` entry with `blocking: false` exits non-zero.

**Behavior:** The command still runs and its outcome is recorded in `verification` (`outcome:
fail`, `gate: "<name>"`) — objective evidence, never suppressed. Also record a MAJOR finding in
`lenses.correctness.findings[]`, `file`/`line` citing the gate's declaring entry in
`.ai-team/config.yaml` — the same container and citation shape as the blocking case (Decision
Gates), just a lower severity. This finding alone never sets `verdict: review-blocked`
(Decision Gates: verdict is `review-blocked` iff ≥ 1 CRITICAL finding exists). When no CRITICAL
finding exists elsewhere in the run, the verdict stays `review-clear`; the failure is
documented, not blocking.

## Verification Discrepancy

**Condition:** A re-run command's outcome contradicts the implementer's `check_results` for
the same command (the implementer reported `pass`, the re-run shows `fail`, or vice versa).

**Behavior:** Record a CRITICAL correctness finding citing the command, both outcomes, and —
when the failure surfaces a stack trace or assertion message — the `file:line` it points to.
This is a discrepancy in verified behavior, not a style disagreement; never reconcile it
silently (Decision Gates).

## Prior Report Unreadable or Delta Scope Absent

**Condition:** `prior_report` is injected but cannot be read on disk (missing, moved, permission
error), or no `delta_scope` accompanies it, or `delta_scope.findings_to_verify` is an empty
list.

**Behavior:** Return `status: blocked`, `failure_class: review`, naming the unreachable path or
the missing field. Do NOT fall back to a bounded pass with an empty closure list — a `verdict:
review-clear` derived from no prior evidence at all is worse than blocking (Decision Gates). An
empty `findings_to_verify` list is invalid input, not "nothing to verify".

## Delta Scope Exceeded By The Actual Diff

**Condition:** In DELTA MODE, the actual changed set (`git -C {project_root} diff HEAD
--name-only`) contains a path outside `delta_scope.changed_files` and the prior report's Scope
section (Execution Step 2).

**Behavior:** Do NOT silently review the wider diff. Record a CRITICAL correctness finding
citing the out-of-scope path, `claim`: "delta scope exceeded — full pass required" — the
standard `verdict` iff (`SKILL.md` → Hard Rules) then resolves to `review-blocked` with no
special case. This CRITICAL finding is itself the "Delta Pass Files a CRITICAL" case below — the
orchestrator routes it to a full re-review on the whole candidate, never a further chained delta
pass.

## Delta Pass Files a CRITICAL

**Condition:** A DELTA MODE pass (Execution Step 2) itself finds ≥ 1 CRITICAL finding — either
a named finding that is still open, or a new inconsistency introduced by the fix.

**Behaviour:** Set `verdict: review-blocked` as normal (Decision Gates). Do NOT chain a further
delta pass for the same objective's finding set — a delta pass finding a CRITICAL is itself the
full-re-review trigger (`_shared/cards/review.md`; a non-decreasing finding count reopens the design — Delta
re-validation). Note this in the executive summary and in `risks`: "delta pass found a CRITICAL
— escalate to a full re-review, not a further delta." The orchestrator re-engages
`organic-implementer`, then delegates a full pass (no `prior_report` injected) rather than
another DELTA MODE run.

## Compilation/Lint Passes But Code Is Wrong

Passing verification does not mean correct. A service that returns an empty array instead of
querying the database will pass a shallow test.

- Verification (Execution Step 5) and correctness (Execution Step 4) are independent checks.
- Code that verifies clean but does not implement the objective: `verification` shows
  `outcome: pass`, `lenses.correctness` still carries the CRITICAL finding.
- The overall verdict reflects both — a clean verification list never substitutes for the
  correctness lenses.
