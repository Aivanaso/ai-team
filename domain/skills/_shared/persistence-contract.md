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

When the SDD pipeline records a deviation from the approved plan (a fix outside `tasks.md`, a design pivot, a new dependency, a structural change, a security override, or an approved drift surfaced by Post-Apply Audit), the **orchestrator** appends an entry to `state.yaml.decisions:`. Sub-agents that detect a deviation signal it via the result envelope (apply via `deviation_report`; verify via `failure_class` + Drift Summary); they signal deviations via the result envelope — the orchestrator exclusively authors `decisions[]` entries. The orchestrator is the exclusive sub-agent-side writer.

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
| `phase` | Yes | The phase the agent is currently in when it logs. Recognised values: `propose | spec | design | tasks | apply | verify | security-threat-model | security-code-audit | orchestrator`. Going forward, only the orchestrator authors entries; new SDDs use `phase: orchestrator` for orchestrator-authored entries. Legacy archived entries with `phase: apply` or `phase: spec` remain valid; readers (verify, archive) parse them without error. |
| `task_ref` | Yes | Use the task ID; or one of the recognised non-task identifiers: `"out-of-plan"` (no task ancestor), `"design-pivot"` (overrides a design.md decision), `"security-override"` (user accepted CRITICAL security finding), `"test-contract-correction"` (legacy-recognised, no new writes — new SDDs use `test-orphan-re-engage`), `"test-orphan-re-engage"` (orchestrator-authored when re-engaging sdd-tasks on apply's `deviation_report.kind: test-orphan`), `"post-apply-audit-gap"` (orchestrator re-engages after Post-Apply Audit discrepancy per REQ-ORCHESTRATOR-010) |
| `decision` | Yes | One sentence, what changed |
| `reason` | Yes | One sentence, why it had to change |
| `evidence` | Yes | A grep result, command output, file:line, or test failure that triggered the decision. Per Evidence Protocol Rule 1, a hand-wave like "it didn't work" is not evidence |
| `commits` | No | SHA list, populated after the fix lands. Empty list is fine when logging before commit |

### Writer Set (exclusive — sub-agent boundary)

`decisions[]` entries are authored by exactly two parties:

| Writer | Triggers | task_ref values used |
|--------|----------|----------------------|
| **Orchestrator** (in-session, per Post-Apply Audit and re-engage protocols) | (a) Post-Apply Audit Check 1/2/3/4 discrepancy (Rule 6); (b) apply returns blocked with `deviation_report.kind: out-of-plan` and orchestrator approves drift; (c) apply returns blocked with `deviation_report.kind: design-pivot` and orchestrator re-engages design; (d) apply returns blocked with `deviation_report.kind: test-orphan` and orchestrator re-engages tasks; (e) Post-Apply Audit Check 5 failure → re-engage apply | `post-apply-audit-gap`, `out-of-plan`, `design-pivot`, `test-orphan-re-engage` |
| **User** (via orchestrator at approval gates) | (a) Security gate "Accept and proceed" override on CRITICAL finding; (b) skip-spec confirmation logged in `phases.spec.skip_reason`, NOT decisions[]; (c) Drift acceptance during a verify warning | `security-override` |

**The orchestrator is the exclusive `decisions[]` writer.** Apply signals deviations via the envelope's `deviation_report` block (REQ-APPLY-023 reformulated). Verify signals drift via the Drift Summary table and via the envelope's `failure_class`. work-unit-commits backfills commit SHA into existing entries (REQ-WUC-003 step 5) without creating new entries.

**When to write a decision entry:**

- A deviation from `tasks.md` approved by the orchestrator (after reviewing apply's `deviation_report`).
- A design assumption override approved by the orchestrator (after reviewing apply's `deviation_report.kind: design-pivot`).
- A new dependency or infra change approved during re-engage.
- A design-document deviation surfaced by verify's Drift Summary and approved by the orchestrator.

**When NOT to write a decision entry:**

- Sub-agents (propose, spec, design, tasks, apply, verify, work-unit-commits, sdd-security executions) signal deviations via the result envelope; the orchestrator exclusively writes `decisions[]` entries. apply surfaces blocks via `deviation_report`; verify surfaces drift via the Drift Summary table; the orchestrator translates these into `decisions[]` entries.
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
| **Timestamps** | Sub-agents MUST use the `current_iso_utc` value injected by the orchestrator for all timestamp fields. Generating timestamps from the sub-agent's own sense of "now" produces drift (observed in me-profile retro 2026-05-09: `2026-05-09T23:25:00Z` written when real date was `2026-05-08`). Format is ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`). If the Injected Context block lacks `current_iso_utc`, surface as a `risk:` and use `date -u +%Y-%m-%dT%H:%M:%SZ` from Bash. |
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

As of sdd-redesign apply-junior, `decisions[].task_ref` value `"test-orphan-re-engage"` (orchestrator-authored per REQ-ORCHESTRATOR-008) is recognised. Legacy `phase: apply` entries (date < this SDD's `state.yaml.created`) are tolerated; new SDDs use only orchestrator-authored entries (sdd-verify Step 10 flags WARNING for apply-authored entries).
