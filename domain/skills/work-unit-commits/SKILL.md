---
name: work-unit-commits
description: "Trigger: orchestrator invokes after sdd-verify GREEN on a group. Owns commit creation per logical group (auto/manual mode)."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator invokes after sdd-verify returns GREEN (PASS or PASS WITH WARNINGS) for a logical group. Produce: a git commit (auto mode) or commit instructions (manual mode) covering all declared files for the completed group. Update `state.yaml.phases.apply.commits[group_id]`. Never activate on verify FAIL.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Activate only on orchestrator invocation after verify GREEN (REQ-WUC-001). -- because premature commits before sdd-verify runs break the pipeline's validation order; uncommitted state is required for verify's diff scope.
- Stage each declared file individually with `git add {file}` (REQ-WUC-006). Staging by glob (`git add .` or `git add -A`) may include debug artifacts, `.env`, or files from other branches.
- Resolve mode from `.ai-team/config.yaml.commit_strategy`; if missing, default auto and surface a WARNING (REQ-WUC-002).
- Skill-first commit message resolution: before applying REQ-WUC-005 defaults, check `{project_root}/.claude/skills/commit/SKILL.md` (project) then `~/.claude/skills/commit/SKILL.md` (user); if found, apply its rules; REQ-WUC-005 is the floor (REQ-WUC-008).
- Conventional Commits format. Subject ≤ 72 chars: `{type}({change-name}/G{N}): {description}`. Body: `Covers: REQ-X, REQ-Y`. No `Co-Authored-By` footer (project convention) (REQ-WUC-005).
- On git command failure (pre-commit hook reject, merge conflict, file missing): return `status: failed` with git output in `risks`; do NOT retry (REQ-WUC-003).
- Backfill commit SHA into `state.yaml.decisions[]` entries that have `commits: []` for tasks in this group (REQ-WUC-003 step 5).

## Decision Gates

| Condition | Action |
|---|---|
| Orchestrator did not pass `group_id` | `status: blocked`, reason: "missing group_id in injected context" |
| `config.yaml` not found at `.ai-team/config.yaml` | `status: blocked`, reason: "config.yaml not found" |
| `commit_strategy` missing or unrecognised | Default to `auto`; emit WARNING in envelope |
| auto mode AND `git commit` fails | `status: failed`; do not retry; preserve git output in `risks` |
| Project or user commit skill found | Override REQ-WUC-005 defaults for fields the skill addresses (REQ-WUC-008) |
| Undeclared file in working tree (in diff but not in any task `Files:` block) | Stage only the declared files; emit WARNING for the undeclared file (REQ-WUC-006) |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup) and `_shared/persistence-contract.md` (write rules). Validate injected context: `group_id`, `change_name`, `project_root`. Block if missing.
2. Read `.ai-team/config.yaml`. Extract `commit_strategy` (default `auto` if absent — emit WARNING). Read `.ai-team/changes/{change_name}/tasks.md` to identify all tasks in `group_id` and their declared `Files:` blocks.
3. Skill-first resolution: check `{project_root}/.claude/skills/commit/SKILL.md`, then `~/.claude/skills/commit/SKILL.md`. If found, load and apply its rules for commit message composition (REQ-WUC-008).
4. Compose commit message per REQ-WUC-005: `{type}({change_name}/G{N}): {description}` subject + `Covers: {REQ-list}` body. Subject MUST be ≤ 72 chars; truncate and emit WARNING if needed. No `Co-Authored-By`.
5. Collect file list: union of all `Files:` block paths for tasks in this group. Compare against `git diff --name-only HEAD`; emit WARNING for any diff file not in the declared list (do NOT stage undeclared files).
6. Dispatch to mode per Step 7.
7. **Mode dispatch:**
   - **7a (auto):** Stage each declared file: `git add {file}` (individually). Then `git commit -m "{message}"`. On failure: return `status: failed`, git output in `risks`. On success: capture SHA.
   - **7b (manual):** Compose `manual_commit` object: `{ message: "{message}", files: [...], commands: ["git add {f1}", "git add {f2}", "git commit -m '{message}'"] }`. Compose the command list and emit WARNING — the user must run these commands manually.
8. Update `state.yaml.phases.apply.commits[{group_id}]` — SHA string (auto) or `"manual-pending"` (manual). See [references/envelope-examples.md](references/envelope-examples.md) for state.yaml update examples.
9. Backfill SHA: for each `decisions[]` entry with `commits: []` where `task_ref` maps to a task in this group, set `commits: ["{sha}"]` (auto) or leave as `[]` (manual — user has not yet committed).
10. Return envelope per [references/envelope-examples.md](references/envelope-examples.md).

## Output Contract

Writes: git commit to working tree (auto mode); `state.yaml.phases.apply.commits[group_id]` (both modes). Returns envelope with: `mode` (MANDATORY), `commit_sha` (auto+ok only), `manual_commit` (manual+ok only), `group_id` (ok only), `risks` (WARNING entries for undeclared files, truncated subject, missing commit_strategy), `model_used`, `context_resolution`.

## References

- [references/envelope-examples.md](references/envelope-examples.md) — ok (auto), ok (manual), failed (hook reject), blocked (config missing) variants.
- [references/commit-message-examples.md](references/commit-message-examples.md) — pure feat, mixed feat+fix, project-skill override worked examples.
- [references/edge-cases.md](references/edge-cases.md) — pre-commit hook reject, file missing, merge conflict, undeclared file, skill contradiction, manual mode pending.
- `../_shared/common-rules.md` — consolidated principles (read-only, write-scope, envelope-always).
- `../_shared/context-protocol.md` — startup sequence.
- `../_shared/persistence-contract.md` — write rules, decisions[] schema, commits[] field.
- `../_shared/result-envelope.md` — envelope schema.
