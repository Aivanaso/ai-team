# Review Report Format — organic-reviewer

> Load at Step 7, only when `report_destination` is injected. This is the on-disk `.md` report
> template; the envelope's Review Receipt (see `_shared/result-envelope.md`) is the record
> of authority — this file is a durable, human-readable copy written into the target repo.
> ONE file per report: the report's last content is a `## Receipt` heading followed by a single
> fenced ```json block carrying that same Review Receipt object verbatim (same field names, no
> additions). That block — never the prose around it — is what the orchestrator's BLOCKING
> Citation audit validates (`_shared/scripts/check-receipt.py`, `orchestrator-protocol.md` →
> Evidence-Tier Review). No separate receipt file is written next to the report.
>
> **Exactly one ```json block per report.** A second one anywhere in the file — a JSON excerpt
> quoted inside a finding, a probe's captured output — makes the whole report a structural
> VIOLATION at exit 1. Fence every such excerpt as ```text or indent it; never as ```json.

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

## Receipt Self-Validation

| Command | Exit Code | Violations fixed before return |
|---------|-----------|--------------------------------|
| python3 skills/_shared/scripts/check-receipt.py receipt {report_destination} . | {int} | none / {one line per VIOLATION fixed} |

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
          "severity": "MAJOR",
          "confidence": "high",
          "evidence": "read",
          "trigger": "the concrete input/command/state that reaches the cited line",
          "file": "README.md",
          "line": 1,
          "claim": "README.md:1 — one line naming the defect"
        }
      ]
    }
  },
  "verification": [
    { "command": "{verbatim command}", "exit_code": 0, "outcome": "pass" },
    { "command": "{verbatim command}", "exit_code": 0, "outcome": "pass", "gate": "{gate name}" }
  ]
}
```
````

The receipt block above carries illustrative values; the lens serializes the exact Review Receipt
object it composed at Step 6, field for field. Every cited `file` must resolve on disk under
`project_root` (the validator checks containment plus existence), which is why the example cites
a file that really exists. The Receipt Self-Validation row records the validator run against this
same report file: the validator parses only the fenced block and never the prose, so filling the
row in after the run never invalidates what the run observed.

## Per-Finding Structure

Expand each finding inside its lens section using this structure. `file` and `line` are two
separate fields — the Review Receipt (`_shared/result-envelope.md` → Review Receipt) carries them
split, and `check-receipt.py` validates them split (a joined `path:line` string would not resolve
as either field). This `.md` narrative MAY still print them joined as `path:line` for a human
reader; that rendering choice never changes what the receipt block carries.

| Field | Description |
|-------|-------------|
| `id` | `F-1`, `F-2`, … (sequential, stable within the report) |
| `lens` | One of: business-logic \| state-transitions \| concurrency \| resource-lifecycle \| error-handling \| gate (a failing `review_gates` entry — objective, always `confidence: high`; not a sixth correctness lens, see SKILL.md Hard Rules) |
| `file` | `path/to/file` — mandatory (Evidence Protocol Rule 1); for a `gate` finding this is the gate's declaring entry in `.ai-team/config.yaml` |
| `line` | integer ≥ 1 — the line inside `file` the claim cites |
| `severity` | CRITICAL \| MAJOR \| MINOR |
| `confidence` | high \| medium \| low — every finding is recorded regardless of confidence (coverage; see SKILL.md Hard Rules); for a `gate` finding this is always `high` (objective exit-code evidence) |
| `evidence` | `executed` \| `read` — `executed` = a command, mutation probe, scenario, or measurement against real data demonstrated the defect; `read` = the finding rests on code reading alone; for a `gate` finding this is always `executed` |
| `trigger` | One line naming the concrete input/command/state that reaches the cited line and produces the defect. Optional in general; REQUIRED when `severity` is MAJOR or CRITICAL and `evidence` is `read` — a `read` finding with no `trigger` is emitted at MINOR as maximum (see SKILL.md Hard Rules) |
| `description` | 1–3 sentences: the defect. A code or data excerpt here is fenced as ```text or indented — never as ```json, which would add a second block and fail the report's own gate |
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
does not re-render the prior pass's clean lenses. The receipt-block rule above applies
identically here: `verdict_history` and `not_reverified` live inside this report's own
`## Receipt` block (the exact Review Receipt fields, `_shared/result-envelope.md` → Review
Receipt) — this `.md` narrative's "Chain" line and "Not Re-Verified" section are the
human-readable mirror, never the validated copy. `prior_report` names the prior pass's `.md`
report; that pass's own receipt block lives inside it.

````markdown
# Delta Review Report: {group_id}

**Date:** {current_iso_utc}
**Tier:** {tier} — {tier_reason}
**Prior report:** {prior_report path}
**Verdict:** review-clear | review-blocked
**Chain:** {N} passes total (see `verdict_history` in the Receipt block below)

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

## Receipt Self-Validation

| Command | Exit Code | Violations fixed before return |
|---------|-----------|--------------------------------|
| python3 skills/_shared/scripts/check-receipt.py receipt {report_destination} . | {int} | none / {one line per VIOLATION fixed} |

## Receipt

```json
{
  "tier": 1,
  "tier_reason": "tier 1: standard code change",
  "verdict": "review-clear",
  "lenses": {
    "correctness": { "status": "pass", "findings": [] }
  },
  "verification": [
    { "command": "{verbatim command}", "exit_code": 0, "outcome": "pass" }
  ],
  "verdict_history": [
    { "pass": "full", "report": "{prior report path}", "verdict": "review-blocked", "note": "F-1 CRITICAL: {one line}" },
    { "pass": "delta", "report": "{this report's path}", "verdict": "review-clear", "note": "F-1 closed at {path:line}" }
  ],
  "not_reverified": [
    "{lens/file not re-checked this pass} — already clean in the prior pass"
  ]
}
```
````

The chain injected as `delta_scope.prior_verdict_history` is appended to, never rebuilt: this
pass adds exactly one entry — its own — and the resulting array's last entry mirrors this
receipt's top-level `verdict`.

A CRITICAL finding in a delta pass escalates to a full re-review — the delta report format is
never chained a third time for the same objective's finding set
(`references/edge-cases.md` → "Delta Pass Files a CRITICAL").
