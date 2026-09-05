# Review Report — fixture `receipt-verdict-mismatch`

Inherited from check-receipt.py's calibration suite; the prose is never parsed, only the single fenced json block below.

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
          "severity": "CRITICAL",
          "confidence": "high",
          "evidence": "executed",
          "file": "README.md",
          "line": 1,
          "claim": "CRITICAL finding present but verdict wrongly says review-clear"
        }
      ]
    }
  },
  "verification": [
    {
      "command": "true",
      "exit_code": 0,
      "outcome": "pass"
    }
  ]
}
```
