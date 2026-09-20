# Review Report — fixture `receipt-closed-and-findings-same-id`

`F-1` appears under `lenses.correctness.findings` and under `closed` at the same time -- an id
is never both open and closed.

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
          "file": "README.md",
          "line": 1,
          "claim": "still open under findings"
        }
      ]
    }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ],
  "closed": [
    { "id": "F-1", "file": "README.md", "line": 2 }
  ]
}
```
