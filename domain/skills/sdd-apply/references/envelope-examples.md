# Envelope Examples — sdd-apply

> Result envelope variants for sdd-apply. Load at the final step when building the return envelope.

## All Tasks Succeeded

```yaml
status: ok
executive_summary: "Applied 8/8 tasks for sdd-llm-first. 4 files created, 3 modified, 1 removed. All tasks compile successfully."
artifacts:
  - name: "state"
    path: ".ai-team/changes/sdd-llm-first/state.yaml"
next_recommended:
  - "verify"
model_used: "sonnet"
context_resolution: "injected"
```

## Tasks Completed With Warnings

```yaml
status: warning
executive_summary: "Applied 6/8 tasks for sdd-llm-first. 2 tasks failed: 3.2, 3.4. 4 files created, 2 modified, 0 removed."
artifacts:
  - name: "state"
    path: ".ai-team/changes/sdd-llm-first/state.yaml"
next_recommended:
  - "verify"
risks:
  - "Task 3.2 failed: TypeScript error TS2322 — type mismatch in UserService.create(). File: src/users/user.service.ts:47."
  - "Task 3.4 skipped: depends on failed task 3.2."
model_used: "sonnet"
context_resolution: "injected"
```

## Blocked

```yaml
status: blocked
executive_summary: "Cannot apply tasks — scope dependency not met. Task 4.1 requires task 3.2 (status: failed) which is not in current scope."
artifacts: []
next_recommended:
  - "Re-run apply with task 3.2 included in scope, or fix the failing task manually"
risks:
  - "Task 3.2 is failed; task 4.1 cannot proceed without it"
model_used: "sonnet"
context_resolution: "injected"
```
