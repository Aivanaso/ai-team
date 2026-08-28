# Review Report Format — organic-reviewer

> Load at Step 7, only when `report_destination` is injected. This is the on-disk report
> template; the envelope's Review Receipt (see `_shared/result-envelope.md`) is the record
> of authority — this file is a durable copy written into the target repo.

````markdown
# Review Report: {group_id}

**Date:** {current_iso_utc}
**Tier:** {tier} — {tier_reason}
**Verdict:** review-clear | review-blocked

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

| Command | Exit Code | Outcome | Gate |
|---------|-----------|---------|------|
| {verbatim command} | {int} | pass / fail | — |
| {verbatim command} | {int} | pass / fail | {gate name} |

(the Gate column is `—` for a plain `acceptance_checks`/build/lint command; it carries the
`review_gates` entry's `name` for a gate outcome row. unrunnable commands are omitted from this
table; the gap is noted in the envelope's `risks` instead — for an unrunnable gate, name it:
"review gate '{name}' could not be re-run in this environment")
````

## Per-Finding Structure

Expand each finding inside its lens section using this structure:

| Field | Description |
|-------|-------------|
| `id` | `F-1`, `F-2`, … (sequential, stable within the report) |
| `lens` | One of: business-logic \| state-transitions \| concurrency \| resource-lifecycle \| error-handling \| gate (a failing `review_gates` entry — objective, always `confidence: high`; not a sixth correctness lens, see SKILL.md Hard Rules) |
| `file_line` | `path/to/file:42` — mandatory (Evidence Protocol Rule 1); for a `gate` finding this is the gate's declaring entry in `.ai-team/config.yaml` |
| `severity` | CRITICAL \| MAJOR \| MINOR |
| `confidence` | high \| medium \| low — every finding is recorded regardless of confidence (coverage; see SKILL.md Hard Rules); for a `gate` finding this is always `high` (objective exit-code evidence) |
| `evidence` | `executed` \| `read` — `executed` = a command, mutation probe, scenario, or measurement against real data demonstrated the defect; `read` = the finding rests on code reading alone; for a `gate` finding this is always `executed` |
| `trigger` | One line naming the concrete input/command/state that reaches the cited line and produces the defect. Optional in general; REQUIRED when `severity` is MAJOR or CRITICAL and `evidence` is `read` — a `read` finding with no `trigger` is emitted at MINOR as maximum (see SKILL.md Hard Rules) |
| `description` | 1–3 sentences: the defect |
| `recommendation` | One paragraph or fix sketch — an unverified hypothesis: the lens verified the defect, not this fix; the orchestrator re-derives the edge case before acting on it (`orchestrator-protocol.md` → Recommendation ingestion) |
| `confidence_rationale` | One sentence: why this confidence level. For a `gate` finding: N/A — objective evidence (command + exit code), not a judgment call. |

All five lens sections are always present in the output report ("No findings" if clean for
that lens). A `gate`-lens finding is not one of the five sections — when a `review_gates`
outcome produces one, it is listed directly under the Correctness Findings heading, only when
one exists (no empty "Gate" section for projects with no `review_gates` declared). Finding IDs
are stable within the report so an override decision recorded in the receipt's `overrides`
field can cite `F-N` by reference.

## Delta Report Variant

Used only for a DELTA MODE pass (`prior_report` injected, Execution Step 2). Replaces the
full five-lens template above with a compact report chained to the prior pass — the delta pass
does not re-render the prior pass's clean lenses.

````markdown
# Delta Review Report: {group_id}

**Date:** {current_iso_utc}
**Tier:** {tier} — {tier_reason}
**Prior report:** {prior_report path}
**Verdict:** review-clear | review-blocked
**Chain:** {N} passes total (see `verdict_history` in the Review Receipt)

## Closures Verified

{for each named finding from the delta scope: "F-N — closed, {citation}" or "F-N — still open, {citation}"}

## New Inconsistency Check

{findings from the delta scope only, same per-finding structure as above, or "None found"}

## Gates Re-run

| Command | Exit Code | Outcome | Gate |
|---------|-----------|---------|------|
| {verbatim command} | {int} | pass / fail | {gate name or —} |

## Not Re-Verified

{mandatory — every lens/file the prior pass covered that this pass did not re-check, with the
reason: "already clean in the prior pass" | "outside the delta scope"}
````

A CRITICAL finding in a delta pass escalates to a full re-review — the delta report format is
never chained a third time for the same objective's finding set
(`references/edge-cases.md` → "Delta Pass Files a CRITICAL").
