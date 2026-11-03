# Review Report — fixture `receipt-major-clear-mismatch`

Prose is never parsed, only the single fenced json block below.

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
          "id": "F-1",
          "severity": "MAJOR",
          "confidence": "high",
          "evidence": "executed",
          "file": "README.md",
          "line": 1,
          "claim": "MAJOR finding present but verdict wrongly says review-clear"
        }
      ]
    }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ]
}
```
