# Retro Format

The template `organic-retro` (`retro` mode) fills in when composing the retro file at the
injected `report_destination` — convention `.ai-team/retros/<task>.md`, the same task id as
`.ai-team/tasks/<task>.json`. Every section is evidence, not memory: a claim with no citable
source (a task JSON field, a design decision, a report path and finding id, or `file:line`)
does not go in.

## Header

```markdown
# Retro — {task id} — {design title, or the plan's title for a bounded task}

**Date**: {current_iso_utc date}
**Kind**: {bounded | large} · **Phases**: {N} · **Attempts**: {sum of phases[].attempts}
**Result**: {done | PROVISIONAL — task not yet closed} — {commits, one per phase; the balance line}
```

When the task JSON's `status` is not `done` (Decision Gates warning row), the Result line reads
`PROVISIONAL — task not yet closed` and no commit list is claimed.

## What worked

- One item per grounded win — a reviewer verdict on the first attempt, a hook denial that
  redirected a launch, a scout gotcha that became a decision, a threat-model requirement the
  audit later found implemented.
- One short paragraph each, citing its evidence: `tickets[t3].verdict`, `.ai-team/reviews/<file>
  finding F-N`, a design decision quoted, `file:line`.
- No adjective without a citation — "worked well" is not a claim; "review-clear on attempt 1,
  `tickets[t3]`" is.

## Frictions

- **Equal or more space than "What worked".** This section is where the retro earns its keep.
- Numbered (F1, F2, …) so Watch-items can reference them.
- Each friction: what happened (cited) → **the mechanism** — which rule, artifact or moment
  let it happen (a decision that was really a mechanism, a scope pass skipped, a check that
  could not fail, findings that did not decrease) → one concrete proposal. Attempts are the
  first place to look: every attempt beyond the first has a cause, and the cause is either the
  design (the constraint was wrong or missing), the plan (a file or check was missing) or the
  worker.

## Metrics

Copied from the task JSON — never recomputed beyond sums of its columns, never estimated.

- **Tickets** — one row per settled ticket, verbatim:

  | id | kind | phase | attempt | model | tokens | tool uses | duration | outcome / verdict |
  |---|---|---|---|---|---|---|---|---|

- **Attempts per phase** — `phases[].attempts`, and for each attempt beyond 1 the reviewer's
  finding count, so the trend is visible (decreasing / not).
- **Rulings** — `rulings[]`, each with its finding and cost-if-wrong quoted.
- **Deferred** — every `tickets[].deferred` id, with its `tech-debt.md` row.
- **Amendments** — `phases[].amendments[]`, each reason quoted: these are plan defects.
- **Totals** — tokens, tool uses, duration summed over the settled tickets; commits per phase.

A figure the JSON does not hold (e.g. an `infra-death` ticket's tokens) is written "not
recorded", never guessed.

## Watch-items for the next task

- One line per item, phrased as a question the *next* retro should answer, tied to a friction
  number: `"F2 — did the scope pass name the construction sites this time?"`.

## Conventions proposed

Present only when a friction yields a reusable rule. Per entry (mirrors the envelope's
`conventions_proposed` shape):

```markdown
### C1 — {rule, one line}
**Why**: {one line, cites the friction}
**Good**: {an example from this task, cited}
**Bad**: {the counter-example from this task, cited}
**Target**: {file#section — a card, a skill, a protocol}
**RED**: {the eval scenario under evals/ that would catch a recurrence}
```

## Compact worked example

```markdown
# Retro — 2026-09-05-billing-export — Billing export endpoint

**Date**: 2026-09-05
**Kind**: large · **Phases**: 2 · **Attempts**: 3
**Result**: done — a1b2c3d (phase 1), d4e5f6a (phase 2) · 5 tickets · 312,000 tokens

## What worked
- The scope pass named `services/billing/tax.py` as a construction site
  (`.ai-team/explorations/…-scope.md` phase 1), so the implementer never blocked on it
  (`tickets[t2].outcome: ok`).

## Frictions
1. **F1 — attempt 2 on phase 2 for a constraint that was a mechanism.** The design's decision
   "totals are rounded with `Tax::round`" named a helper, not an invariant; the implementer used
   it, the reviewer flagged a rounding defect in a path the helper never covered
   (`…-phase-2-attempt-1-reviewer.md` F-1, CRITICAL). Mechanism: the decision test (card:
   classify) was not applied at approval. Proposal: the design card's self-review names the
   decision test explicitly.

## Metrics
| id | kind | phase | attempt | model | tokens | tool uses | duration | outcome / verdict |
|---|---|---|---|---|---|---|---|---|
| t1 | scout-scope | – | – | sonnet | 40,000 | 22 | 180s | ok |
| t2 | implementer | 1 | 1 | sonnet | 90,000 | 31 | 400s | ok |
| t3 | reviewer | 1 | 1 | sonnet | 52,000 | 18 | 210s | ok / review-clear |
| … | | | | | | | | |

Attempts per phase: phase 1 → 1; phase 2 → 2 (findings 3 → 0).

## Watch-items
- F1 — did every approved decision pass the rewrite test this time?

## Conventions proposed
### C1 — A decision that names a function is a mechanism; rewrite it as the invariant it protects
**Why**: F1. **Good**: "an empty batch exports zero rows and exits 0". **Bad**: "totals use `Tax::round`".
**Target**: `_shared/cards/design.md#2`. **RED**: `evals/cases/design-mechanism-as-decision`.
```
