# Review Report: {change-name} — Group {group_id}

**Date:** {current_iso_utc}
**Verdict:** review-clear | review-blocked
**Confidence threshold:** > 80%

## Diff Scope

Files reviewed: {group_files}   (1-hop callers read: {n}/10)

## Findings by Lens

### 1. Concurrency & Race Conditions

{findings or "No findings"}

### 2. Resource Lifecycle

{findings or "No findings"}

### 3. Error Handling & Propagation

{findings or "No findings"}

### 4. API-Contract Misuse

{findings or "No findings"}

## Suppression Tally

{N} findings suppressed (confidence ≤ 80%). {brief reasons, or "none"}

Per-finding structure (expand each finding inside the relevant lens section):

| Field | Description |
|-------|-------------|
| `id` | `RV-001`, `RV-002`, … (sequential, stable within the report so override decisions can cite by reference) |
| `lens` | One of: concurrency \| resource-lifecycle \| error-handling \| api-contract |
| `file_line` | `path/to/file:42` — mandatory (Evidence Protocol Rule 1) |
| `severity` | CRITICAL \| WARNING \| SUGGESTION |
| `description` | 1–3 sentences: the defect |
| `recommendation` | One paragraph or fix sketch |
| `confidence_rationale` | One sentence: why > 80% |

All four lens sections are always present in the output report ("No findings" if clean for that lens). Finding IDs are stable within the report so the override prompt and `decisions[].evidence` can cite `RV-NNN` by reference.
