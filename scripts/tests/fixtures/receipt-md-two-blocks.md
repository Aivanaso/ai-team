# Review Report — fixture group `md-container-two-blocks`

Negative fixture: two fenced json blocks in one container. Both are valid full
receipts on their own, so the ONLY rule that can fail here is the uniqueness
rule (calibration isolation) — an ambiguous container is reported, never
resolved by position ("first wins" and "last wins" are both refused).

## Receipt (first pass)

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
          "claim": "README.md:1 documents the project name"
        }
      ]
    }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ]
}
```

## Receipt (second pass, left in by mistake)

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
  ]
}
```
