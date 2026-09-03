# Review Report — fixture group `md-container-malformed-block`

Negative fixture: exactly one fenced json block, correctly opened and closed,
whose content is not valid JSON syntax (a trailing comma after the last
member). The rule under test is that a malformed block is the same exit-1
VIOLATION class as a malformed legacy `.json` file — never exit 2, which stays
reserved for what prevented validation from running at all.

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
}
```
