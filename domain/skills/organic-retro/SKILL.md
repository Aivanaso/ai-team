---
name: organic-retro
description: "Trigger: orchestrator delegates retro mode after a task is closed (ticket retro), or conventions mode on correction/friction input."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run after `ai-team close` (ticket `retro`) or on an explicit request for a provisional retro.
Two modes. **`retro`** reads the injected `task_json` (`.ai-team/tasks/<task>.json` — the
machine's record: phases, attempts, tickets with their figures, rulings, deferrals), the
`design`, the `plan` and every review report the tickets recorded, and composes a
retrospective at `report_destination`; when a friction yields a reusable convention it also
drafts a "Conventions proposed" section. **`conventions`** composes PROPOSED convention entries
from injected `source_material` and writes nothing. Neither mode writes application code,
`CLAUDE.md`, `AGENTS.md`, or any config file — proposals are for the orchestrator or the user.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Metrics are copied verbatim from the task JSON's tickets — tokens, tool uses, duration, model, outcome, attempt — never recomputed beyond sums of those columns, never estimated; a figure the JSON does not hold is "not recorded", not a guess.
- Explain, do not describe: every friction states the mechanism (what rule, artifact or moment let it happen) and one concrete proposal; a retro that lists events is not a retro.
- Frictions get equal or more space than "What worked"; every win cites its evidence (a ticket, a receipt verdict, a specific catch), never an adjective.
- Every claim cites its source — a JSON field (`tickets[t5].outcome`), a report path and finding id, a design decision, a `file:line`, or the `source_material`.
- Attempts are the first metric: attempts per phase, where each attempt's findings came from, whether findings decreased — that is what says whether the design or the implementer was at fault.
- Writes only its own retro file, in `retro` mode; `conventions` mode writes nothing.
- A proposed convention names its RED: the scenario under which the next eval (`evals/`) would catch the friction recurring. -- because a rule without a failing test is prose.
- Read-only otherwise: no state-changing git commands.

## Decision Gates

| Condition | Action |
|---|---|
| `mode: retro` AND `task_json` missing or unreadable | `status: blocked`, cite the path. |
| `mode: retro` AND `report_destination` missing | `status: blocked` — the file is the product. |
| `mode: retro` AND `design` / `plan` / a review report path unreadable | proceed on the remaining evidence; note each unreadable path in `risks`. |
| `mode: retro` AND the task JSON's `status` is not `done` | `status: warning`; compose it, header prefixed `PROVISIONAL — task not yet closed`. |
| `mode: conventions` AND `source_material` absent or empty | `status: needs_input`. |
| `mode` not `retro` / `conventions` | `status: blocked`, "Invalid mode: '{value}'." |

## Execution Steps

1. Read `_shared/context-protocol.md` and `_shared/persistence-contract.md`. Identify `mode`; validate its fields (Decision Gates). Report `context_resolution`.
2. `retro`: read `task_json` in full — kind, phases (status, attempts, tier, commit, amendments), tickets (kind, phase, attempt, outcome, model, tokens, tool_uses, duration_s, report, verdict, findings, deferred), rulings. Then the design (`## Decisiones`, `## Fases`), the plan, and every `tickets[].report` path.
3. `retro`: reconstruct the timeline per phase: attempt → implementer outcome → reviewer verdict and finding count → next attempt. Name where findings did not decrease, where a plan amendment happened, where a ruling was needed.
4. `retro`: draft per [references/retro-format.md](references/retro-format.md) — header, What worked, Frictions (numbered, mechanism + proposal), Metrics (the ticket table verbatim; totals; attempts per phase; deferred findings), Watch-items (questions for the next retro).
5. `retro`: scan the Frictions for reusable conventions; for each, a `conventions_proposed` entry (rule, why, good/bad example cited, target file+section, RED scenario) and the "Conventions proposed" section.
6. `conventions`: one entry per distinct candidate in `source_material`, same shape; no retro, nothing written.
7. `retro`: write the retro file (one atomic write) at `report_destination`.
8. Return the envelope.

## Output Contract

```yaml
status: ok | warning | needs_input | blocked
executive_summary: "1-3 sentences"
mode: retro | conventions
questions: []
artifacts: [{ name: "retro", path: "<report_destination>" }]   # retro mode only
conventions_proposed:            # CAP 10 — [] when none
  - { rule: "<one line>", why: "<one line>", good_example: "<cited>", bad_example: "<cited>", target: "<file#section>", red: "<the eval scenario that would catch a recurrence>" }
proposals_omitted: 0
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded | fallback | none
```

## References

- [references/retro-format.md](references/retro-format.md) — the retro template and the conventions-proposal shape.
- [references/envelope-examples.md](references/envelope-examples.md) — envelopes per mode.
- `../_shared/machine.md` — the task JSON's fields; load at Step 2.
- `../_shared/context-protocol.md`, `../_shared/persistence-contract.md`, `../_shared/common-rules.md` — startup, write rules, principles.
- `../_shared/result-envelope.md` — base envelope vocabulary.
- `../_shared/evidence-protocol.md` — Rule 1 (every claim cited).
