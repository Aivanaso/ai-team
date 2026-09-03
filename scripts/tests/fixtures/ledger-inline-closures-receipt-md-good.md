# Brief File — fixture group `md-container-ledger`

Positive fixture, both halves of the Markdown container at once: this file is a
`.md` LEDGER (so the CLI-argument loader must extract its block) whose
`close.inline_closures[0].receipt` cites a `.md` RECEIPT (so the widened
extension guard must accept it and the cited-receipt loader must extract that
file's block in turn). Its block mirrors `ledger-inline-closures-good.json`,
with the citation pointed at `receipt-md-block-good.md`, whose
`findings_addressed[].finding_id` covers the closed id `F-1`.

## Cost Ledger

| # | agent | model | tokens | outcome |
|---|-------|-------|--------|---------|
| 1 | organic-implementer | sonnet | 50000 | ok |
| 2 | organic-reviewer | opus | 30000 | review-clear |
| 3 | commit-step | sonnet | 5000 | ok |

## Close

```json
{
  "ledger": [
    { "n": 1, "agent": "organic-implementer", "model": "sonnet", "tokens": 50000, "tool_uses": 12, "duration_s": 300, "outcome": "ok" },
    { "n": 2, "agent": "organic-reviewer", "model": "opus", "tokens": 30000, "tool_uses": 8, "duration_s": 200, "outcome": "review-clear" },
    { "n": 3, "agent": "commit-step", "model": "sonnet", "tokens": 5000, "tool_uses": 3, "duration_s": 60, "outcome": "ok" }
  ],
  "close": {
    "delegations": 3,
    "subagent_tokens": 85000,
    "commits": ["a1b2c3d"],
    "re_briefs": 0,
    "inline_closures": [
      { "receipt": "scripts/tests/fixtures/receipt-md-block-good.md", "finding_ids": ["F-1"] }
    ]
  }
}
```
