# Review Report — fixture `receipt-tier-bool`

Inherited from check-receipt.py's calibration suite; the prose is never parsed, only the single fenced json block below.

## Receipt

```json
{
  "tier": true,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-clear",
  "lenses": {
    "correctness": {
      "status": "pass",
      "findings": []
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
