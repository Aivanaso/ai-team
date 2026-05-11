# Task Execution Loop — sdd-apply

> Detailed prose for Steps 3a-3f. Load when executing the per-task loop.

## Step 3a — Gate Check

Before touching any file, verify the task is eligible to run:

- **Skip if already `done`** in `state.yaml.phases.apply.progress`. Quick-verify that the task's output files still exist (glob check). If missing, re-implement (treat as pending).
- **Skip if not in `scope`** when the orchestrator provided a scope list of task IDs.
- **Check dependencies:** all tasks listed in the `Depends On` column must be `done`. If a dependency is `failed`, check whether this task can proceed independently (different file set). If it cannot, skip and mark it `skipped` in state.yaml.

## Step 3b — State Update

Write the task status to `state.yaml` before touching any file:

```yaml
phases:
  apply:
    status: active
    started: "{timestamp}"
    agent: sdd-apply
    progress:
      "{task-id}": active
```

This enables safe resume after interruption — an `active` entry at startup means the previous run was cut short.

## Step 3c — Implementation Order

Process files within a task in this dependency order:

1. Types / interfaces
2. Entities / domain models
3. DTOs / value objects
4. Services
5. Controllers
6. Modules / registrations
7. Pages / views (frontend)
8. Tests

**For CREATE files:**
1. Read the task's Implementation Notes for this file (signatures, patterns, key logic).
2. Write the complete file following: Implementation Notes (WHAT) + skill conventions (HOW — naming, imports, patterns) + project conventions from `config.yaml`.
3. Include all necessary imports.
4. Add JSDoc/PHPDoc only where logic is non-obvious. Do not over-document.

**For MODIFY files:**
1. Read the current file in full.
2. Read the task's Implementation Notes for the changes.
3. Apply the specified changes: ADD inserts new code at the appropriate location; REMOVE deletes specified code blocks; CHANGE replaces specified code with the new version.
4. Preserve existing code structure, formatting, and style.
5. Update imports as needed (add new, remove unused).

**For REMOVE files:**
1. Delete the file. No need to read it first.

## Step 3d — Compilation Verification

After all files in the task are written, run the project's compile command:

- **TypeScript projects:** `npx tsc --noEmit` or the compile command from `config.yaml`.
- **PHP projects:** `php -l` on modified files or the lint command from `config.yaml`.
- **Other stacks:** use the `verify` command from `config.yaml`, or check for a `build` / `typecheck` script in `package.json`.

**On pass:** mark task as `done` in `state.yaml`. Move to next task.

**On fail:**
1. Read the error output.
2. Identify the cause (missing import, type mismatch, syntax error).
3. Fix the issue in the relevant file.
4. Re-run compilation.
5. If it passes on second attempt → mark `done`, move on.
6. If it fails again → mark task as `failed` in `state.yaml`, record the error.
   - If the next task does NOT depend on this one → continue.
   - If the next task depends on this one → skip dependent tasks, flag in result.

## Step 3e — Group boundary detection and hand-off

1. Detect last-task-in-group per `_shared/common-rules.md` "Logical group" rule: if the next row in tasks.md Execution Order table belongs to a different group, this task is the last in the current group.
2. (3e.1) Run group informational tests: if any task in the group created scaffold files, run those test files only (not the full suite). Use the project's test runner from `config.yaml`. Failures produce warnings, not blockers — sdd-verify is authoritative.
3. (3e.2) Update state.yaml: set `phases.apply.progress[{group_id}] = done`. The group_id is the literal string "G1", "G2", etc. from the Execution Order table.
4. (3e.3) Return control to the orchestrator. NEVER run `git commit`. The orchestrator will invoke `work-unit-commits` per REQ-ORCHESTRATOR-010.
5. Watchdog-resilience: the `progress[group_id] = done` marker is durable; a resumed run reads it and skips re-execution.

## Step 3f — Progress Update

After each task completes (pass or fail), update `phases.apply.progress` in `state.yaml`:

```yaml
phases:
  apply:
    progress:
      "{task-id}": done    # or: failed / skipped
```

## Drift Detection

If a MODIFY target has changed since the design phase:

| Severity | Condition | Action |
|----------|-----------|--------|
| **None** | All files match expectations | Proceed normally |
| **Minor** | Cosmetic changes or new unrelated files | Note in result, proceed |
| **Moderate** | File content changed (new methods, reordered code) | Read current version before modifying, adapt implementation |
| **Severe** | File deleted or module restructured | Return `status: warning` with drift details. Apply non-affected tasks normally |
