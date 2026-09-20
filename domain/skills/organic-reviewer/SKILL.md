---
name: organic-reviewer
description: "Trigger: orchestrator invokes after an implementer attempt settled ok/warning at tier>=1 (ticket reviewer). Conformity + correctness + verification gate; the report's json block is the Review Receipt."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches the reviewer on a phase candidate at tier ≥ 1. Inputs: the
`design` (the approved design file, or `none` for a bounded task), the `phase_file`, the exact
candidate (`group_files`), `tier`, `tier_reason`, `attempt`, the implementer's `check_results`
and `decisions_taken`, and `report_destination`. Three lenses: **conformity** — every decision
of the design and every scenario of the phase is met, nothing the phase asked for is missing,
nothing it did not ask for was added; **correctness** — business logic, state transitions,
concurrency, resource lifecycle, error handling; **verification** — the declared checks re-run
by you. The product is ONE report at `report_destination` whose final fenced ```json block is
the Review Receipt; the machine validates that block when the orchestrator settles your
ticket, and a violating report keeps the ticket open until a clean relaunch. From attempt 2 the pass is a
DELTA: `prior_report` and `delta_scope` are injected and you verify the named findings closed,
the changed files for new inconsistencies, and the checks; the prior pass's clean lenses stand.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority, English — see `_shared/common-rules.md`.
- Conformity is a lens with findings: a decision not honored is a MAJOR (CRITICAL when the phase's objective depends on it), a scenario undemonstrated is a MAJOR, an addition outside the phase's files or objective is a MINOR naming the file. Each cites the decision or scenario text and the `file:line`. -- because the design is what the user approved; a candidate that drifts from it passed no review.
- Verification: re-run every acceptance check of the phase file verbatim, plus `config.yaml` `review_gates` and declared build/lint commands the checks do not cover; capture command, exit code, pass/fail from this pass's own run. A zero-work result is `outcome: fail` with the nature named in `risks` (`_shared/evidence-protocol.md` Rule 7).
- A re-run that contradicts the implementer's claimed `check_results` is a CRITICAL correctness finding. Absent `check_results`, note in `risks` that the reconciliation could not run.
- Read the FULL content of every file in `group_files`; `git -C {project_root} diff HEAD -- <group_files>` is a pointer to what changed; the scope is `group_files` (the diff misses untracked files).
- Every finding cites `file:line` (Rule 1); an uncited candidate is dropped and its topic named in `risks`.
- Report every finding, uncertain or minor included, each with `confidence`, `severity`, `evidence: executed | read` and, when `read` and MAJOR/CRITICAL, a `trigger`. A `read` finding without a trigger is emitted MINOR at most; severity follows the evidence, and confidence travels beside it. -- because coverage is the contract; the orchestrator's triage is the filter.
- Security findings belong to `organic-security`'s report. At tier 2 the machine combines both reports at commit-check.
- Verdict: `review-blocked` iff ≥ 1 CRITICAL in this receipt's `lenses.correctness`; else `review-clear`.
- A `decisions_taken` entry contradicting a constraint is a MAJOR `read` finding whose trigger cites both texts; a behavioral decision visible in the diff that `decisions_taken` does not declare is a MINOR (MAJOR when it contradicts a constraint).
- TDD evidence audit when `strict_tdd` is injected: a cycle naming an absent test, a zero-work or reason-less red digest, an uncovered behavior, or a missing `tdd_cycles`/`tdd_not_applicable` is a MAJOR `read` finding with the cycle as trigger; the OPTIONAL mutation probe (break the covered change in place, re-run the test, restore the file and confirm the restore with `cmp` or a hash; still green → CRITICAL `executed`) stays optional and stays inside the pass. You run alone on this tree, and the machine compares it at settle with the tree the implementer left (`_shared/common-rules.md` → Mutation probe).
- Receipt self-validation, every pass: `skills/_shared/scripts/ai-team receipt check {report_destination} .` before returning; fix every printed VIOLATION; record command, exit code and fixes in `## Receipt Self-Validation`.
- One report, one block: every other JSON excerpt in the report is fenced ```text.
- Git is for inspection only (`diff`, `log`, `show`, `status`); the tree you settle on is the tree you were given. Rulings are the orchestrator's and live in the task JSON, so the receipt carries no `overrides` field.
- Framework-agnostic: languages, frameworks and test runners appear only inside `# e.g.` enumerations.

## Decision Gates

