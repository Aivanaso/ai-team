# Review Report — fixture `receipt-security-fragment-major-clear`

Prose is never parsed, only the single fenced json block below.

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
          "severity": "MAJOR",
          "confidence": "high",
          "evidence": "executed",
          "file": "README.md",
          "line": 1,
          "claim": "MAJOR security finding present but verdict wrongly says review-clear"
        }
      ]
    }
  }
}
```
