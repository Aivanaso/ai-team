# Review Report — fixture `receipt-file-traversal`

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
          "severity": "MINOR",
          "confidence": "medium",
          "evidence": "read",
          "file": "../../../../../../etc/passwd",
          "line": 1,
          "claim": "finding cites a relative traversal escaping project_root"
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
