# Review Report — fixture `receipt-minor-gated-mismatch`

Prose is never parsed, only the single fenced json block below.

## Receipt

```json
{
  "tier": 1,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-gated",
  "lenses": {
    "correctness": {
      "status": "findings",
      "findings": [
        {
          "id": "F-1",
          "severity": "MINOR",
          "confidence": "high",
          "evidence": "executed",
          "file": "README.md",
          "line": 1,
          "claim": "MINOR-only findings but verdict wrongly says review-gated"
        }
      ]
    }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ]
}
```
