# Brief File — fixture group `open-ledger`

Positive fixture for `ledger --open`: an IN-PROGRESS Brief File. Its ledger
carries two real rows and its `## Plan` mirror carries two entries that are
NOT done — and there is no `close` object at all, because the objective has
not closed yet. Under `--open` that is exactly what a valid in-progress Brief
File looks like (exit 0); WITHOUT `--open` the same file is the negative that
proves the flag is load-bearing — one violation, `close is required`.

## Plan

1. Validator: `--legacy`, `--open`, `report`
2. Gate script and hooks

## Ledger

```json
{
  "ledger": [
    { "n": 1, "agent": "organic-scout", "model": "sonnet", "tokens": 40000, "tool_uses": 9, "duration_s": 240, "outcome": "ok" },
    { "n": 2, "agent": "organic-implementer", "model": "opus", "tokens": 60000, "tool_uses": 15, "duration_s": 420, "outcome": "ok" }
  ],
  "plan": [
    { "n": 1, "title": "Validator: --legacy, --open, report", "done": false },
    { "n": 2, "title": "Gate script and hooks", "done": false }
  ]
}
```
