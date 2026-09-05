# Review Report — fixture `receipt-lens-status-incoherent`

Inherited from check-receipt.py's calibration suite; the prose is never parsed, only the single fenced json block below.

## Receipt

```json
{
  "tier": 1,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-clear",
  "lenses": {
    "correctness": {
      "status": "pass",
      "findings": [
        {
          "id": "F-1",
          "severity": "MINOR",
          "confidence": "medium",
          "evidence": "read",
          "file": "README.md",
          "line": 1,
          "claim": "status says pass but a finding is listed"
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
