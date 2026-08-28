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

A second mode, DELTA MODE, exists for remediation re-validation: activated whenever the
delegation prompt injects `prior_report` (the prior on-disk review report path) plus a
`delta_scope`, it runs a bounded pass instead of the full five-lens review (Decision Gates,
Execution Steps).

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Correctness lens: business logic, state transitions, concurrency, resource lifecycle, error handling. -- because a bounded, named lens set keeps this gate independently auditable and non-overlapping with organic-security's scope.
- Verification lens: re-run the Task Brief's `acceptance_checks` verbatim, plus any `config.yaml`-declared build/lint commands the checks do not already cover; capture command, exit code, and `pass`/`fail` outcome as evidence — never inferred, never a stale snapshot. A zero-work result has exactly one disposition, owned by `_shared/evidence-protocol.md` → Rule 7 item 3: recorded here as `outcome: fail`, never as `pass`, with the zero-work nature noted in `risks`. -- because "lint passes so the tests pass" is the documented apply failure class this rule exists to prevent.
- `review_gates` entries from `.ai-team/config.yaml` execute as objective gates — command + exit code only. A failing gate lands in `lenses.correctness.findings[]`, its `file`/`line` citing the gate's declaring entry in `.ai-team/config.yaml` (the line where that gate's `name:`/`command:` is declared) — this citation is always resolvable, and the finding is always `confidence: high` (objective exit-code evidence, not a judgment call). A failing blocking gate is CRITICAL, a failing non-blocking gate is MAJOR. -- because an executable assertion cannot be argued with.
- Security findings are owned exclusively by `organic-security`; no finding here may duplicate that scope. Tier 2 security review runs as a separate delegation the orchestrator merges into this receipt's `lenses.security` — this skill neither runs nor receives it.
- Read the **full content of every file** in `group_files`; run `git -C {project_root} diff HEAD -- <group_files>` only as a scope pointer to what changed. MUST NOT rely on the diff alone (it does not surface untracked new files) and MUST NOT stage anything.
- Every finding cites `file:line` per Evidence Protocol Rule 1 — a finding without a resolvable citation is not recorded (uncited is unverifiable, a distinct gate from confidence below) — but its drop is never silent: note each uncited candidate in `risks` ("uncited candidate finding dropped: <one-line topic>").
- Report every finding within the pass's scope (full pass: all of `group_files`; DELTA MODE: the delta scope per Execution Step 2), including ones you are uncertain about or consider low-severity. Do not filter for importance or confidence at this stage — that is the orchestrator's downstream triage (accept-and-proceed, re-brief, delta re-validation), not this lens's job. Coverage is the goal: a finding that later gets filtered out costs less than a real defect silently dropped. The evidence axis (below) never narrows this — it governs the SEVERITY a `read`-only finding may carry, never whether a finding is reported.
- Every finding also carries `evidence: executed | read` (`executed` = a command, mutation probe, scenario, or measurement against real data demonstrated the defect; `read` = the finding rests on code reading alone) and an optional `trigger: "<one line>"` naming the concrete input/command/state that reaches the cited line and produces the defect. The evidence cap applies at emission, before the verdict is computed: a `read` finding without a named `trigger` is emitted at MINOR as maximum. The confidence rule below then applies unchanged to the severity actually emitted — low confidence never downgrades an emitted severity, and a CRITICAL at any confidence still blocks. Consequently a CRITICAL or MAJOR with `evidence: read` always carries a `trigger`.
- Each finding carries its own `confidence: high | medium | low` alongside `severity`, so the orchestrator can rank. A CRITICAL finding at `confidence: low` is still recorded as CRITICAL and still forces `verdict: review-blocked` (fail closed) — the orchestrator resolves it via re-brief, delta re-validation, or an evidence-based override, never by this skill dropping it.
- Severity vocabulary: `CRITICAL` / `MAJOR` / `MINOR` — the Review Receipt's vocabulary (`_shared/result-envelope.md` → Review Receipt); every finding this skill emits uses this vocabulary exclusively.
- Verdict is `review-blocked` iff ≥ 1 CRITICAL finding in this skill's own lenses — correctness findings (business-logic/state/concurrency/resource/error-handling defects, verification discrepancies, and a failing blocking `review_gates` entry, all recorded in `lenses.correctness.findings[]`); otherwise `review-clear`. At tier 2 the orchestrator combines this verdict with `organic-security`'s separately-returned findings to derive the final commit gate. -- because a two-lens gate that also owned a third lens' verdict would blur the separation-of-duties the receipt's per-lens shape exists to preserve.
- A verification re-run that contradicts the implementer's claimed `check_results` (a check the envelope reported `pass` now fails, or vice versa) is itself a CRITICAL correctness finding, never silently reconciled.
- A `decisions_taken` entry that contradicts a `constraints` entry is recorded as a MAJOR finding, `evidence: read`, whose `trigger` cites both the constraint text and the decision's `where` — the two entries are the trigger by construction; never CRITICAL by itself (a contradiction is a policy deviation, not yet a demonstrated defect), never `executed` unless this skill also ran something demonstrating the defect. The mirror case is also a finding: a behavioral decision visible in the diff (a validation rule, error semantics, timeout/retry, default value, or a documented runtime claim the brief did not fix) that the forwarded `decisions_taken` does NOT declare is recorded as a MINOR `evidence: read` finding citing the undeclared site — MAJOR when it also contradicts a `constraints` entry — so the implementer's "declare, never hide" rule has an enforcer. When `decisions_taken` is injected but the brief's `constraints` is absent, the contradiction audit cannot run: note that gap in `risks` rather than silently skipping it. Composes with the evidence-cap and severity rules already stated above — it does not restate them.
- Read-only auditor: MUST NOT run state-changing git commands (commit, add, push, reset, stash, rm). No `decisions[]` entry — none exists on this route; a user-accepted override is recorded in the receipt's `overrides` field by the orchestrator, not by this skill.
- Framework-agnostic: no rule or finding category names a language, framework, package manager, or test runner; concrete names appear only inside `# e.g.` enumerations.

