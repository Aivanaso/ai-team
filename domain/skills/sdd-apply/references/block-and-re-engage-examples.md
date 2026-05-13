# Block-and-Re-engage Examples — sdd-apply

> Worked examples of `deviation_report` blocks. Load when you need to compose a
> `deviation_report` in a blocked envelope. Do NOT author audit-trail entries.

These examples illustrate the three deviation triggers: out-of-plan, design-pivot, and
test-orphan. Each shows the `deviation_report` block in the apply envelope.

---

## Example 1 — Out-of-Plan Fix (`kind: "out-of-plan"`)

**Scenario:** While implementing Task 2.3, the agent discovers that `scripts/install.sh`
swallows a copy exit code. This is not in any task; the agent cannot self-resolve.

```yaml
status: blocked
executive_summary: "Blocked at T2.3: discovered out-of-plan structural issue in scripts/install.sh. Apply cannot self-resolve; orchestrator action required."
tasks_status:
  completed: ["T1.1", "T1.2", "T2.1", "T2.2"]
  partial: []
  skipped: ["T2.3"]
execution_evidence:
  typecheck:
    command: "<from config.yaml>"
    exit_code: 0
    last_lines: "..."
deviation_report:
  kind: out-of-plan
  task_ref: "T2.3"
  evidence:
    file: "scripts/install.sh"
    line: 47
    command: "grep -n '2>/dev/null' scripts/install.sh"
    output: "47: cp -R \"$dir.\" \"$dest/\" 2>/dev/null   # exit code swallowed"
  suggested_action: re-engage-apply-refined
next_recommended:
  - "orchestrator-audit"
```

The orchestrator inspects the evidence, decides: if drift is mechanical and scoped, it
authors a `decisions[]` entry and re-engages apply with the approved fix inlined. If scope
creep is ambiguous, it escalates to the user.

---

## Example 2 — Design Pivot (`kind: "design-pivot"`)

**Scenario:** Task 3.1 requires a class that depends on a service the actual config does not
provide. Evidence Protocol Rule 1: design.md made an assumption not backed by a config line.

```yaml
status: blocked
executive_summary: "Blocked at T3.1: design.md assumption about service availability does not hold. Apply cannot self-resolve; orchestrator should re-engage sdd-design."
tasks_status:
  completed: ["T1.1", "T2.1", "T3.1"]
  partial: ["T3.1"]
  skipped: ["T3.2"]
execution_evidence:
  typecheck:
    command: "<from config.yaml>"
    exit_code: 1
    last_lines: "Error: Cannot find module '@/services/FooService'"
deviation_report:
  kind: design-pivot
  task_ref: "T3.1"
  evidence:
    file: "config/services.yaml"
    line: 12
    command: "grep -n 'FooService' config/services.yaml"
    output: "(no matches) — FooService is not registered"
  suggested_action: re-engage-design
next_recommended:
  - "orchestrator-audit"
```

The orchestrator re-engages sdd-design with the failed assumption inlined. Design re-emits
`design.md`; downstream tasks/apply rerun.

---

## Example 3 — Test Orphan (`kind: "test-orphan"`)

**Scenario:** Task 2.3 creates a test file. The test references `MissingService` which does
not exist in the system. No REQ in tasks.md justifies adding the entity.

```yaml
status: blocked
executive_summary: "Blocked at T2.3: test scaffold references MissingService which is absent from the system. Apply cannot self-resolve; orchestrator should re-engage sdd-tasks."
tasks_status:
  completed: ["T1.1", "T1.2", "T2.1", "T2.2"]
  partial: []
  skipped: ["T2.3", "T2.4"]
execution_evidence:
  typecheck:
    command: "<from config.yaml>"
    exit_code: 0
    last_lines: "..."
  tests_created:
    - file: "src/feature/missing-service.spec.ts"
      command: "<test runner cmd>"
      exit_code: 1
      passed: 0
      failed: 1
deviation_report:
  kind: test-orphan
  task_ref: "T2.3"
  evidence:
    file: "src/feature/missing-service.spec.ts"
    line: 14
    command: "grep -rn 'MissingService' src/"
    output: "1 match — only in the test file itself; no implementation found"
  suggested_action: re-engage-tasks
next_recommended:
  - "orchestrator-audit"
```

The orchestrator re-engages sdd-tasks with the failed test + grep result inlined. Tasks
re-evaluates: (a) the test is wrong → correct the scaffold; (b) the entity should exist
(REQ justifies it) → expand scope; (c) spec ambiguous → return needs_input.

---

## When NOT to Block

Trivial corrections within the bounds of a task do NOT require a deviation_report block:

- Fixing a typo in a variable name caught immediately.
- Adding a missing semicolon found by the compiler.
- Reordering imports to satisfy linting rules.
- Adjusting whitespace / line endings.

The bar is: **"does this deviate from the approved plan?"** If yes, block. If it's mechanical
correction within the task bounds, handle inline.
