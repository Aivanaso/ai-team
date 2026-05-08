# Edge Cases — sdd-apply

> Handling for non-happy-path situations. Load when an unexpected condition arises during execution.

## Resumed Execution

If `phases.apply.progress` exists in `state.yaml` with some tasks `done`:

1. Accept completed tasks as-is — do not re-implement them.
2. Quick-verify that their output files still exist (glob check).
3. If a completed task's files are missing → re-implement it (treat as pending).
4. Continue from the first non-done task.
5. Note in the result: "Resumed from task {id}. {N} tasks already completed."

An `active` entry at startup means the previous run was cut short mid-task. Treat `active` as pending — the task may be partially complete. Check whether its output files exist before deciding to skip or redo.

## Compilation Failure

If compilation fails after a task and two fix attempts are exhausted:

1. Read the error output carefully.
2. Common causes: missing import, wrong type, missing dependency, circular reference.
3. Fix attempt 1: address the specific error.
4. Fix attempt 2: if still failing, check whether the Implementation Notes were ambiguous.
5. If still failing after 2 attempts: mark task `failed`; add the error to `risks` in the result envelope.
6. Continue to the next independent task (if any). Dependent tasks are marked `skipped`.

Never spend more than 2 fix attempts per task — escalate to `failed` and move on.

## File Already Exists for CREATE

If a file that should be created already exists (possible partial prior run):

- Read the existing file to assess whether it was from a previous apply run.
- If it matches the expected implementation → mark as done, skip writing.
- If it is different (pre-existing code, not from apply) → return `status: warning` with details. Do not overwrite without logging a decision entry.

## Missing File for MODIFY

If a file listed as MODIFY does not exist:

- Check if it was renamed (grep for the class/function name in nearby files).
- If found renamed → note the drift, apply changes to the renamed file, log a decision entry.
- If not found → mark task `failed`, flag in result envelope.

## Circular Dependency at Runtime

If implementing task A requires code from task B that has not been written yet (should not happen with proper task ordering):

- Check if task B is earlier in the execution order (ordering bug in `tasks.md`).
- If so → implement B first, then A.
- If the dependency is truly circular → flag both tasks as `blocked` in the result envelope. Do not attempt implementation.

## No Verify Commands Configured

If `config.yaml` has no `verify`/`compile` commands and no `package.json` with type-check scripts:

- Skip compilation verification.
- Note the limitation in the result envelope: "No compilation verification available — manual check recommended."
- Still mark tasks as `done` (absence of verification is not a failure).

## Scope Limiting

When the orchestrator passes a `scope` parameter with specific task IDs:

- Only process the listed tasks.
- Still verify their dependencies are met (either `done` in `state.yaml` or `done` from this run).
- If a dependency is not met and not in scope → return `status: blocked`.
- Update `state.yaml` only for tasks in scope. Do not touch progress entries for out-of-scope tasks.
