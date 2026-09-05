# Review Report — fixture `receipt-fragment-with-omitted-reason`

Inherited from check-receipt.py's calibration suite; the prose is never parsed, only the single fenced json block below.

## Receipt

```json
{
  "kind": "security-fragment",
  "tier": 2,
  "tier_reason": "tier 2: security lens fragment",
  "lenses": {
    "security": {
      "status": "pass",
      "findings": []
    }
  },
  "verification_omitted_reason": "should be rejected on a fragment"
}
```
