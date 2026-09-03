# Review Report — fixture group `md-container-good`

Positive fixture for the Markdown container: one report file whose prose is
never parsed and whose single fenced `json` block carries a full, valid Review
Receipt (the shape of `receipt-good.json`, plus a `findings_addressed` entry so
`ledger-inline-closures-receipt-md-good.md` can cite this file and have its
closed id covered).

## Summary

Tier 1, correctness lens only. One MINOR finding, addressed inline.

## Findings

- **F-1 (MINOR, medium)** — `README.md:1` documents the project name.

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
          "claim": "README.md:1 documents the project name"
        }
      ]
    }
  },
  "verification": [
    { "command": "true", "exit_code": 0, "outcome": "pass" }
  ],
  "findings_addressed": [
    {
      "finding_id": "F-1",
      "files": ["README.md"],
      "fix_evidence": "README.md:1 confirms the wording fix",
      "gate_results": "pass: 1/1 checks"
    }
  ]
}
```
