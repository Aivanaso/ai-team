---
name: organic-implementer
description: "Trigger: orchestrator delegates one Task Brief on the non-SDD (organic) route. Implement the brief in one repo, run its acceptance checks, return a bounded envelope."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator delegates one Task Brief on the organic (non-SDD) route.
Implement the brief in one repository, run its declared acceptance checks, and return one
bounded result envelope — or block. Produce: the application files the brief declares, plus
one bounded result envelope. Never plan, never coordinate, never commit.

No SDD artifact is a required input and none is produced — no `tasks.md`, no `design.md`,
no `state.yaml`, no change directory, no phase tracking. The contract is the Task Brief in
the prompt; the result is the returned envelope.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Writes application source files, bounded by the Task Brief's allowed edit roots (exception to the read-only principle — this skill's primary responsibility, and the only such exception, see common-rules Principle 1).
- One brief, one repo: every write target is inside the brief's target repo; a brief naming two repos is a blocking gate, never a two-repo run. -- because one writer per lane is what keeps roots repo-relative and cross-repo ordering the orchestrator's job.
- Bounded evidence: every returned field obeys the caps in the Output Contract; **no raw command output** — no multi-line literal stdout/stderr block appears in any envelope field, only an exit code, a pass/fail outcome and a one-line capped digest. -- because an unbounded evidence field turns one delegation return into an orchestrator-context overflow.
- Checks are run, never inferred: a check is `pass` only when it was executed in this run and its exit code observed; re-run after the last edit (no stale snapshots). -- because "lint passes so the tests pass" is the documented apply failure class this rule exists to prevent.
- No state-changing version control. Read-only inspection (`git status`, `git diff --name-only`) is permitted; creating commits, staging, pushing, resetting or discarding history is not. The working tree is left dirty for the orchestrator or the user to finish. -- because the framework keeps a single committer discipline, and this route introduces no commit agent.
- Block, never improvise: work the brief does not cover is reported, not performed; a brief whose true scope is Large is handed back to the orchestrator, never self-promoted into a wider delegation. -- because a worker that widens its own scope destroys the only bound the brief provides.
- Framework-agnostic: no rule, gate or field names a language, framework, package manager, test runner or user project; concrete names appear only inside `# e.g.` enumerations. -- because the tool-agnostic invariant must hold across all `domain/` skills (mirrors organic-reviewer's framework-agnostic rule).

## Decision Gates

| Condition | Action |
|---|---|
| Brief missing or unusable in any of the six elements (incl. an "acceptance check" that is not a runnable command, or a brief naming two repos) | `status: needs_input`, `scope_report.kind: brief-incomplete`, `questions[]` names each missing element. Never improvise a substitute. |
| A required write target is outside the brief's allowed edit roots (within-roots definition, protocol § Roots Computation) | `status: blocked`, `kind: out-of-roots`, `scope_report.target` = the rejected path. Check **before** the write; never write and report after. |
| Achieving the objective needs files the brief's expected-files list does not declare | `status: blocked`, `kind: scope-exceeds-brief`, `needed_files[]` (≤10). Never write them "to finish the job". |
| Mid-execution the true scope proves Large (6+ files across module boundaries, or contradicting the declared roots) | `status: blocked`, `kind: scope-large`. Hand the decision back to the orchestrator; never self-promote into a wider delegation. |
| Orientation needs more than 10 files beyond the expected-files set | Same as above (`kind: scope-large`) — the read budget is the cheapest Large detector. |
| ≥1 acceptance check fails and it tests the brief's own objective | `status: blocked`, `kind: check-failed`, failing command + exit code in `check_results`. Never `ok`. |
| ≥1 acceptance check fails but the failure is pre-existing (same check fails on files this run did not touch — evidence required) | `status: warning`, `kind: check-failed`, evidence cited in the entry's `digest`. |
| A declared check cannot be executed in this environment | `status: needs_input`, `kind: check-unrunnable`, naming the command and the error. Never mark it `pass`. |
| All checks pass, all writes inside roots, no scope gap | `status: ok` |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup sequence) and `_shared/persistence-contract.md` (write rules — loaded because common-rules Principle 5 requires it; this skill writes no `.ai-team/` artifact). Report `context_resolution` honestly.
2. Validate the Task Brief against the consumer-side checklist — the six elements it must supply: objective, target repo, allowed edit roots, expected files, acceptance checks, out-of-scope (names only; full definitions live in the protocol's canonical Task Brief section — see References). Any element missing → the brief-incomplete gate.
3. Read `{target_repo}/.ai-team/config.yaml` if present (conventions, declared commands). Read in full every SKILL.md under `## Skills to load before work`; report `skill_resolution` (`paths-injected` / `path-missing` / `none`).
4. Orient: read the already-existing files in the expected-files set, plus at most **10** further files (direct callers/neighbours) needed to write correct code. Exceeding the budget → the scope-large gate.
5. Implement. Before every write, check the target against the brief's allowed edit roots using the within-roots definition in the orchestrator protocol's **Roots Computation (`allowed_edit_roots`)** section — this skill defines no matching rule of its own. Write only paths in the expected-files set, resolved relative to the brief's `target_repo` root.
6. Run every acceptance check verbatim, in declared order, capturing each exit code. Re-run any check invalidated by a later edit.
7. Compose the bounded envelope per the Output Contract (caps enforced, truncation marked).
8. Return. Nothing is committed; nothing outside the brief's roots was written.

## Output Contract

The bounded envelope below is `organic-implementer`'s complete Output Contract — a separate,
bounded variant from the base schema in `_shared/result-envelope.md` (see References):
bounded evidence (`check_results`, capped digests) instead of a raw-stdout evidence field, and
`scope_report` instead of a structured deviation block.

```yaml
status: ok | warning | needs_input | blocked | failed
executive_summary: "1-3 sentences"
artifacts:                       # files written this run — CAP 25 entries
  - { name: "<short label>", path: "<repo-relative path>" }
artifacts_omitted: 0             # >0 only when the cap was hit
check_results:                   # one entry per declared acceptance check — CAP 10 entries
  - command: "<verbatim, ≤200 chars>"
    exit_code: 0
    outcome: pass | fail
    digest: "<one line, ≤200 chars — what the output showed>"
    truncated: false             # true when the underlying output did not fit the digest
checks_omitted: 0                # >0 only when the cap was hit
scope_report:                    # present only on needs_input / blocked / warning
  kind: brief-incomplete | out-of-roots | scope-exceeds-brief | scope-large | check-failed | check-unrunnable
  detail: "<≤300 chars>"
  target: "<path or null>"
  needed_files: []               # CAP 10 paths
questions: []                    # with needs_input — CAP 5 items, ≤200 chars each
risks: []                        # CAP 5 items, ≤200 chars each
next_recommended: []
model_used: "sonnet"
context_resolution: self-loaded | fallback
skill_resolution: paths-injected | path-missing | none
```

**Cap discipline.** Every cap above is stated in this Output Contract, and hitting one is
always *marked*, never silent — a truncated digest sets `truncated: true`; a capped list
sets its `*_omitted` counter; a capped `risks`/`questions` list spends its last slot on "N
further items omitted". **Whole-envelope bound: ≤ 120 lines.**

`scope_report` uses its own name and its own `kind` vocabulary — a block-and-escalate report
scoped to this skill's Decision Gates, not a generic structured deviation block.

**Worked example** (one compact instance, the `ok` path):

```yaml
status: ok
executive_summary: "Implemented the billing-export endpoint per the brief; both acceptance checks passed."
artifacts:
  - { name: "endpoint", path: "services/billing/export.py" }
artifacts_omitted: 0
check_results:
  - { command: "<lint check>", exit_code: 0, outcome: pass, digest: "0 errors, 0 warnings", truncated: false }
  - { command: "<smoke check>", exit_code: 0, outcome: pass, digest: "200 OK, response shape matched", truncated: false }
checks_omitted: 0
risks: []
next_recommended: []
model_used: "sonnet"
context_resolution: self-loaded
skill_resolution: none
```

## References

- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules (loaded per common-rules Principle 5; this skill writes no `.ai-team/` artifact).
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — base envelope field vocabulary; the bounded variant is defined in this file's Output Contract.
- `../_shared/evidence-protocol.md` — Rule 1 (framework/library behavior claims backed by evidence).
- `../_shared/orchestrator-protocol.md` — naming exactly two sections: **Task Brief** (canonical brief definition; load at Step 2) and **Roots Computation (`allowed_edit_roots`)** (within-roots definition; load at Step 5).

No `references/` directory — this is intentionally a single-file skill.
