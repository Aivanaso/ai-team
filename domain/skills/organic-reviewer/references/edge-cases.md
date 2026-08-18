# Edge Cases — organic-reviewer

> Handling for non-happy-path situations. Load when an unexpected condition arises.

## No Candidate Changes to Review

**Condition:** `group_files` is empty, or none of the declared files exist on disk (and
`git diff HEAD -- <group_files>` also shows no changes to tracked files).

**Behavior:** Return `status: ok`, `verdict: review-clear`, `lenses.correctness.findings: []`.
Note in executive summary: "no candidate changes to review — gate passes with no findings".
Set `suppressed_count: 0`.

Rationale: an empty change set is a valid state (e.g., the Task Brief declared a file the
implementer did not need to touch). The gate must not block on a clean slate.

## All Findings Below 80% Confidence

**Condition:** Every finding identified across the five correctness lenses has confidence
≤ 80%.

**Behavior:** Suppress all findings. Return `status: ok`, `verdict: review-clear`,
`lenses.correctness.findings: []`. Set `suppressed_count` to the total suppressed. Note:
"All {N} candidate findings suppressed — confidence below threshold."

## Missing group_files (not injectable)

**Condition:** `group_files` is absent from injected context.

**Behavior:** Return `status: blocked`, executive summary names the missing field. Do NOT
widen scope to "all changed files" — reviewing outside the declared candidate produces
findings the orchestrator cannot route back to the Task Brief.

## Large File Set (read budget)

**Condition:** The union of `group_files` contains more files than fit one context window
alongside 1-hop callers.

**Behavior:** Read files in the order `group_files` lists them; prioritise CREATE over MODIFY
(new code is more likely to carry defects). Note in the report's Scope section: "read budget
reached after {N}/{total} files; {M} files not reviewed". Return the partial verdict;
`suppressed_count` stays 0 for unreviewed files (not reviewed, not suppressed).

## Verification Check Cannot Be Re-Run

**Condition:** A declared `acceptance_checks` command, a `config.yaml`-declared build/lint
command, or a `review_gates` entry cannot be executed in this environment (missing runner, no
network, sandboxed tool).

**Behavior:** Omit that command from `verification` — never fabricate `pass` or `fail` for a
command that did not run. Note the gap in `risks`: "verification check '{command}' could not
be re-run in this environment" (for an unrunnable `review_gates` entry, name the gate:
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

## Compilation/Lint Passes But Code Is Wrong

Passing verification does not mean correct. A service that returns an empty array instead of
querying the database will pass a shallow test.

- Verification (Execution Step 4) and correctness (Execution Step 3) are independent checks.
- Code that verifies clean but does not implement the objective: `verification` shows
  `outcome: pass`, `lenses.correctness` still carries the CRITICAL finding.
- The overall verdict reflects both — a clean verification list never substitutes for the
  correctness lenses.
