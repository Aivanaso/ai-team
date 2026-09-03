# Review Report — fixture group `md-container-prose-fence`

Positive fixture: the literal text ```json appears mid-sentence in the prose
below, and the file still validates, because an opening fence is a WHOLE LINE
of (at most three spaces, then) three backticks and the label — never a
substring inside a sentence. Only the real block at the end is the object.

## Convention

A writer opens the container's block with a ```json fence on a line of its own
and closes it with three backticks on a line of their own; a ```json mentioned
inside a paragraph, like this one, opens nothing at all.

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
  ]
}
```
