# Review Report — fixture group `md-container-wrong-fence-label`

Negative fixture: the file carries two fenced blocks whose bodies are valid
receipts, but neither fence label is the exact, lower-case `json` — one is
`JSON`, the other `jsonc`. The rule under test is label exactness (and its
case sensitivity): neither opens a block, so the container has zero blocks and
fails the same way `receipt-md-no-block.md` does.

## Receipt (upper-case label)

```JSON
{
  "tier": 1,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-clear",
  "lenses": {
    "correctness": { "status": "pass", "findings": [] }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ]
}
```

## Receipt (jsonc label)

```jsonc
{
  "tier": 1,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-clear",
  "lenses": {
    "correctness": { "status": "pass", "findings": [] }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ]
}
```
