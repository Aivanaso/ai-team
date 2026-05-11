# Persistence Contract

> Filesystem-only persistence rules for all agents.

## Purpose

All state and artifacts live on the filesystem. No external services, no databases, no engram. This keeps everything human-readable, version-controllable, and debuggable.

## Directory Structure

All active work lives under `.ai-team/changes/{change-name}/`:

```
.ai-team/changes/{change-name}/
├── state.yaml           # Phase tracking (source of truth)
├── proposal.md          # What and why
├── specs/               # Delta specs
│   └── {domain}/spec.md
├── design.md            # Technical design
├── tasks.md             # Implementation plan
└── verification-report.md  # Verify phase output
```

## state.yaml Format

```yaml
change: user-authentication
created: 2026-03-11T10:00:00Z
updated: 2026-03-11T14:30:00Z

phases:
  propose:
    status: done          # pending | active | done | skipped
    completed: 2026-03-11T10:15:00Z
    agent: sdd-propose
  spec:
    status: done
    completed: 2026-03-11T11:00:00Z
    agent: sdd-spec
  design:
    status: active
    started: 2026-03-11T14:00:00Z
    agent: sdd-design
  tasks:
    status: pending
  apply:
    status: pending
    progress:
      "1.1": done           # task-keyed entries (existing)
      "G1": done            # NEW: group-keyed entries (REQ-WUC-007 cross-ref)
    commits:                # NEW: per-group commit SHAs (REQ-WUC-007)
      "G1": "abc1234ef9"    # auto mode
      "G2": "manual-pending"# manual mode
  verify:
    status: pending
  archive:
    status: pending

current_phase: design
blocked: false
blocked_reason: ""

decisions: []          # Mid-flight decision log (see below)
```

### `decisions:` — Mid-Flight Decision Log

When apply or verify discovers something that requires a deviation from the approved plan (a fix outside `tasks.md`, a pivot from `design.md`, a new dependency, a structural change), the agent MUST append an entry to `state.yaml.decisions:` BEFORE committing the change. This preserves the audit trail across phases — without it, sdd-verify cannot tell legitimate drift from scope creep, and archive ends with documentation that does not match what shipped.

**Schema** (each entry is a list item):

```yaml
decisions:
  - date: 2026-05-04T18:30:00Z       # ISO 8601, UTC preferred
    phase: apply                      # propose | spec | design | tasks | apply | verify
    task_ref: "T1.5"                  # task ID it affects, or "out-of-plan" for net-new
    decision: "Drop pull-first caching in cuideo-core CI"
    reason: "Single-stage base is commit-dependent; pull-first serves stale composer.lock"
    evidence: "PR 2 PRE deploy missing symfony/messenger from vendor/"
    commits: ["a489aa1"]              # SHAs (or empty list if not yet committed)
  - date: 2026-05-07T10:30:00Z
    phase: security-code-audit
    task_ref: "security-override"
    decision: "Accept CRITICAL finding F-3 (path traversal in upload handler)"
    reason: "Upload path is admin-only, behind authenticated middleware; risk acceptable"
    evidence: ".ai-team/changes/{name}/audit-report.md#finding-F-3"
    commits: []
```

**Field rules:**

| Field | Required | Notes |
|-------|----------|-------|
| `date` | Yes | ISO 8601 timestamp |
| `phase` | Yes | The phase the agent is currently in when it logs. Recognised values: `propose | spec | design | tasks | apply | verify | security-threat-model | security-code-audit` |
| `task_ref` | Yes | Use the task ID; or one of the recognised non-task identifiers: `"out-of-plan"` (no task ancestor), `"design-pivot"` (overrides a design.md decision), `"security-override"` (user accepted CRITICAL security finding), `"test-contract-correction"` (sdd-apply corrects a test-orphan per REQ-APPLY-023), `"post-apply-audit-gap"` (orchestrator re-engages after Post-Apply Audit discrepancy per REQ-ORCHESTRATOR-010) |
| `decision` | Yes | One sentence, what changed |
| `reason` | Yes | One sentence, why it had to change |
| `evidence` | Yes | A grep result, command output, file:line, or test failure that triggered the decision. Per Evidence Protocol Rule 1, a hand-wave like "it didn't work" is not evidence |
| `commits` | No | SHA list, populated after the fix lands. Empty list is fine when logging before commit |