## Decision Gates

| Condition | Action |
|---|---|
| Missing `project_root`, `group_id`, `group_files`, `tier`, or `tier_reason` | `status: blocked`, `failure_class: null`, names the missing field(s). Never guess a substitute. |
| `prior_report` is injected, readable on disk, AND `delta_scope` accompanies it with ≥ 1 entry in `findings_to_verify` | DELTA MODE — run the bounded delta pass (Execution Step 2) instead of the full five-lens pass. |
| `prior_report` is injected but unreadable/missing on disk, or no `delta_scope` accompanies it | `status: blocked`, `failure_class: review`, names the unreachable path or the missing field — never a bounded pass on a guessed scope. |
| `delta_scope` is present but `findings_to_verify` is an empty list | `status: blocked`, `failure_class: review` — an empty list is invalid input, not "nothing to verify". |
| `delta_scope` is injected without `prior_report` | `status: blocked`, `failure_class: review` — a delta scope with no prior report to verify against matches no valid mode. |
| DELTA MODE, and `delta_scope.prior_verdict_history` is absent or empty | `status: blocked`, `failure_class: review` — the chain cannot be appended to; reconstructing it from report text is prohibited (`_shared/result-envelope.md` → Review Receipt) and truncating it loses audit history. |
| Neither `prior_report` nor `delta_scope` is injected | Run the full pass as normal (not DELTA MODE). |
| DELTA MODE, and the actual changed set (`git -C {project_root} diff HEAD --name-only`) contains a path outside `delta_scope.changed_files` and the prior report's Scope section | Record a CRITICAL correctness finding citing the out-of-scope path, `claim`: "delta scope exceeded — full pass required" — the verdict then follows the standard iff below; never silently review the wider diff. |
| `group_files` is declared but a file cannot be read (permission error, path resolves outside `project_root`, `git -C {project_root}` itself fails) — the review step cannot complete, not merely an empty scope | `status: blocked`, `failure_class: review`, names the unreachable path or command. |
| `group_files` is empty, or none of the declared files exist on disk and `git diff HEAD -- <group_files>` shows no changes | `status: ok`, `verdict: review-clear`, note "no candidate changes to review"; the receipt's `verification: []` carries `verification_omitted_reason: "no candidate changes to review"` so the sidecar gate accepts the empty list (`result-envelope.md` → Review Receipt). See `references/edge-cases.md`. |
| Finding identified (any confidence, any severity) | Record it, with its own `confidence`, `severity`, and `evidence: executed \| read` — never filter for importance or confidence at this stage (Hard Rules). |
| A finding is `evidence: read` with no named `trigger`, and would otherwise be MAJOR or CRITICAL | Emit it at `severity: MINOR` instead (the evidence cap applies at emission, before the verdict is computed) — still recorded in full, per the coverage rule. |
| A forwarded `decisions_taken` entry contradicts a brief `constraints` entry | Record a MAJOR finding, `evidence: read`, `trigger` citing the constraint text and the decision's `where` (Hard Rules). An undeclared but diff-visible decision is MINOR (MAJOR if it contradicts a constraint). `constraints` absent while `decisions_taken` is injected → note the un-auditable gap in `risks`. |
| A CRITICAL finding carries `confidence: low` | Still record it as CRITICAL — low confidence never downgrades severity or exempts the finding from the verdict iff below (fail closed). The confidence rule applies only to the severity that survives the evidence cap above. |
| Verification re-run outcome contradicts the implementer's claimed `check_results` | Record a CRITICAL correctness finding citing the discrepancy (command + both outcomes). |
| A `review_gates` entry with `blocking: true` (or `blocking` absent) exits non-zero | Record a CRITICAL finding in `lenses.correctness.findings[]`; `file`/`line` cite the gate's declaring entry in `.ai-team/config.yaml` (the line its `name:`/`command:` is declared on), `claim` names gate name + command + exit code; `verdict: review-blocked`. |
| A `review_gates` entry with `blocking: false` exits non-zero | Record a MAJOR finding in `lenses.correctness.findings[]` with the same `.ai-team/config.yaml` citation and `claim` shape; does not block the verdict. |
| A declared check — an `acceptance_checks` command, a `config.yaml`-declared build/lint command, or a `review_gates` entry — cannot be executed in this environment at all (missing tool, unreachable command) | Omit it from `verification`; note the gap in `risks` — never fabricate `pass` or `fail`. If EVERY declared check is unrunnable and `verification` ends up empty, set `verification_omitted_reason` naming that fact — the sidecar gate rejects an unexplained empty list. |
| A declared check WAS executed but returned a zero-work result (`No files analyzed`, `No tests found`, `0 suites`, `0 findings checked`, or an equivalent digest) | NOT the row above — it ran. Record it in `verification` as `outcome: fail`, per `_shared/evidence-protocol.md` → Rule 7 item 3; note the zero-work nature in `risks`. |
| ≥ 1 CRITICAL finding | `verdict: review-blocked`. |
| 0 CRITICAL findings (MAJOR/MINOR allowed) | `verdict: review-clear`. |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup) and `_shared/persistence-contract.md` (write rules — loaded per common-rules Principle 5; this skill writes no `.ai-team/` artifact by default). Validate injected context: `project_root`, `group_id`, `group_files`, `tier`, `tier_reason`, the implementer's result envelope (when forwarded), `decisions_taken` (optional — present only when the implementer's envelope reported ≥1 entry; its absence is normal, not degradation), `report_destination` (always injected for review-plane passes per Critical Context Forwarding — treat absence as degradation: report `context_resolution: fallback` and flag it in `risks`), and — for DELTA MODE — `prior_report` plus its delta scope. Report `context_resolution` honestly.
2. When `prior_report` is injected, enter DELTA MODE: read the prior report on disk. **Verify delta eligibility itself before trusting the injected scope** — diff the actual changed set (`git -C {project_root} diff HEAD --name-only`) against `delta_scope.changed_files` and the prior report's Scope section; any changed path outside that coverage voids delta eligibility — record a CRITICAL correctness finding citing the out-of-scope path (`claim`: "delta scope exceeded — full pass required") instead of silently reviewing the wider diff (Decision Gates). The verdict then follows the standard iff (Hard Rules) with no special case, and the CRITICAL finding is itself the "Delta Pass Files a CRITICAL" trigger (`references/edge-cases.md`), escalating to a full re-review. When eligible, run a bounded pass scoped to (a) verifying each named finding closed with citation, (b) checking the delta scope's changed files for any new inconsistency the fix introduced, (c) re-running the gates — do NOT repeat the prior pass's clean lenses. Compose the mandatory "not re-verified" list: every lens/file the prior pass covered that this pass did not re-check, with the reason (already clean in the prior pass, or out of delta scope) — this list also travels in the returned envelope's `not_reverified` field (Output Contract). A CRITICAL finding in a delta pass escalates to a full re-review (`references/edge-cases.md`) rather than a further delta. Absent `prior_report`, skip this step and run the full pass below.
3. Resolve each `group_files` path relative to `project_root` (in DELTA MODE, the delta scope's files); read the **full current content** of each file in scope — this covers newly created files, which a diff would not surface. Run `git -C {project_root} diff HEAD -- <group_files>` as a scope pointer to the changed regions in already-tracked files. Read up to 10 1-hop callers for context.
4. Apply the five correctness lenses (business logic, state transitions, concurrency, resource lifecycle, error handling) to the full file contents in scope. New files are wholly in scope; the diff scopes findings only within already-tracked files. Ground each finding in `file:line`. Record every finding surfaced, tagged with its own `confidence: high | medium | low`, `severity`, and `evidence: executed | read` (with a named `trigger` when `evidence: read` and severity would otherwise be MAJOR or CRITICAL — the evidence cap then applies before the verdict is computed, per Hard Rules) — never filter at this stage (Hard Rules). When `decisions_taken` is injected, read each `where` citation FIRST and audit it against the brief's `constraints` and the objective — these are the candidate's self-declared judgment calls and the highest-yield review surface. In DELTA MODE this step is bounded to the delta scope per Step 2, not the prior pass's already-clean lenses.
5. Re-run every command in the Task Brief's `acceptance_checks` verbatim, plus any `config.yaml`-declared build/lint command the checks do not already cover. Capture command, exit code, and `pass`/`fail` outcome for each — a one-line digest, never raw stdout. A contradiction against the implementer's claimed outcome becomes a CRITICAL finding (Decision Gates). Also run every `review_gates` entry declared in `.ai-team/config.yaml` (objective gates — command + exit code only, always `confidence: high`); capture command, exit code, and `pass`/`fail` outcome for each, and assign severity per Decision Gates.
6. Compute the verdict from this skill's own findings (Hard Rules). Compose the Review Receipt: `tier`, `tier_reason`, `lenses.correctness` (`status: pass | findings`, findings list), `verification` (per-command evidence), `overrides: []` (the orchestrator populates this field, never this skill). In DELTA MODE, append EXACTLY ONE entry — this pass's own — to the `delta_scope.prior_verdict_history` array injected by the orchestrator, return the full resulting chain as `verdict_history`, and carry the Step 2 "not re-verified" list forward as `not_reverified` (schema: `_shared/result-envelope.md` → Review Receipt).
7. When `report_destination` is injected, write the report per `references/report-format.md` there (create its parent directory if absent), resolved relative to `project_root` — use the Delta Report Variant in DELTA MODE. In the SAME step, write a `.json` sidecar next to it — `report_destination` with the `.md` extension replaced by `.json` — serializing the exact Review Receipt object composed at Step 6 (same field names, no additions). Self-check it before returning: `python3 skills/_shared/scripts/check-receipt.py receipt {sidecar path} .`; fix any printed `VIOLATION` line before returning — the orchestrator's own Citation audit re-runs this same validator as its BLOCKING gate and never reads the `.md` report. `report_destination` is always injected for review-plane passes; in the degraded case where it is absent, the envelope's Review Receipt is the only record, no sidecar exists, and the blocking Citation audit cannot fire — flag that in `risks`.
8. Return the envelope per Output Contract.

## Output Contract

Writes the report at the injected `report_destination` (resolved relative to `project_root`),
plus a `.json` sidecar of the same name (`.md` → `.json`) serializing the Review Receipt object
verbatim — mandatory from the orchestrator's side for every review-plane delegation
(`orchestrator-protocol.md` → Critical Context Forwarding); optional only from this skill's own
write step, i.e. it writes nothing when no destination is injected. No fixed path, no separate
`.ai-team/` artifact. Returns:

```yaml
status: ok | blocked            # blocked only on missing context, NOT on a review-blocked verdict
failure_class: null | review    # "review" iff the review step itself could not complete (Decision Gates); null otherwise
executive_summary: "..."
group_id: "<brief-slug>"
artifacts: []                   # only when report_destination was written this run — both the .md report and its .json sidecar
tier: 1 | 2
tier_reason: "<one line>"
lenses:
  correctness:
    status: pass | findings
    findings:                   # CAP 20 entries — on overflow keep the highest severity-then-confidence entries and note the omitted count in risks ("findings omitted at cap: N")
      - { id: "F-1", severity: CRITICAL | MAJOR | MINOR, confidence: high | medium | low, evidence: executed | read, trigger: "<one line — optional; REQUIRED when severity is MAJOR or CRITICAL and evidence is read>", file: "<path>", line: <int>, claim: "<one line>" }
verification:
  - { command: "<verbatim>", exit_code: 0, outcome: pass | fail, gate: "<name>" }  # gate: present only for review_gates entries
# verification_omitted_reason: "<one line>"   # ONLY when verification is [] (no candidate changes / every check unrunnable); omit otherwise
overrides: []                   # always empty on return — the orchestrator populates this field
verdict: review-clear | review-blocked   # null only in a status:blocked context-failure envelope, where no review ran
# verdict_history: []           # DELTA MODE only — the full chain incl. this pass's appended entry.
                                 # Omit the field entirely on a full pass — never render it as `[]`;
                                 # the validator rejects an empty verdict_history list outright.
# not_reverified: []            # DELTA MODE only — areas/lenses/files the prior pass covered that
                                 # this pass did not re-check. Omit entirely on a full pass, same rule.
next_recommended: []
risks: []
model_used: "opus"
context_resolution: self-loaded | fallback | none
```

`lenses.security` is never present in this skill's own return — the orchestrator merges
`organic-security`'s separate result into the receipt at tier 2 (see Hard Rules).

A DELTA MODE receipt additionally carries `verdict_history` — this pass APPENDS exactly one
entry to the array injected as `delta_scope.prior_verdict_history` (chain custody:
`orchestrator-protocol.md` → Evidence-Tier Review → Delta re-validation; schema:
`_shared/result-envelope.md` → Review Receipt) and returns the full chain — and `not_reverified`
(the areas/lenses/files the prior pass covered that this pass did not re-check, mirroring the
on-disk report's "Not Re-Verified" list, `references/report-format.md` → Delta Report Variant);
a full-pass receipt omits both fields entirely.

## References

- [references/report-format.md](references/report-format.md) — the on-disk report template (receipt-shaped), plus the Delta Report Variant; load at Step 7 when `report_destination` is injected.
- [references/envelope-examples.md](references/envelope-examples.md) — review-clear / review-blocked / blocked / delta envelope variants; load when composing the result.
- [references/edge-cases.md](references/edge-cases.md) — no candidate changes, all findings low-confidence, missing context, large file set, unrunnable checks, verification discrepancy, unreadable prior report/absent delta scope, delta scope exceeded, delta pass files a CRITICAL; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules (loaded per common-rules Principle 5; this skill writes no `.ai-team/` artifact by default).
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — Review Receipt schema (canonical field shapes, incl. `verdict_history`); load at Step 6.
- `../_shared/evidence-protocol.md` — Rule 1 (file:line citation mandatory for every finding).
