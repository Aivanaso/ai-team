# Brief File — fixture group `ledger-report`

Negative fixture for the traversal arm of the `ledger[].report` containment
probe: `ledger[1].report` is a `../` chain, and this fixture is asserted with
`scripts/tests/fixtures` itself as project_root, so the chain resolves to the
repo's own `README.md` — a file that really EXISTS but lies OUTSIDE the
declared root (ELEVENTH citation-policy exception in this runner's header).
Citing an existing target is what makes the assertion discriminating: delete
the containment call and this fixture passes clean (0 violations) instead of
failing on a second, unrelated existence check.

## Ledger

```json
{
  "ledger": [
    { "n": 1, "agent": "organic-implementer", "model": "sonnet", "tokens": 50000, "tool_uses": 12, "duration_s": 300, "outcome": "ok" },
    { "n": 2, "agent": "organic-reviewer", "model": "opus", "tokens": 30000, "tool_uses": 8, "duration_s": 200, "outcome": "review-clear", "report": "../../../README.md" },
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
