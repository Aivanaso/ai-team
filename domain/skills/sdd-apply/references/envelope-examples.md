# Envelope Examples — sdd-apply

> Result envelope variants for sdd-apply. Load at the final step when building the return envelope.

## All Tasks Succeeded

```yaml
status: ok
executive_summary: "Applied 8/8 tasks for sdd-llm-first. 4 files created, 3 modified, 1 removed. All verify commands passed. Typecheck: exit 0. Lint: exit 0. 2 test files created, both green."
artifacts:
  - name: "state"
    path: ".ai-team/changes/sdd-llm-first/state.yaml"
next_recommended:
  - "verify"
execution_evidence:
  typecheck:
    command: "<typecheck command from config.yaml>"
    exit_code: 0
    last_lines: |
      Found 0 errors in 12 files.
  lint:
    command: "<lint command from config.yaml>"
    exit_code: 0
    summary: "0 errors, 0 warnings"
  tests_created:
    - file: "src/auth/auth.service.spec.ext"
      command: "<test runner from config.yaml> src/auth/auth.service.spec.ext"
      exit_code: 0
      passed: 4
      failed: 0
    - file: "src/auth/auth.guard.spec.ext"
      command: "<test runner from config.yaml> src/auth/auth.guard.spec.ext"
      exit_code: 0
      passed: 2
      failed: 0
model_used: "sonnet"
context_resolution: "injected"
```

## Tasks Completed With Warnings (red test)

```yaml
status: warning
executive_summary: "Applied 7/8 tasks. Task 3.2 is partial — created test file has 1 failing assertion. Task 3.4 skipped: depends on partial task 3.2. Typecheck: exit 0. Lint: exit 0."
artifacts:
  - name: "state"
    path: ".ai-team/changes/sdd-llm-first/state.yaml"
next_recommended:
  - "verify"
risks:
  - "Task 3.2 partial: src/users/user.service.spec.ext — 1 test failing (exit_code: 1, passed: 3, failed: 1). Test stdout in execution_evidence."
  - "Task 3.4 skipped: depends on partial task 3.2."
execution_evidence:
  typecheck:
    command: "<typecheck command from config.yaml>"
    exit_code: 0
    last_lines: |
      Found 0 errors.
  lint:
    command: "<lint command from config.yaml>"
    exit_code: 0
    summary: "0 errors, 0 warnings"
  tests_created:
    - file: "src/users/user.service.spec.ext"
      command: "<test runner from config.yaml> src/users/user.service.spec.ext"
      exit_code: 1
      passed: 3
      failed: 1
model_used: "sonnet"
context_resolution: "injected"
```

## Blocked (verify command failed, unresolvable)

```yaml
status: blocked
executive_summary: "Cannot complete apply — typecheck command from config.yaml exited non-zero after 2 fix attempts. Blocked at task 4.1. Remaining tasks not attempted."
artifacts:
  - name: "state"
    path: ".ai-team/changes/sdd-llm-first/state.yaml"
next_recommended:
  - "Re-run apply after resolving the typecheck failure listed in execution_evidence"
risks:
  - "Task 4.1 blocked by persistent typecheck failure (exit_code: 1). See execution_evidence.typecheck.last_lines for details."
execution_evidence:
  typecheck:
    command: "<typecheck command from config.yaml>"
    exit_code: 1
    last_lines: |
      error: type mismatch at src/payments/payment.service.ext:47
      Expected: string
      Got: number
      (2 attempts — could not resolve)
model_used: "sonnet"
context_resolution: "injected"
```
