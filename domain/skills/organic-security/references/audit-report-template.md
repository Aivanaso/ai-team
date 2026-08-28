# Audit Report Output Template

Use this template when writing `audit-report.md` at the injected `report_destination`. In the
same step, write a `.json` sidecar next to it (`report_destination` with `.md` replaced by
`.json`) serializing `{ kind: "security-fragment", tier, tier_reason, lenses: { security: security_lens } }`
— the Review Receipt security-lens fragment this mode contributes; the top-level `kind` is
REQUIRED (it is the only discriminator the validator accepts — a fragment without it is
rejected as a truncated full receipt) (`_shared/result-envelope.md` → Review
Receipt). That sidecar, not this `.md` narrative, is what the orchestrator's Citation audit
validates (`_shared/scripts/check-receipt.py`). `threat-model` mode writes no sidecar (SKILL.md,
Execution Steps, threat-model Step 6).

## Template

```markdown
# Audit Report: {group_id}

**Date:** {ISO 8601}
**Mode:** code-audit

## Summary

{1-3 sentences overall assessment}

## Audit Scope

Files audited: {group_files}
1-hop callers read: {count} / 10 max

## Findings by Category

### 1. Input Validation
{findings or "No findings"}

### 2. Authentication & Authorization
{findings or "No findings"}

### 3. Cryptography & Secrets
{findings or "No findings"}

### 4. Injection & Code Execution
{findings or "No findings"}

### 5. Data Exposure
{findings or "No findings"}

### 6. Enforcement Wiring
{findings or "No findings" — every guard the candidate introduces has its executor (CI step, script entry, registration) in the same candidate}

## Dependency Auditor

{output of test_commands.security, or "Dependency auditor: not configured (skipped)"}

## Sidecar Self-Validation

| Command | Exit Code | Violations fixed before return |
|---------|-----------|--------------------------------|
| python3 skills/_shared/scripts/check-receipt.py receipt {sidecar path} . | {int} | none / {one line per VIOLATION fixed} |
```

## Per-Finding Structure

Each finding MUST include all twelve fields:

| Field | Description |
|-------|-------------|
| `id` | F-1, F-2, ... (sequential, stable within a single artifact) |
| `category` | One of the 5 vulnerability categories or `enforcement-wiring` |
| `file` | `path/to/file.ts` — repo-relative, mandatory per Evidence Protocol Rule 1; the `.md` may print it joined with `line` as `path:line` for humans, but the JSON sidecar carries `file` and `line` as two separate fields |
| `line` | `42` — integer ≥ 1, the line the finding cites |
| `severity` | CRITICAL \| MAJOR \| MINOR |
| `confidence` | high \| medium \| low — every finding is recorded regardless of confidence (coverage; see SKILL.md Hard Rules) |
| `evidence` | `executed` \| `read` — `executed` = a command, mutation probe, scenario, or measurement against real data demonstrated the defect; `read` = the finding rests on code reading alone |
| `trigger` | One line naming the concrete input/command/state that reaches the cited line and produces the defect. Optional in general; REQUIRED when `severity` is MAJOR or CRITICAL and `evidence` is `read` — a `read` finding with no `trigger` is emitted at MINOR as maximum (see SKILL.md Hard Rules) |
| `description` | 1-3 sentences: what the issue is |
| `exploit_scenario` | One paragraph: how an attacker would use this |
| `recommendation` | One paragraph or fix sketch — an unverified hypothesis: the lens verified the defect, not this fix; the orchestrator re-derives the edge case before acting on it (`orchestrator-protocol.md` → Recommendation ingestion) |
| `confidence_rationale` | One sentence: why this confidence level |

## Scope Semantics

`group_files` is resolved relative to the injected `project_root` — this route audits a
declared file set, never a branch diff. There is no `base_branch`/`change_branch` concept on
this route; scope is exactly the Task Brief's candidate files.
