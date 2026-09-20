# Review Report — fixture `receipt-closed-file-traversal`

A `closed` entry whose `file` escapes `project_root` -- the same containment check a finding's
own `file` goes through.

## Receipt

```json
{
  "tier": 1,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-clear",
  "lenses": {
    "correctness": {
      "status": "pass",
      "findings": []
    }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ],
  "closed": [
    { "id": "F-1", "file": "../../../../../../etc/passwd", "line": 1 }
  ]
}
```
