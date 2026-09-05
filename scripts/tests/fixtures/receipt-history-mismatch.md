# Review Report — fixture `receipt-history-mismatch`

Inherited from check-receipt.py's calibration suite; the prose is never parsed, only the single fenced json block below.

## Receipt

```json
{
  "tier": 1,
  "tier_reason": "tier 1: delta pass",
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
  ],
  "verdict_history": [
    {
      "pass": "full",
      "report": ".ai-team/reviews/example.md",
      "verdict": "review-blocked",
      "note": "initial full pass found a CRITICAL"
    },
    {
      "pass": "delta",
      "report": ".ai-team/reviews/example-delta.md",
      "verdict": "review-blocked",
      "note": "still blocked after remediation"
    }
  ]
}
```
