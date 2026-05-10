# Threat Model Output Template

Use this template when writing `{change_dir}/threat-model.md` in Step 8.4.

## Template

```markdown
# Threat Model: {change-name}

**Date:** {ISO 8601}
**Mode:** threat-model
**Touchpoints triggered:** {comma-separated list, or "none"}

## Summary

{1-3 sentences overall assessment}

## Findings

### {touchpoint-slug}

#### F-{n}: {short title}

- **Severity:** CRITICAL | WARNING | SUGGESTION
- **File:line:** {path:line}
- **Description:** {1-3 sentences}
- **Exploit scenario:** {paragraph}
- **Recommendation:** {paragraph or snippet}
- **Confidence rationale:** {one sentence}

(repeat per finding; "No findings" if clean for this touchpoint)

## Temporal Invariant Sweep

(always present in threat-model; transversal sub-pass, runs even when no touchpoints triggered)

**Temporal fields detected:** {comma-separated list of `table.column` or proposal references, or "none"}

| Field | Read path | Rejection semantic | Enforcement | Result |
|-------|-----------|--------------------|-----------:|--------|
| {table.column} | {endpoint or method} | {`now > field` / `IS NOT NULL` / etc.} | {Yes — cite / No} | OK / WARNING / CRITICAL |

(one row per field × read path; if no temporal fields detected, write "No temporal fields detected — sweep complete." and omit the table)

#### Findings emitted by sweep

(use category `temporal-invariant-sweep` in each finding; full per-finding structure; "No findings — all temporal fields enforced." if clean)

## Security Requirements

{RFC 2119 requirements block — only present for threat-model; empty list if no findings}

```yaml
security_requirements:
  - req_text: "..."
    priority: MUST | SHOULD
    related_touchpoint: "{slug}"
```

## Suppression Tally

{N} findings suppressed (confidence < 80%). Reasons: {brief list, or "none"}
```

## Per-Finding Structure

Each finding MUST include all seven fields:

| Field | Description |
|-------|-------------|
| `id` | F-1, F-2, ... (sequential, stable within a single artifact) |
| `category` | One of the 9 touchpoints or `temporal-invariant-sweep` |
| `file_line` | `path/to/file.ts:42` — mandatory per Evidence Protocol Rule 1 |
| `severity` | CRITICAL \| WARNING \| SUGGESTION |
| `description` | 1-3 sentences: what the issue is |
| `exploit_scenario` | One paragraph: how an attacker would use this |
| `recommendation` | One paragraph or fix snippet |
| `confidence_rationale` | One sentence: why > 80% confidence |
