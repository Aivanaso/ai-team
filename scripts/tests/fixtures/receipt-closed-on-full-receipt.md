# Review Report — fixture `receipt-closed-on-full-receipt`

A `closed` list on a receipt carrying no `verdict_history` (the shape a "full" receipt used to
be told apart by). `receipt.py` validates `closed`'s shape and containment only and has no
opinion on full vs delta -- the machine owns that discriminator at `settle` (attempt >= 2),
ticket-aware, not this standalone validator (open question resolved 2026-09-20T19:03:49Z).
This fixture is structurally valid and exits 0 here; `scripts/tests/test_machine.py` proves the
attempt-1 refusal at `settle`.

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
    { "id": "F-1", "file": "README.md", "line": 1 }
  ]
}
```
