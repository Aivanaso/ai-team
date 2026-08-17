---
name: organic-reviewer
description: "Trigger: orchestrator invokes after a tier>=1 candidate, before work-unit-commits. Correctness + verification gate."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator invokes the reviewer after `organic-implementer` returns `status: ok`
(or a `warning` the user accepted) for a tier ≥ 1 candidate, and before `work-unit-commits`
creates the commit. Produce a result envelope carrying the Review Receipt (schema:
`_shared/result-envelope.md` → Review Receipt). Reviews the exact diff a worker produced,
never a plan. Read application code to find correctness defects and re-run verification
evidence; never modify application code.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Correctness lens: business logic, state transitions, concurrency, resource lifecycle, error handling. -- because a bounded, named lens set keeps this gate independently auditable and non-overlapping with organic-security's scope.
- Verification lens: re-run the Task Brief's `acceptance_checks` verbatim, plus any `config.yaml`-declared build/lint commands the checks do not already cover; capture command, exit code, and `pass`/`fail` outcome as evidence — never inferred, never a stale snapshot. -- because "lint passes so the tests pass" is the documented apply failure class this rule exists to prevent.
- Security findings are owned exclusively by `organic-security`; no finding here may duplicate that scope. Tier 2 security review runs as a separate delegation the orchestrator merges into this receipt's `lenses.security` — this skill neither runs nor receives it.
- Read the **full content of every file** in `group_files`; run `git -C {project_root} diff HEAD -- <group_files>` only as a scope pointer to what changed. MUST NOT rely on the diff alone (it does not surface untracked new files) and MUST NOT stage anything.
- Every finding cites `file:line` per Evidence Protocol Rule 1. No citation = suppress and tally.
- Confidence threshold **strictly > 80%**. Suppress findings ≤ 80%; tally every suppression.
- Severity vocabulary: `CRITICAL` / `MAJOR` / `MINOR` — the Review Receipt's vocabulary (`_shared/result-envelope.md` → Review Receipt); every finding this skill emits uses this vocabulary exclusively.
- Verdict is `review-blocked` iff ≥ 1 CRITICAL finding in this skill's own lenses (correctness + verification discrepancies); otherwise `review-clear`. At tier 2 the orchestrator combines this verdict with `organic-security`'s separately-returned findings to derive the final commit gate. -- because a two-lens gate that also owned a third lens' verdict would blur the separation-of-duties the receipt's per-lens shape exists to preserve.
- A verification re-run that contradicts the implementer's claimed `check_results` (a check the envelope reported `pass` now fails, or vice versa) is itself a CRITICAL correctness finding, never silently reconciled.
- Read-only auditor: MUST NOT run state-changing git commands (commit, add, push, reset, stash, rm). No `decisions[]` entry — none exists on this route; a user-accepted override is recorded in the receipt's `overrides` field by the orchestrator, not by this skill.
- Framework-agnostic: no rule or finding category names a language, framework, package manager, or test runner; concrete names appear only inside `# e.g.` enumerations.

## Decision Gates

