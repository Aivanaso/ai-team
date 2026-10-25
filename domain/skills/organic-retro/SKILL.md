---
name: organic-retro
description: "Trigger: orchestrator delegates the retro after a task is closed (ticket retro)."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run after `ai-team close` (ticket `retro`) or on an explicit request for a provisional retro.
Read the injected `task_json` (`.ai-team/tasks/<task>.json` — the machine's record: phases,
attempts, tickets with their figures, rulings, deferrals), the `design`, the `plan` and every
review report the tickets recorded, and compose a retrospective at `report_destination`. The
retro describes and cites: each friction carries its mechanism and a scope label, and the retro
ends there. The analysis, the watchlist count and any change happen afterwards in the ai-team
repository. The retro file is the only file written.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority, English — see `_shared/common-rules.md`.
- Metrics are copied verbatim from the task JSON's tickets — tokens, tool uses, duration, model, outcome, attempt — the only arithmetic is sums of those columns; a figure the JSON does not hold reads "not recorded".
- Describe: every friction states what happened (cited), the mechanism (what rule, artifact or moment let it happen) and `Scope: project | framework` — `framework` when the mechanism is a card, a skill, a protocol or a machine verb; `project` when it is the repository's tooling, convention or code. Language- and repo-specific detail is kept whole, never abstracted. -- because the scope label is what lets the reader of the retro route the friction.
- Frictions get equal or more space than "What worked"; every win cites its evidence (a ticket, a receipt verdict, a specific catch).
- Every claim cites its source — a JSON field (`tickets[t5].outcome`), a report path and finding id, a design decision, a `file:line`, or the `source_material`.
- Attempts are the first metric: attempts per phase, where each attempt's findings came from, whether findings decreased — that is what says whether the design or the implementer was at fault.
- The retro file is the only write.
- Git is for inspection only.

## Decision Gates

| Condition | Action |
|---|---|
| `task_json` missing or unreadable | `status: blocked`, cite the path. |
| `report_destination` missing | `status: blocked` — the file is the product. |
| `design` / `plan` / a review report path unreadable | proceed on the remaining evidence; note each unreadable path in `risks`. |
| The task JSON's `status` is not `done` | `status: warning`; compose it, header prefixed `PROVISIONAL — task not yet closed`. |

## Execution Steps

1. Read `_shared/context-protocol.md` and `_shared/persistence-contract.md`. Validate the injected fields (Decision Gates). Report `context_resolution`.
2. Read `task_json` in full — kind, phases (status, attempts, tier, commit, amendments), tickets (kind, phase, attempt, outcome, model, tokens, tool_uses, duration_s, report, verdict, findings, deferred), rulings. Then the design (`## Decisions`, `## Phases`), the plan, and every `tickets[].report` path.
3. Reconstruct the timeline per phase: attempt → implementer outcome → reviewer verdict and finding count → next attempt. Name where findings did not decrease, where a plan amendment happened, where a ruling was needed.
4. Draft per [references/retro-format.md](references/retro-format.md) — header, What worked, Frictions (numbered, mechanism + scope label), Metrics (the ticket table verbatim; totals; attempts per phase; deferred findings), Watch-items (questions for the next retro).
5. Write the retro file (one atomic write) at `report_destination`.
6. Return the envelope.

## Output Contract

```yaml
status: ok | warning | needs_input | blocked
executive_summary: "1-3 sentences"
questions: []
artifacts: [{ name: "retro", path: "<report_destination>" }]
next_recommended: []
risks: []
model_used: "sonnet"
context_resolution: self-loaded | fallback | none
```

## References

- [references/retro-format.md](references/retro-format.md) — the retro template.
- [references/envelope-examples.md](references/envelope-examples.md) — the retro envelopes.
- `../_shared/machine.md` — the task JSON's fields; load at Step 2.
- `../_shared/context-protocol.md`, `../_shared/persistence-contract.md`, `../_shared/common-rules.md` — startup, write rules, principles.
- `../_shared/result-envelope.md` — base envelope vocabulary.
- `../_shared/evidence-protocol.md` — Rule 1 (every claim cited).
