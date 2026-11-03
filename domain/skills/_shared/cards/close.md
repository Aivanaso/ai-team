# Card: close

> Read when: every phase is `committed`, or the task is already `done`.

```
ai-team close
```
Refused while a ticket is open or a phase is not committed — finish those first.

Close succeeds when every finding of each phase's final-attempt lens receipt (reviewer,
security-audit) is fixed, deferred or ruled. A deferral is recorded at the lens's settle
(`ai-team settle <ticket> --defer <id>`), which has already passed at close; an undisposed
finding of any severity is refused by id, and the verb available now is
`ai-team ruling <ticket> --finding <id> --text "..." --cost-if-wrong "..."`.

## Report the balance

`ai-team status --json` before closing, or the `close` output: tickets, tokens, tool uses,
duration, attempts per phase, commits. Plain words, the user's language. This balance is the
instrument that tells whether fewer rules worked better; every figure reaches the user.

## Retro

`.ai-team/config.yaml → retro`:

| Value | Action |
|---|---|
| `always` | `ai-team acquire retro`, then delegate `organic-retro` (sonnet · medium) |
| `on-signal` (default) | only when the task had ≥2 attempts on a phase, an `infra-death`, a `review-blocked` (a CRITICAL; `review-gated` does not count), or one ticket above 300k tokens |
| `off` | none |

Inject: `task_json` (`.ai-team/tasks/<task>.json`), `design`, `plan`, every report path the
tickets recorded, `report_destination: .ai-team/retros/<task>.md`. The retro copies the JSON's
figures verbatim. The retro describes and cites; it proposes nothing. It is read in the
ai-team repository, where its frictions are counted in the watchlist and a pattern seen twice
becomes a change.

## Deferred findings

Rows left `open` in `.ai-team/tech-debt.md` are the next tasks' candidates. Closing one later
is a bounded task or a phase of a design; its commit flips the row (`ai-team debt fix`).
