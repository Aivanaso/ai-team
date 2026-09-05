# Card: close

> Read when: every phase is `committed`, or the task is already `done`.

```
ai-team close
```
Refused while a ticket is open or a phase is not committed — finish those first.

## Report the balance

`ai-team status --json` before closing, or the `close` output: tickets, tokens, tool uses,
duration, attempts per phase, commits. Plain words, the user's language. This balance is the
instrument that tells whether fewer rules worked better — do not summarise it away.

## Retro

`.ai-team/config.yaml → retro`:

| Value | Action |
|---|---|
| `always` | `ai-team acquire retro`, then delegate `organic-retro` (mode `retro`, sonnet · medium) |
| `on-signal` (default) | only when the task had ≥2 attempts on a phase, an `infra-death`, a `review-blocked`, or one ticket above 300k tokens |
| `off` | none |

Inject: `task_json` (`.ai-team/tasks/<task>.json`), `design`, `plan`, every report path the
tickets recorded, `report_destination: .ai-team/retros/<task>.md`. The retro reads the JSON's
figures verbatim, never recomputes. Its `conventions_proposed` are proposals: the user or you
apply one as a trivial edit, or leave it.

## Deferred findings

Rows left `open` in `.ai-team/tech-debt.md` are the next tasks' candidates. Closing one later
is a bounded task or a phase of a design; its commit flips the row (`ai-team debt fix`).