**When to write a decision entry:**

- A `fix:` commit during apply that was not in `tasks.md`.
- A change to design assumptions discovered during apply (e.g., "compiler pass approach blocked by autowiring quirk, switching to manual array").
- A new dependency added during apply that the proposal did not list.
- A design-document deviation surfaced by verify (the report references the entry instead of generating one).

**When NOT to write a decision entry:**

- Trivial typo fixes inside the scope of an existing task.
- Test-only adjustments that don't change production behavior.
- Refactoring the agent does within a single task to keep code readable.

**Reading decisions:**

- `sdd-verify` reads `decisions:` during the Drift Summary step to distinguish approved drift from unaccounted scope creep.
- `sdd-archive` carries the full list into the archived `state.yaml`. Decisions are part of the audit trail.

### Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Not started, waiting for dependencies |
| `active` | Currently being worked on |
| `done` | Completed successfully |
| `skipped` | Intentionally skipped (e.g., trivial change needs no design) |

## Rules

### Writing

| Rule | Description |
|------|-------------|
| **Atomic writes** | Write complete files, not partial updates |
| **state.yaml is truth** | Always update `state.yaml` AFTER writing artifacts, not before |
| **Timestamps** | Use the `current_iso_utc` value injected by the orchestrator (Injected Context block) for all `completed:`, `started:`, `updated:` and `decisions[].date` fields. Format is ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`). Sub-agents MUST NOT generate timestamps from their own sense of "now" — that drifts (observed in me-profile retro 2026-05-09: `2026-05-09T23:25:00Z` written when real date was `2026-05-08`). If the Injected Context block lacks `current_iso_utc`, surface as a `risk:` and use `date -u +%Y-%m-%dT%H:%M:%SZ` from Bash; do NOT fabricate. |
| **No orphan artifacts** | Every artifact MUST be tracked in `state.yaml` |
| **UTF-8 only** | All files MUST be UTF-8 encoded |

### Reading

| Rule | Description |
|------|-------------|
| **state.yaml first** | Always read `state.yaml` to understand current phase before reading artifacts |
| **File existence check** | Use file existence as secondary validation (if `state.yaml` says `done` but artifact is missing → `blocked`) |
| **No assumptions** | Never assume an artifact exists — verify |

### Archiving

When a change completes all phases:

1. Copy the change directory to `.ai-team/changes/archive/YYYY-MM-DD-{change-name}/`
2. Merge delta specs into `.ai-team/specs/{domain}/spec.md`
3. Delete the active change directory
4. Archive is committed to git; active changes are gitignored

## Explorations

Standalone investigations (not part of SDD workflow) go to:

```
.ai-team/explorations/{topic}/
├── findings.md
└── state.yaml     # Minimal: just created/updated timestamps
```

These have no phase tracking — they're one-shot research artifacts.

### Backward compatibility (additive — sdd-redesign-v2)

The following fields were added in sdd-redesign-v2 without breaking older state.yaml files. Parsers MUST tolerate missing values:

- `phases.apply.progress[{group_id}]` — `done` when a group completed; absent for groups not yet completed or for runs that pre-date this SDD.
- `phases.apply.commits[{group_id}]` — commit SHA (auto mode) or the literal `"manual-pending"` (manual mode); absent if work-unit-commits has not yet run for this group.
- `decisions[].task_ref` values `"test-contract-correction"` (REQ-APPLY-023) and `"post-apply-audit-gap"` (REQ-ORCHESTRATOR-010 / Rule 6) are now recognised.

Old runs that wrote state.yaml without these fields continue to be readable by sdd-verify, sdd-archive, and the orchestrator. No migration is required.
