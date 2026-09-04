# Brief File — fixture group `open-ledger`

Negative fixture: `--open` relaxes the `close is required` rule and NOTHING
else. `ledger[1].tokens` is the string `"60000"` instead of an integer, so the
unconditional per-row shape rules must still fire under `--open` — exactly one
violation, isolating that single rule (no `close`, so no Close-time rule can
mask it).

## Ledger

```json
{
  "ledger": [
    { "n": 1, "agent": "organic-scout", "model": "sonnet", "tokens": 40000, "tool_uses": 9, "duration_s": 240, "outcome": "ok" },
    { "n": 2, "agent": "organic-implementer", "model": "opus", "tokens": "60000", "tool_uses": 15, "duration_s": 420, "outcome": "ok" }
  ]
}
```
