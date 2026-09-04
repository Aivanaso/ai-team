# Brief File — fixture group `ledger-report`

Negative fixture for the `ledger[].report` suffix rule, and the positive for
the same field under `--legacy`: `ledger[1].report` cites the sibling fixture
`receipt-good.json`, a real, contained, on-disk file (ELEVENTH citation-policy
exception in this runner's header). Without `--legacy` the `.json` suffix is
its own violation and the file is never opened — exactly one violation. WITH
`--legacy` the same citation is legal and the whole ledger validates (exit 0),
which is also what makes this fixture discriminating: a deleted suffix guard
falls through to a clean pass instead of a second, unrelated violation.

## Ledger

```json
{
  "ledger": [
    { "n": 1, "agent": "organic-implementer", "model": "sonnet", "tokens": 50000, "tool_uses": 12, "duration_s": 300, "outcome": "ok" },
    { "n": 2, "agent": "organic-reviewer", "model": "opus", "tokens": 30000, "tool_uses": 8, "duration_s": 200, "outcome": "review-clear", "report": "scripts/tests/fixtures/receipt-good.json" },
    { "n": 3, "agent": "commit-step", "model": "sonnet", "tokens": 5000, "tool_uses": 3, "duration_s": 60, "outcome": "ok" }
  ],
  "close": {
    "delegations": 3,
    "subagent_tokens": 85000,
    "commits": ["a1b2c3d"],
    "re_briefs": 0
  }
}
```
