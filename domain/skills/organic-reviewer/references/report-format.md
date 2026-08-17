# Review Report Format — organic-reviewer

> Load at Step 6, only when `report_destination` is injected. This is the on-disk report
> template; the envelope's Review Receipt (see `_shared/result-envelope.md`) is the record
> of authority — this file is a durable copy written into the target repo.

````markdown
# Review Report: {group_id}

**Date:** {current_iso_utc}
**Tier:** {tier} — {tier_reason}
**Verdict:** review-clear | review-blocked
**Confidence threshold:** > 80%

## Scope

Files reviewed: {group_files}   (1-hop callers read: {n}/10)

## Correctness Findings

### Business Logic

{findings or "No findings"}

### State Transitions

{findings or "No findings"}

### Concurrency

{findings or "No findings"}

### Resource Lifecycle

{findings or "No findings"}

### Error Handling

{findings or "No findings"}

## Verification

| Command | Exit Code | Outcome |
|---------|-----------|---------|
| {verbatim command} | {int} | pass / fail |

(unrunnable commands are omitted from this table and listed instead under Suppression Tally
with reason "unrunnable in this environment")

## Suppression Tally

{N} findings suppressed (confidence ≤ 80%). {brief reasons, or "none"}
````

## Per-Finding Structure

Expand each finding inside its lens section using this structure:

| Field | Description |
|-------|-------------|
| `id` | `F-1`, `F-2`, … (sequential, stable within the report) |
| `lens` | One of: business-logic \| state-transitions \| concurrency \| resource-lifecycle \| error-handling |
| `file_line` | `path/to/file:42` — mandatory (Evidence Protocol Rule 1) |
| `severity` | CRITICAL \| MAJOR \| MINOR |
| `description` | 1–3 sentences: the defect |
| `recommendation` | One paragraph or fix sketch |
| `confidence_rationale` | One sentence: why > 80% |

All five lens sections are always present in the output report ("No findings" if clean for
that lens). Finding IDs are stable within the report so an override decision recorded in the
receipt's `overrides` field can cite `F-N` by reference.
