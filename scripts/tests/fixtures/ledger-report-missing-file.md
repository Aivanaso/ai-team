# Brief File — fixture group `ledger-report`

Negative fixture for the `ledger[].report` containment probe, and the carrier
of the degenerate-root SHORT-CIRCUIT assertion for that probe:
`ledger[1].report` cites a guaranteed-absent `.md` path (ordinary citation
policy). Under a HEALTHY project_root the probe runs and the citation fails it
— one violation. Under the degenerate project_root `/` the probe never runs at
all, so the degenerate-root rule itself is the ONLY violation — still one, but
a different one. Pinning both counts is what distinguishes "short-circuited"
from "ran and happened to find nothing".

## Ledger

```json
{
  "ledger": [
    { "n": 1, "agent": "organic-implementer", "model": "sonnet", "tokens": 50000, "tool_uses": 12, "duration_s": 300, "outcome": "ok" },
    { "n": 2, "agent": "organic-reviewer", "model": "opus", "tokens": 30000, "tool_uses": 8, "duration_s": 200, "outcome": "review-clear", "report": "domain/skills/does-not-exist-anywhere-report.md" },
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
