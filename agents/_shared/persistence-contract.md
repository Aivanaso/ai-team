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
└── tasks.md             # Implementation plan
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
  verify:
    status: pending
  archive:
    status: pending

current_phase: design
blocked: false
blocked_reason: ""
```

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
| **Timestamps** | Use ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`) |
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
