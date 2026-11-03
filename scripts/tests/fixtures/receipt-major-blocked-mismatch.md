# Review Report — fixture `receipt-major-blocked-mismatch`

Prose is never parsed, only the single fenced json block below.

## Receipt

```json
{
  "tier": 1,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-blocked",
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
          "claim": "MAJOR finding without a CRITICAL but verdict wrongly says review-blocked"
        }
      ]
    }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ]
}
```
