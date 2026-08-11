---
name: sdd-reviewer
description: "Trigger: orchestrator invokes after sdd-verify GREEN on a group, before work-unit-commits. Code-correctness review gate."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator invokes the reviewer after `sdd-verify` returns GREEN (PASS or PASS WITH WARNINGS) for a logical group, and before `work-unit-commits` creates the commit. Produce `review-report.md` and a blocking verdict. Read application code to find code-correctness defects; never modify it. The reviewer has two invocation modes inferred from its injected inputs — SDD and non-SDD (organic); the four correctness lenses, the >80% confidence threshold, the severity vocabulary, and the verdict semantics (`review-clear`/`review-blocked`) are identical in both modes.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Review lens is **code correctness only**: concurrency and race conditions; resource lifecycle (acquisition, use, release); error handling and propagation; API-contract misuse. -- because focusing on a distinct, bounded lens prevents overlap with sdd-security (security) and sdd-verify (spec-compliance) and ensures each gate is independently auditable.
- Security findings are owned exclusively by `sdd-security`; spec-compliance findings are owned exclusively by `sdd-verify`. No finding may duplicate either adjacent scope. -- because overlapping verdicts from two gates create contradictory overrides and undermine the separation-of-duties model.
- Spec MUSTs calibrate observations: when an observation surfaced by the correctness lenses contradicts a `MUST` requirement (cite the REQ-ID from the injected `spec_paths`), record it as a finding — an established project pattern legitimizes style choices, never contract violations. Spec-compliance *verification* (test execution, compliance matrix) stays with sdd-verify; this rule classifies only what the correctness lenses already surfaced. -- because the contract defines correct behavior, so contradicting it is a correctness defect by definition: a reviewer once saw a MUST violation, filed it as "mirrors the established pattern", and the defect shipped.
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
| **SDD mode** (`change_dir` + `tasks_path` present): Missing `group_id` / `group_files` and not recoverable from `state.yaml` | `status: blocked`, reason names the missing field. |
| **Non-SDD mode** and `report_destination` missing | `status: blocked`, reason names the missing destination. Never derive a path. |
| Neither mode's discriminating inputs present | `status: blocked` per the existing gate (missing `group_id`/`group_files`, not recoverable) — unchanged outcome. |
| `group_files` is empty, or none of the declared files exist on disk | `status: ok`, `verdict: review-clear`; report notes "no group changes to review". See `references/edge-cases.md`. |
| Finding confidence > 80% | Record finding. |
| Finding confidence ≤ 80% | Suppress; increment tally. |
| Observation contradicts a spec `MUST` (REQ-ID citable) | Record as finding regardless of pattern mimicry; severity per blast radius (CRITICAL when the violated MUST guards data integrity or a critical flow). |
| ≥ 1 CRITICAL finding | `verdict: review-blocked`. |
| 0 CRITICAL findings (WARNING/SUGGESTION allowed) | `verdict: review-clear`. |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup), `_shared/persistence-contract.md` (write rules). Validate injected context: `change_name`, `change_dir`, `group_id`, `group_files`, `project_root`, `tasks_path`, plus the directed-review inputs `attention_areas` (orchestrator-curated "trace X, verify Y" lines), `untested_scenarios` (verify's UNTESTED / pre-accepted rows), and `spec_paths`. **Mode inference (input precedence).** When `change_dir` AND `tasks_path` are present, run the SDD path — unchanged, including the blocking gate below. When both are absent AND `group_files` plus `report_destination` are injected, run the non-SDD (organic) path: same lenses, same threshold, same verdict; no phase-tracking write; the report goes to `report_destination`. If SDD and non-SDD inputs both appear, **SDD wins** — presence of `change_dir`/`tasks_path` always selects SDD mode. Recover missing fields from `state.yaml`/`tasks.md`; report `context_resolution: fallback` if needed. When the directed-review inputs are absent, proceed with the four lenses alone and record the gap in `risks` ("review ran undirected — no attention_areas injected").
2. Resolve the file set: use injected `group_files`. **SDD mode only:** if absent, derive it from `tasks.md` `Files:` blocks for `group_id` (the same union `work-unit-commits/SKILL.md` Step 5 computes). **Read the full current content of each file** in the set — this covers newly created files, which `git diff HEAD` would not surface. Run `git diff HEAD -- <group_files>` as a scope pointer to the changed regions in tracked files. Read up to 10 1-hop callers for context.
3. Inspect in priority order: (a) each injected `attention_areas` line — trace the named flow end-to-end exactly as instructed (these encode project memories and threat-model context the lenses alone lack); (b) each `untested_scenarios` row — a pre-accepted UNTESTED scenario marks a code path zero tests cover, the highest-yield place for a defect to hide; (c) then apply the four correctness lenses to the full file contents (concurrency / resource lifecycle / error handling / API-contract misuse). New files are wholly in scope; the diff scopes findings only within already-tracked files (do NOT limit a new file's review to diff hunks). Ground each finding in `file:line`. Before discarding any observation as style, cross-check it against the MUSTs of the group's REQs in `spec_paths` (Hard Rule: MUST contradiction = finding). Suppress confidence ≤ 80% with a tally.
4. Write the report per `references/review-report-template.md` — to `{change_dir}/review-report.md` in SDD mode, or to the injected `report_destination` in non-SDD mode (create its parent directory if absent). All four lens sections present ("No findings" if clean); include the group ID, verdict, numbered findings with stable IDs (`RV-001`, `RV-002`, …), suppression tally, and the confidence threshold applied.
5. **SDD mode only:** update `state.yaml`: `phases.review.status: done`, `completed: {current_iso_utc}`, `agent: sdd-reviewer`. (Runtime key `review`; `decisions[].phase` token is `code-review` — written by orchestrator, not here.)
6. Return envelope per `references/envelope-examples.md`.

## Output Contract

Writes `.ai-team/changes/{change}/review-report.md` in SDD mode, or the injected `report_destination` in non-SDD mode. Updates `state.yaml.phases.review` in SDD mode only — non-SDD mode writes no `state.yaml` (no change directory exists). Returns envelope with `status`, `executive_summary`, `artifacts`, `findings`, `verdict` (`review-clear` | `review-blocked`), `suppressed_count`, `group_id`, `next_recommended`, `risks`, `model_used`, `context_resolution`. No `decisions_written` field (auditor role — the orchestrator exclusively writes `decisions[]` override entries).

## References

- [references/review-report-template.md](references/review-report-template.md) — review-report.md output template and per-finding structure; load at Step 4.
- [references/envelope-examples.md](references/envelope-examples.md) — envelope variants (review-clear / review-blocked / blocked); load when returning the result.
- [references/edge-cases.md](references/edge-cases.md) — empty diff, all-suppressed, missing group_files, large diff; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules, `decisions:` full schema; load at Step 1.
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always, seniority); load at startup.
- `../_shared/result-envelope.md` — envelope schema; load when returning the result.
- `../_shared/evidence-protocol.md` — Rule 1 (file:line citation mandatory for every finding).
