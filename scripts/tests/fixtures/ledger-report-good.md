# Brief File — fixture group `ledger-report`

Positive fixture for `ledger[].report`: a `.md` citation resolving to a real
regular file contained under project_root (README.md, the ordinary citation
policy), on a ledger that is otherwise the `ledger-good` shape. The report's
own content is never opened in ledger mode — this pins the citation check, not
a nested receipt validation.

## Ledger

```json
{
  "ledger": [
    { "n": 1, "agent": "organic-implementer", "model": "sonnet", "tokens": 50000, "tool_uses": 12, "duration_s": 300, "outcome": "ok" },
    { "n": 2, "agent": "organic-reviewer", "model": "opus", "tokens": 30000, "tool_uses": 8, "duration_s": 200, "outcome": "review-clear", "report": "README.md" },
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