| Condition | Action |
|---|---|
| Missing `project_root`, `group_id`, `group_files`, `tier`, or `tier_reason` | `status: blocked`, `failure_class: null`, names the missing field(s). Never guess a substitute. |
| `group_files` is declared but a file cannot be read (permission error, path resolves outside `project_root`, `git -C {project_root}` itself fails) — the review step cannot complete, not merely an empty scope | `status: blocked`, `failure_class: review`, names the unreachable path or command. |
| `group_files` is empty, or none of the declared files exist on disk and `git diff HEAD -- <group_files>` shows no changes | `status: ok`, `verdict: review-clear`, note "no candidate changes to review". See `references/edge-cases.md`. |
| Finding confidence > 80% | Record finding. |
| Finding confidence ≤ 80% | Suppress; increment tally. |
| Verification re-run outcome contradicts the implementer's claimed `check_results` | Record a CRITICAL correctness finding citing the discrepancy (command + both outcomes). |
| A declared check cannot be executed in this environment | Omit it from `verification`; note the gap in `risks` — never fabricate `pass` or `fail`. |
| ≥ 1 CRITICAL finding | `verdict: review-blocked`. |
| 0 CRITICAL findings (MAJOR/MINOR allowed) | `verdict: review-clear`. |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup) and `_shared/persistence-contract.md` (write rules — loaded per common-rules Principle 5; this skill writes no `.ai-team/` artifact by default). Validate injected context: `project_root`, `group_id`, `group_files`, `tier`, `tier_reason`, the implementer's result envelope (when forwarded), and an optional `report_destination`. Report `context_resolution` honestly.
2. Resolve each `group_files` path relative to `project_root`; read the **full current content** of each file — this covers newly created files, which a diff would not surface. Run `git -C {project_root} diff HEAD -- <group_files>` as a scope pointer to the changed regions in already-tracked files. Read up to 10 1-hop callers for context.
3. Apply the five correctness lenses (business logic, state transitions, concurrency, resource lifecycle, error handling) to the full file contents. New files are wholly in scope; the diff scopes findings only within already-tracked files. Ground each finding in `file:line`. Suppress confidence ≤ 80% with a tally.
4. Re-run every command in the Task Brief's `acceptance_checks` verbatim, plus any `config.yaml`-declared build/lint command the checks do not already cover. Capture command, exit code, and `pass`/`fail` outcome for each — a one-line digest, never raw stdout. A contradiction against the implementer's claimed outcome becomes a CRITICAL finding (Decision Gates).
5. Compute the verdict from this skill's own findings (Hard Rules). Compose the Review Receipt: `tier`, `tier_reason`, `lenses.correctness` (`status: pass | findings`, findings list), `verification` (per-command evidence), `overrides: []` (the orchestrator populates this field, never this skill).
6. When `report_destination` is injected, write the report per `references/report-format.md` there (create its parent directory if absent), resolved relative to `project_root`. Run `bash _shared/scripts/check-verify-citations.sh {report_destination} .` when applicable — its grep targets `COMPLIANT`/`FAILING` scenario rows and will report a trivial 0-checked pass against this skill's CRITICAL/MAJOR/MINOR finding format (that vocabulary mismatch is a known gap, not a citation defect); citation discipline for findings is enforced by this skill's own Hard Rule instead (no `file:line` = suppress and tally). Otherwise the envelope's Review Receipt is the sole record.
7. Return the envelope per Output Contract.

## Output Contract

Writes nothing by default; writes the report at the injected `report_destination` (resolved
relative to `project_root`) only when one is provided — no fixed path, no `.ai-team/`
artifact. Returns:

```yaml
status: ok | blocked            # blocked only on missing context, NOT on a review-blocked verdict
failure_class: null | review    # "review" iff the review step itself could not complete (Decision Gates); null otherwise
executive_summary: "..."
group_id: "<brief-slug>"
artifacts: []                   # only when report_destination was written this run
tier: 1 | 2
tier_reason: "<one line>"
lenses:
  correctness:
    status: pass | findings
    findings:                   # CAP 20 entries
      - { id: "F-1", severity: CRITICAL | MAJOR | MINOR, file: "<path>", line: <int>, claim: "<one line>" }
verification:
  - { command: "<verbatim>", exit_code: 0, outcome: pass | fail }
overrides: []                   # always empty on return — the orchestrator populates this field
verdict: review-clear | review-blocked
suppressed_count: 0
next_recommended: []
risks: []
model_used: "opus"
context_resolution: self-loaded | fallback | none
```

`lenses.security` is never present in this skill's own return — the orchestrator merges
`organic-security`'s separate result into the receipt at tier 2 (see Hard Rules).

## References

- [references/report-format.md](references/report-format.md) — the on-disk report template (receipt-shaped); load at Step 6 when `report_destination` is injected.
- [references/envelope-examples.md](references/envelope-examples.md) — review-clear / review-blocked / blocked envelope variants; load when composing the result.
- [references/edge-cases.md](references/edge-cases.md) — no candidate changes, all-suppressed, missing context, large file set, unrunnable checks, verification discrepancy; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules (loaded per common-rules Principle 5; this skill writes no `.ai-team/` artifact by default).
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — Review Receipt schema (canonical field shapes); load at Step 5.
- `../_shared/evidence-protocol.md` — Rule 1 (file:line citation mandatory for every finding).
