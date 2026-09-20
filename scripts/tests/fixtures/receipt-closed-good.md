# Review Report — fixture `receipt-closed-good`

Inherited shape from `receipt-good.md`, extended with a validated `closed` entry and a
`verdict_history` chain: a delta-shaped receipt whose `closed` list cites a prior finding this
pass verified closed, and re-lists a different id under `findings`.

## Receipt

```json
{
  "tier": 1,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-clear",
  "lenses": {
    "correctness": {
      "status": "findings",
      "findings": [
        {
          "id": "F-2",
          "severity": "MINOR",
          "confidence": "medium",
          "evidence": "read",
          "file": "README.md",
          "line": 1,
          "claim": "README.md:1 documents the project name"
        }
      ]
    }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ],
  "closed": [
    { "id": "F-1", "file": "README.md", "line": 1 }
  ],
  "verdict_history": [
    { "pass": "full", "report": "prior.md", "verdict": "review-blocked", "note": "F-1 MAJOR" },
    { "pass": "delta", "report": "this.md", "verdict": "review-clear", "note": "F-1 closed at README.md:1" }
  ]
}
```