| Condition | Action |
|---|---|
| Missing `project_root`, `phase_file`, `group_files`, `tier`, `tier_reason`, `attempt` or `report_destination` | `status: blocked`, `failure_class: null`, name the fields for the orchestrator to inject. |
| `phase_file` or the injected `design` unreadable | `status: blocked`, `failure_class: review`, cite the path — conformity cannot be checked against a missing contract. |
| `attempt` ≥ 2 AND `prior_report: none` injected (the machine found no earlier reviewer report for this phase: the earlier attempt settled before reaching review) | Full pass (Execution Steps 3–7), no `verdict_history`. |
| `attempt` ≥ 2 AND `prior_report` names a path AND (the path is unreadable OR `delta_scope` absent OR `findings_to_verify` empty OR `prior_verdict_history` empty) | `status: blocked`, `failure_class: review`, name the gap — a delta pass needs the real prior scope, so the orchestrator re-injects it. |
| `attempt` ≥ 2 with a valid delta scope | DELTA MODE (Execution Step 2). |
| DELTA MODE AND `git -C {project_root} diff HEAD --name-only` contains a path outside `delta_scope.changed_files` and the prior report's Scope | CRITICAL correctness finding "delta scope exceeded — full pass required"; verdict follows. |
| A `group_files` file cannot be read (permission, escapes `project_root`, git fails) | `status: blocked`, `failure_class: review`. |
| `group_files` empty, or nothing changed | `status: ok`, `verdict: review-clear`, `verification: []` with `verification_omitted_reason: "no candidate changes to review"`. |
| A declared check cannot run at all (missing tool) | omit it from `verification`, note in `risks`; if every check is unrunnable, `verification_omitted_reason` says so. |
| A check ran and returned a zero-work result | `verification` row with `outcome: fail`; the nature in `risks`. |
| ≥ 1 CRITICAL finding | `verdict: review-blocked`. |
| 0 CRITICAL | `verdict: review-clear`. |

## Execution Steps

1. Read `_shared/context-protocol.md` and `_shared/persistence-contract.md`. Validate the injected context (Decision Gates). Report `context_resolution`.
2. Attempt ≥ 2: read `prior_report`; verify the actual changed set against `delta_scope.changed_files` (Decision Gates); run the bounded pass — each `findings_to_verify` id closed with citation (into `closed: [{id, file, line}]`) or re-listed under `findings` when still open, the changed files for new inconsistencies, the checks — and compose the "not re-verified" list. `settle` refuses a receipt that drops a prior MAJOR/CRITICAL without one of the two (`_shared/machine.md`). Otherwise the full pass below.
3. Read the design (`## Decisions`, `## Security`, `## Out of scope`) and the phase file (objective, constraints, scenarios, expected files). Resolve `group_files`; read each file in full; `git diff HEAD -- <group_files>` as a pointer; up to 10 1-hop callers.
4. Conformity lens: decision by decision, scenario by scenario, file by file (declared vs touched). Then the five correctness lenses on the full contents in scope. `decisions_taken` and `tdd_cycles` are the first surfaces read — the candidate's own declared judgment calls.
5. Verification: every acceptance check verbatim, every `review_gates` entry, the uncovered build/lint commands. Compare with the claimed `check_results`.
6. Compute the verdict. Compose the receipt: `tier`, `tier_reason`, `verdict`, `lenses.correctness`, `verification`; DELTA MODE adds `verdict_history` (the injected chain plus exactly one entry — this pass), `not_reverified`, and `closed` (every prior MAJOR/CRITICAL this pass verified closed, with a citation; a prior MAJOR/CRITICAL neither closed nor re-listed under `findings` fails `settle`'s reconciliation).
7. Write the report at `report_destination` per [references/report-format.md](references/report-format.md) (Delta Report Variant in DELTA MODE): Conformity · Findings · Verification · Receipt Self-Validation · `## Receipt` with the single ```json block. Run `skills/_shared/scripts/ai-team receipt check {report_destination} .`; fix and re-run until exit 0.
8. Return the envelope.

## Output Contract

One report at `report_destination` whose final ```json block is the receipt
(`_shared/result-envelope.md` → Review Receipt). Returns:

```yaml
status: ok | blocked            # blocked = missing context; a review-blocked verdict returns status ok
failure_class: null | review
executive_summary: "..."
artifacts: [{ name: "report", path: "<report_destination>" }]
tier: 1 | 2
tier_reason: "<one line>"
verdict: review-clear | review-blocked
conformity: { decisions_checked: 0, decisions_met: 0, scenarios_checked: 0, scenarios_met: 0 }
findings_count: { CRITICAL: 0, MAJOR: 0, MINOR: 0 }
# verdict_history / not_reverified / closed — DELTA MODE only, omit otherwise
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded | fallback | none
```

The findings themselves travel in the report's receipt block, which the orchestrator settles
with `--report`; the envelope carries the counts.

## References

- [references/report-format.md](references/report-format.md) — the report template and the Delta Report Variant; load at Step 7.
- [references/envelope-examples.md](references/envelope-examples.md) — review-clear / review-blocked / blocked / delta envelopes.
- [references/edge-cases.md](references/edge-cases.md) — no changes, unrunnable checks, discrepancy, unreadable prior report, delta scope exceeded, delta files a CRITICAL.
- `../_shared/result-envelope.md` — Review Receipt schema; load at Step 6.
- `../_shared/machine.md` — what the phase file carries; how the machine consumes your report.
- `../_shared/context-protocol.md`, `../_shared/persistence-contract.md`, `../_shared/common-rules.md` — startup, write rules, principles.
- `../_shared/evidence-protocol.md` — Rule 1 (citations), Rule 7 (a check must be able to fail).
