# Review Report — fixture `receipt-security-fragment-bad-verdict`

Inherited from check-receipt.py's calibration suite; the prose is never parsed, only the single fenced json block below.

## Receipt

```json
{
  "kind": "security-fragment",
  "tier": 2,
  "tier_reason": "tier 2: security lens fragment",
  "verdict": "review-clear",
  "lenses": {
    "security": {
      "status": "findings",
      "findings": [
        {
          "id": "F-1",
          "severity": "CRITICAL",
          "confidence": "high",
          "evidence": "executed",
          "trigger": "demonstrated directly against the shipped fragment",
          "file": "README.md",
          "line": 1,
          "claim": "CRITICAL security finding present but verdict wrongly says review-clear"
        }
      ]
    }
  }
}
```
