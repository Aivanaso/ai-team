# Threat Model Output Template

Use this template to write the report at the injected `report_destination` — a FILE path
ending in `.md` (e.g. `.ai-team/reviews/YYYY-MM-DD-<slug>-threat-model.md`), never a directory
to write a fixed filename into. This mode writes no `.json` sidecar: `threat-model` findings
carry no `verdict`/`lenses.correctness` object and never feed the Review Receipt or the commit
gate (SKILL.md, Hard Rules + Execution Steps, threat-model Step 6) — the report includes a
one-line "no receipt sidecar in this mode" note instead.

## Template

```markdown
# Threat Model: {scope}

**Date:** {ISO 8601}
**Mode:** threat-model
**Touchpoints triggered:** {comma-separated list, or "none"}
**Receipt sidecar:** none — no receipt sidecar in this mode (threat-model findings never feed the Review Receipt)

## Summary

{1-3 sentences overall assessment}

## Findings

### {touchpoint-slug}

#### F-{n}: {short title}

- **Severity:** CRITICAL | MAJOR | MINOR
- **Confidence:** high | medium | low
- **File:line:** {path:line}
- **Description:** {1-3 sentences}
- **Exploit scenario:** {paragraph}
- **Recommendation:** {paragraph or snippet}
- **Confidence rationale:** {one sentence — why this confidence level}

(repeat per finding; "No findings" if clean for this touchpoint)

## Temporal Invariant Sweep

(always present; transversal sub-pass, runs even when no touchpoints triggered)

**Temporal fields detected:** {comma-separated list of `table.column` or scope references, or "none"}

| Field | Read path | Rejection semantic | Enforcement | Result |
|-------|-----------|--------------------|-----------:|--------|
| {table.column} | {endpoint or method} | {`now > field` / `IS NOT NULL` / etc.} | {Yes — cite / No} | OK / MINOR / CRITICAL |

(one row per field × read path; if no temporal fields detected, write "No temporal fields detected — sweep complete." and omit the table)

#### Findings emitted by sweep

(use category `temporal-invariant-sweep` in each finding; full per-finding structure; "No findings — all temporal fields enforced." if clean)

## Seam & Failure Sweep

(always present; transversal sub-pass, runs even when no touchpoints triggered)

| Seam / Mutation | Sub-sweep | Handler / Writers / Stores | Result |
|-----------------|-----------|----------------------------|--------|
| {new call-site, bulk mutation, or multi-store write sequence} | failure-mode / interleaving / crash-window | {catch `file:line` + blast radius / writer-reader list / store list + recovery story} | OK / MINOR / CRITICAL |

(one row per seam × sub-sweep; if the change introduces no new seams, write "No new seams introduced — sweep complete." and omit the table)

#### Findings emitted by sweep

(use category `failure-mode-sweep` / `interleaving-sweep` / `crash-window-sweep`; "No findings — all seams accounted for." if clean)

## Security Requirements

{RFC 2119 requirements block — only present for threat-model; empty list if no findings}

```yaml
security_requirements:
  - req_text: "..."
    priority: MUST | SHOULD
    related_touchpoint: "{slug}"
```
```

## Per-Finding Structure

`evidence`/`trigger` are N/A in threat-model mode — these findings route through
`security_requirements`, never into the Review Receipt or the commit gate.

Each finding MUST include all nine fields:

| Field | Description |
|-------|-------------|
| `id` | F-1, F-2, ... (sequential, stable within a single artifact) |
| `category` | One of the 9 touchpoints or a sweep category (`temporal-invariant-sweep`, `failure-mode-sweep`, `interleaving-sweep`, `crash-window-sweep`) |
| `file_line` | `path/to/file.ts:42` — mandatory per Evidence Protocol Rule 1 |
| `severity` | CRITICAL \| MAJOR \| MINOR |
| `confidence` | high \| medium \| low — every finding is recorded regardless of confidence (coverage; see SKILL.md Hard Rules) |
| `description` | 1-3 sentences: what the issue is |
| `exploit_scenario` | One paragraph: how an attacker would use this |
| `recommendation` | One paragraph or fix snippet |
| `confidence_rationale` | One sentence: why this confidence level |
