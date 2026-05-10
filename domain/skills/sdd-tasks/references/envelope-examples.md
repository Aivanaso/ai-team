# Envelope Examples — sdd-tasks

## Successful Task Plan

```yaml
status: ok
executive_summary: "Task plan for {change-name}. {N} tasks in {M} groups. {new} new files,
  {mod} modified, {del} removed. Full traceability: {AC-count} ACs -> {REQ-count} REQs
  -> {N} tasks."
artifacts:
  - name: "tasks"
    path: ".ai-team/changes/{change-name}/tasks.md"
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
review_workload:
  cohesion_risk: low|medium|high
  features_count: {count}
  independent_prs: {count}
  chained_prs: {count}
  decision_needed_before_apply: true|false
  size_smells:
    - feature: {name}
      lines: {N}
next_recommended:
  - "apply"
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Task Plan With Warnings

```yaml
status: warning
executive_summary: "Task plan for {change-name} complete but {concern}. {N} tasks in {M} groups."
artifacts:
  - name: "tasks"
    path: ".ai-team/changes/{change-name}/tasks.md"
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "apply"
risks:
  - "{specific concern — drift, missing tests, large task count}"
review_workload:
  cohesion_risk: medium
  features_count: 1
  independent_prs: 1
  chained_prs: 0
  decision_needed_before_apply: false
  size_smells:
    - feature: "main-feature"
      lines: 850
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Blocked

```yaml
status: blocked
executive_summary: "Cannot produce task plan — {reason}."
artifacts: []
next_recommended:
  - "{what needs to happen first}"
risks:
  - "{blocker details}"
model_used: "{resolved-model}"
context_resolution: "injected"
```
