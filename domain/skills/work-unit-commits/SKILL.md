---
name: work-unit-commits
description: "Trigger: orchestrator invokes after a candidate's checks pass and its receipt (tier>=1) is clear. Owns commit creation."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator invokes after `organic-implementer`'s acceptance checks pass and,
for a tier ≥ 1 candidate, `organic-reviewer` returns `review-clear` (or the user recorded an
override in the receipt's `overrides` field). Produce: a git commit (auto mode) or commit
instructions (manual mode) covering the candidate's changed files. Never activate on a
`review-blocked` verdict that has no recorded override, and never activate on a declared
tier ≥ 1 candidate whose receipt is absent.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Receipt gate: when the delegation prompt declares `tier >= 1`, a Review Receipt (schema: `_shared/result-envelope.md` → Review Receipt) MUST be present in the prompt — absent → `status: blocked`, no commit. `tier: 0`, or an explicit "review off" kill-switch declaration by the orchestrator, commits under ordinary policy with no receipt required. -- because fabricating an implicit tier-0 pass would let any undeclared commit bypass the review plane this gate exists to enforce.
- Neither a tier declaration nor a "review off" declaration present in the delegation prompt is never treated as tier 0 — it is a missing-context block (Decision Gates). An undeclared tier does not default to "no review needed".
- Activate only after the candidate's own acceptance checks pass and, for tier ≥ 1, the receipt shows `review-clear` or a recorded override. -- because a commit created before review completes breaks the review-then-commit order the receipt gate exists to enforce.
- Enumerate the working tree diff under `project_root` (tracked modifications + untracked adds) and stage each file individually with `git add {file}`. Staging by glob (`git add .` or `git add -A`) may include debug artifacts, `.env`, or files from other branches.
- Resolve mode from `.ai-team/config.yaml.commit_strategy`; if missing, default auto and surface a WARNING.
- Skill-first commit message resolution: before applying the default subject rule, check `{project_root}/.claude/skills/commit/SKILL.md` (project) then `~/.claude/skills/commit/SKILL.md` (user); if found, apply its rules — the default rule below is the floor.
- Conventional Commits format. Subject ≤ 72 chars: `{type}({group_id}): {description}`. No `Co-Authored-By` footer (project convention).
- On git command failure (pre-commit hook reject, merge conflict, file missing): return `status: failed` with git output in `risks`; do NOT retry.

## Decision Gates

| Condition | Action |
|---|---|
| Delegation prompt declares `tier >= 1` AND no Review Receipt is present | `status: blocked`, reason: "tier {N} candidate missing its review receipt" |
| Neither a tier declaration nor a "review off" declaration is present in the prompt | `status: blocked`, reason: "no tier declaration and no review-off declaration — cannot determine the commit gate" |
| `tier: 0`, or "review off" declared | Proceed to commit under ordinary policy; no receipt required |
| Receipt present with `verdict: review-blocked` AND no entry in `overrides` | `status: blocked`, reason: "review-blocked with no recorded override" |
| Orchestrator did not pass `group_id` | `status: blocked`, reason: "missing group_id in injected context" |
| `config.yaml` not found at `.ai-team/config.yaml` | `status: blocked`, reason: "config.yaml not found" |
| `commit_strategy` missing or unrecognised | Default to `auto`; emit WARNING in envelope |
| auto mode AND `git commit` fails | `status: failed`; do not retry; preserve git output in `risks` |
| Project or user commit skill found | Override the default subject rule for fields the skill addresses |
| Working tree has no changes under `project_root` | `status: ok`, note "nothing to commit"; run no git write commands |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup) and `_shared/persistence-contract.md` (write rules — loaded per common-rules Principle 5; this route writes no `state.yaml`, only the working tree commit itself). Validate injected context: `group_id`, `project_root`, `mode`, and — when the prompt declares `tier >= 1` — the Review Receipt. Block if `group_id` or `project_root` is missing.
2. Apply the receipt gate (Decision Gates): missing receipt at tier ≥ 1, or neither a tier nor a review-off declaration present, blocks before any git command runs. A `review-blocked` receipt with a recorded override in `overrides` clears this gate.
3. Read `.ai-team/config.yaml`. Extract `commit_strategy` (default `auto` if absent — emit WARNING).
4. Skill-first resolution: check `{project_root}/.claude/skills/commit/SKILL.md`, then `~/.claude/skills/commit/SKILL.md`. If found, load and apply its rules for commit message composition.
5. Enumerate changed files: `git -C {project_root} status --porcelain` — tracked modifications plus untracked adds under `project_root`. Empty → `status: ok`, "nothing to commit", stop (no further steps).
6. Compose the commit message: `{type}({group_id}): {description}` subject, ≤ 72 chars (truncate and emit WARNING if needed); skill-first override per Step 4. No `Co-Authored-By`.
7. **Mode dispatch:**
   - **7a (auto):** Stage each file individually: `git add {file}`. Then `git commit -m "{message}"`. On failure: return `status: failed`, git output in `risks`. On success: capture SHA.
   - **7b (manual):** Compose `manual_commit` object: `{ message: "{message}", files: [...], commands: ["git add {f1}", "git add {f2}", "git commit -m '{message}'"] }`. Emit WARNING — the user must run these commands manually.
8. Return envelope per [references/envelope-examples.md](references/envelope-examples.md).

## Output Contract

Writes: git commit to the working tree (auto mode only). Returns envelope with: `mode`
(MANDATORY), `commit_sha` (auto+ok only), `manual_commit` (manual+ok only), `group_id` (ok
only), `risks` (WARNING entries for missing receipt handling, truncated subject, missing
commit_strategy), `model_used`, `context_resolution`.

## References

- [references/envelope-examples.md](references/envelope-examples.md) — ok (auto), ok (manual), failed (hook reject), blocked (config missing) variants.
- [references/commit-message-examples.md](references/commit-message-examples.md) — pure feat, mixed feat+fix, project-skill override worked examples.
- [references/edge-cases.md](references/edge-cases.md) — pre-commit hook reject, file missing, merge conflict, undeclared file, skill contradiction, manual mode pending.
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always).
- `../_shared/context-protocol.md` — startup sequence.
- `../_shared/persistence-contract.md` — write rules (loaded per common-rules Principle 5; this route writes no `state.yaml`).
- `../_shared/result-envelope.md` — envelope schema and Review Receipt shape (gate input).
