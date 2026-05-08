# Result Envelope Examples — sdd-archive

> Loaded by sdd-archive Step 6. Contains YAML envelope variants for successful archive and blocked scenarios.

## Successful Archive

```yaml
status: ok
executive_summary: "Archived {change-name}. Merged delta specs for {N} domain(s) into base specs. Artifacts preserved in .ai-team/changes/archive/YYYY-MM-DD-{change-name}/. {N} memory candidates surfaced for orchestrator review."
artifacts:
  - name: "archive"
    path: ".ai-team/changes/archive/YYYY-MM-DD-{change-name}/"
  - name: "base-spec-{domain}"
    path: ".ai-team/specs/{domain}/spec.md"
next_recommended: []
memory_candidates:
  - type: "{user|feedback|project|reference}"
    title: "{short title}"
    body: "{the memory content}"
    rationale: "{where it was surfaced from -- design DD-N, decisions entry, etc.}"
    surface: "{external_dependencies|env_quirks|conventions|decisions|smoke_canaries}"
  # Or empty list if nothing capture-worthy was found
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Blocked

```yaml
status: blocked
executive_summary: "Cannot archive -- {reason}."
artifacts: []
next_recommended:
  - "{what needs to happen first}"
risks:
  - "{blocker details}"
memory_candidates: []
model_used: "{resolved-model}"
context_resolution: "injected"
```

## Notes

- `memory_candidates:` MUST always be present in the envelope (possibly empty list `[]`). The orchestrator depends on this field.
- On PASS WITH WARNINGS, carry verification warnings into `risks:` of the envelope.
- `next_recommended: []` on success — archive is the terminal phase.
- `context_resolution` is `"injected"` when the orchestrator passed context via `## Injected Context` block; `"fallback"` if recovered from `state.yaml`.
