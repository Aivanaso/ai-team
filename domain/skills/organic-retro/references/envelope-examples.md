# Envelope Examples — organic-retro

## `retro` mode — `ok`

```yaml
status: ok
executive_summary: "Retro for 2026-09-05-billing-export: 2 phases, 3 attempts, 1 friction (a mechanism approved as a decision), 1 convention proposed."
mode: retro
artifacts:
  - { name: "retro", path: ".ai-team/retros/2026-09-05-billing-export.md" }
conventions_proposed:
  - { rule: "a decision that names a function is a mechanism; rewrite it as the invariant it protects", why: "phase 2 needed a second attempt because the approved decision named Tax::round instead of the rounding invariant (tickets[t5], finding F-1)", good_example: "'an empty batch exports zero rows and exits 0' (design ## Decisiones, bullet 1)", bad_example: "'totals use Tax::round' (design ## Decisiones, bullet 3)", target: "_shared/cards/design.md#2", red: "evals/cases/design-mechanism-as-decision — the design card's self-review must reject the bullet" }
proposals_omitted: 0
next_recommended:
  - "apply C1 to _shared/cards/design.md if the user accepts it"
risks: []
model_used: "sonnet"
context_resolution: "self-loaded"
```

## `retro` mode — `warning`, provisional (task not yet `done`)

```yaml
status: warning
executive_summary: "Composed a PROVISIONAL retro for an active task (status: active, phase 2 of 3 implementing) at the user's request; re-run after `ai-team close` for the durable version."
mode: retro
artifacts:
  - { name: "retro", path: ".ai-team/retros/2026-09-05-billing-export.md" }
conventions_proposed: []
proposals_omitted: 0
next_recommended:
  - "re-run organic-retro (mode: retro) once the task is closed"
risks:
  - "task JSON status is 'active', not 'done' — Metrics reflect the settled tickets so far"
model_used: "sonnet"
context_resolution: "self-loaded"
```

## `retro` mode — `blocked`

```yaml
status: blocked
executive_summary: "Cannot compose the retro: the injected task_json path .ai-team/tasks/2026-09-05-billing-export.json does not exist."
mode: retro
artifacts: []
conventions_proposed: []
proposals_omitted: 0
next_recommended: []
risks:
  - "task_json unreadable — check the task id"
model_used: "sonnet"
context_resolution: "fallback"
```

## `conventions` mode — `ok`

```yaml
status: ok
executive_summary: "Drafted 1 convention proposal from the user's correction about scope-report checks."
mode: conventions
conventions_proposed:
  - { rule: "a linter is proposed as an acceptance check only when its config scope covers a file of the phase", why: "source_material: 'phpcs was green on every attempt and the changed files were never in its paths'", good_example: "scope report cites phpcs.xml:14 covering src/Billing/", bad_example: "phpcs proposed with no config citation", target: "organic-scout/SKILL.md#Hard Rules", red: "evals/cases/scope-check-cannot-fail" }
proposals_omitted: 0
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: "self-loaded"
```

## `conventions` mode — `needs_input`

```yaml
status: needs_input
executive_summary: "No source_material was injected; nothing to draw proposals from."
mode: conventions
questions:
  - "Which correction or friction should the proposals come from?"
conventions_proposed: []
proposals_omitted: 0
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: "fallback"
```
