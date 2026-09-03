# Review Report — fixture group `md-container-no-block`

Negative fixture: a report file that carries no fenced block at all — not of
any label. The rule under test is "a Markdown container must carry exactly one
fenced json block"; the zero-block arm.

## Summary

Tier 1, correctness lens only. Prose only, deliberately: the writer forgot the
machine-readable object, and the validator must say so rather than read the
prose.

## Findings

- **F-1 (MINOR, medium)** — `README.md:1` documents the project name.

## Receipt

The object belongs here. It is absent.
