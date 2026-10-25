# Envelope Examples — organic-retro

## `ok`

```yaml
status: ok
executive_summary: "Retro for 2026-09-05-billing-export: 2 phases, 3 attempts, 1 friction (a mechanism approved as a decision), scope framework."
artifacts:
  - { name: "retro", path: ".ai-team/retros/2026-09-05-billing-export.md" }
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: "self-loaded"
```

## `warning`, provisional (task not yet `done`)

```yaml
status: warning
executive_summary: "Composed a PROVISIONAL retro for an active task (status: active, phase 2 of 3 implementing) at the user's request; re-run after `ai-team close` for the durable version."
artifacts:
  - { name: "retro", path: ".ai-team/retros/2026-09-05-billing-export.md" }
next_recommended:
  - "re-run organic-retro once the task is closed"
risks:
  - "task JSON status is 'active', not 'done' — Metrics reflect the settled tickets so far"
model_used: "sonnet"
context_resolution: "self-loaded"
```

## `blocked`

```yaml
status: blocked
executive_summary: "Cannot compose the retro: the injected task_json path .ai-team/tasks/2026-09-05-billing-export.json does not exist."
artifacts: []
next_recommended: []
risks:
  - "task_json unreadable — check the task id"
model_used: "sonnet"
context_resolution: "fallback"
```
