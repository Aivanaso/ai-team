# Envelope Examples — sdd-design

## Successful Design

```yaml
status: ok
executive_summary: "Technical design for {change-name}. {N} components across {M} domains. {Key design highlight}. {N} design decisions, {N} risks."
artifacts:
  - name: "design"
    path: ".ai-team/changes/{change-name}/design.md"
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "tasks"
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Design With Warnings

```yaml
status: warning
executive_summary: "Design for {change-name} complete but {concern}."
artifacts:
  - name: "design"
    path: ".ai-team/changes/{change-name}/design.md"
  - name: "state"
    path: ".ai-team/changes/{change-name}/state.yaml"
next_recommended:
  - "tasks"
risks:
  - "{specific concern}"
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Blocked

```yaml
status: blocked
executive_summary: "Cannot produce design — {reason}."
artifacts: []
next_recommended:
  - "{what needs to happen first}"
risks:
  - "{blocker details}"
model_used: "{resolved-model}"
context_resolution: "injected"
```
