---
name: sdd-reviewer
description: "Trigger: orchestrator invokes after sdd-verify GREEN on a group, before work-unit-commits. Code-correctness review gate."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator invokes the reviewer after `sdd-verify` returns GREEN (PASS or PASS WITH WARNINGS) for a logical group, and before `work-unit-commits` creates the commit. Produce `review-report.md` and a blocking verdict. Read application code to find code-correctness defects; never modify it. The reviewer has no modes.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Review lens is **code correctness only**: concurrency and race conditions; resource lifecycle (acquisition, use, release); error handling and propagation; API-contract misuse. -- because focusing on a distinct, bounded lens prevents overlap with sdd-security (security) and sdd-verify (spec-compliance) and ensures each gate is independently auditable.
- Security findings are owned exclusively by `sdd-security`; spec-compliance findings are owned exclusively by `sdd-verify`. No finding may duplicate either adjacent scope. -- because overlapping verdicts from two gates create contradictory overrides and undermine the separation-of-duties model.
- Read the **full content of every declared file** in the group (`group_files`); run `git diff HEAD -- <group_files>` only as a scope pointer to what this group changed. MUST NOT rely on the diff alone, MUST NOT use a `base..branch` diff, MUST NOT stage to surface files. -- because `git diff HEAD` does not surface newly created (untracked) files and correctness defects live in the interaction with surrounding unchanged context; reading files directly captures both while keeping the reviewer read-only.
- Every finding cites `file:line` per Evidence Protocol Rule 1. No citation = suppress and tally. -- because uncited findings are unverifiable and the orchestrator cannot route a fix without knowing exactly where the defect is.
- Confidence threshold **strictly > 80%**. Suppress findings ≤ 80%; tally every suppression. -- because false positives train users to override reflexively, defeating the gate's purpose.
- Severity vocabulary: `CRITICAL` / `WARNING` / `SUGGESTION` only. Never HIGH / MEDIUM / LOW. -- because consistent vocabulary across all three gates (reviewer, security, verify) keeps the orchestrator's routing logic single-table and avoids misclassification at override prompts.
- Verdict is `review-blocked` iff ≥ 1 CRITICAL finding; otherwise `review-clear`. WARNING and SUGGESTION never block. -- because non-critical findings inform without forcing re-engage, matching sdd-security's verdict semantics and preventing override fatigue.
- Read-only auditor: MUST NOT run state-changing git commands (commit, add, push, reset, stash, rm) and MUST NOT write `state.yaml.decisions[]`. The orchestrator records review overrides. -- because an auditor that also writes decisions could launder its own findings through a self-authored override entry.
- Lens taxonomy is framework-agnostic: no finding category may name a language, framework, library, runtime, or tool-native command; concrete names only inside `# e.g.` enumerations. -- because the tool-agnostic invariant must hold across all domain/ skills.

## Decision Gates

| Condition | Action |
|---|---|
| Missing `group_id` / `group_files` and not recoverable from `state.yaml` | `status: blocked`, reason names the missing field. |
| `group_files` is empty, or none of the declared files exist on disk | `status: ok`, `verdict: review-clear`; report notes "no group changes to review". See `references/edge-cases.md`. |
| Finding confidence > 80% | Record finding. |
| Finding confidence ≤ 80% | Suppress; increment tally. |
| ≥ 1 CRITICAL finding | `verdict: review-blocked`. |
| 0 CRITICAL findings (WARNING/SUGGESTION allowed) | `verdict: review-clear`. |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup), `_shared/persistence-contract.md` (write rules). Validate injected context: `change_name`, `change_dir`, `group_id`, `group_files`, `project_root`, `tasks_path`. Recover missing fields from `state.yaml`/`tasks.md`; report `context_resolution: fallback` if needed.
2. Resolve the file set: use injected `group_files`. If absent, derive it from `tasks.md` `Files:` blocks for `group_id` (the same union `work-unit-commits/SKILL.md` Step 5 computes). **Read the full current content of each file** in the set — this covers newly created files, which `git diff HEAD` would not surface. Run `git diff HEAD -- <group_files>` as a scope pointer to the changed regions in tracked files. Read up to 10 1-hop callers for context.
3. Apply the four correctness lenses to the file contents (concurrency / resource lifecycle / error handling / API-contract misuse). New files are wholly in scope; the diff scopes findings only within already-tracked files (do NOT limit a new file's review to diff hunks). Ground each finding in `file:line`. Suppress confidence ≤ 80% with a tally.
4. Write `{change_dir}/review-report.md` per `references/review-report-template.md`. All four lens sections present ("No findings" if clean); include the group ID, verdict, numbered findings with stable IDs (`RV-001`, `RV-002`, …), suppression tally, and the confidence threshold applied.
5. Update `state.yaml`: `phases.review.status: done`, `completed: {current_iso_utc}`, `agent: sdd-reviewer`. (Runtime key `review`; `decisions[].phase` token is `code-review` — written by orchestrator, not here.)
6. Return envelope per `references/envelope-examples.md`.

## Output Contract

Writes `.ai-team/changes/{change}/review-report.md`; updates `state.yaml.phases.review`. Returns envelope with `status`, `executive_summary`, `artifacts`, `findings`, `verdict` (`review-clear` | `review-blocked`), `suppressed_count`, `group_id`, `next_recommended`, `risks`, `model_used`, `context_resolution`. No `decisions_written` field (auditor role — the orchestrator exclusively writes `decisions[]` override entries).

## References

- [references/review-report-template.md](references/review-report-template.md) — review-report.md output template and per-finding structure; load at Step 4.
- [references/envelope-examples.md](references/envelope-examples.md) — envelope variants (review-clear / review-blocked / blocked); load when returning the result.
- [references/edge-cases.md](references/edge-cases.md) — empty diff, all-suppressed, missing group_files, large diff; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules, `decisions:` full schema; load at Step 1.
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — envelope schema; load when returning the result.
- `../_shared/evidence-protocol.md` — Rule 1 (file:line citation mandatory for every finding).
