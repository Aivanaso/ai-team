# Card: ingest

> Read when: a ticket is open and the sub-agent has returned.

An envelope is a **claim**, not proof. Before settling:

- `ok` / `warning`: confirm each `artifacts` path exists under the project root; `git status
  --porcelain` shows only expected files (a stray path is scope creep to name).
- A report was expected (scout, lenses): the file exists at the injected destination.

## Settle — always, immediately, with the harness figures

```
ai-team settle <ticket> --outcome <ok|warning|needs_input|blocked|failed|infra-death> \
  --model <alias> --tokens <n> --tool-uses <n> --duration <seconds> [--report <path.md>]
```
The `Agent` tool result reports tokens, tool uses and duration — copy them, never estimate.
A death without an envelope is `infra-death` (no figures; it does not count as an attempt):
verify the tree with `git status`, then relaunch the same prompt.

## Route by outcome

| Outcome | Next |
|---|---|
| `ok` / `warning` (checks failed but pre-existing, evidence cited) | card: review |
| `needs_input` | the questions to the user, in their language; then the next attempt with the answers |
| `blocked` + `scope_report` | a plan defect: `ai-team plan amend --phase n --reason …` (card: plan), then the next attempt |
| `failed` | read the cause; next attempt with it named; two in a row → tell the user |
| scout / security report | settle with `--report`; the machine records it |

## Reporting to the user

1. Their language; plain words; at most one technical term per sentence.
2. Every item names its origin: the phase, the report and finding id, the decision.
3. Two or three options at most, each with a cost, one recommendation stated as such.
4. The complete record stays in the reports and the task JSON; the message summarises.

A worker's vocabulary (`review-blocked`, `evidence: executed`) is translated, never pasted.
