# Brief File — fixture group `open-ledger`

Negative fixture: under `--open` a `close` object is optional, but a `close`
that IS present validates exactly as it does without the flag. Here
`close.commits` is an empty list, so the unconditional "at least 1 entry"
floor fires — exactly one violation (`delegations` and `subagent_tokens` match
the ledger rows, and `plan` is absent, so nothing else can fire).

## Ledger

```json
{
  "ledger": [
    { "n": 1, "agent": "organic-scout", "model": "sonnet", "tokens": 40000, "tool_uses": 9, "duration_s": 240, "outcome": "ok" },
    { "n": 2, "agent": "organic-implementer", "model": "opus", "tokens": 60000, "tool_uses": 15, "duration_s": 420, "outcome": "ok" }
  ],
  "close": {
    "delegations": 2,
    "subagent_tokens": 100000,
    "commits": [],
    "re_briefs": 0
  }
}
```
