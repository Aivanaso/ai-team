# Persistence Contract

> Filesystem-only persistence rules for all agents.

## Purpose

All state and artifacts live on the filesystem. No external services, no databases, no engram. This keeps everything human-readable, version-controllable, and debuggable.

## What's on disk

Delegated workers track no phase state and archive nothing — there is no state machine, no change directory, no per-worker phase tracking (see `orchestrator-protocol.md` → "Organic Delegation Route"). The orchestrator itself maintains one durable Brief File per task under `.ai-team/briefs/` — the audit trail, cost ledger, and pause/resume state for that task (schema: `orchestrator-protocol.md` → "Task Brief" → "Brief File (durable copy)"). What a project accumulates under `.ai-team/` is:

```
.ai-team/
├── config.yaml           # project conventions, declared commands (organic-scout bootstrap;
│                          # kept up to date by the orchestrator's Config Refresh Check)
├── skill-registry.md     # auto-generated index of stack skills — machine-local, gitignored
├── briefs/                # one durable Brief File per task (orchestrator-authored only) —
│                          # audit trail, cost ledger, phase checkboxes; see orchestrator-protocol.md
└── retros/                # per-task retrospectives — format and generation defined by a later change
```

Everything else a skill produces is either:

- an application source file, written by `organic-implementer`, bounded by the Task Brief's `allowed_edit_roots`; or
- a git commit, created by `work-unit-commits`, the exclusive owner of commit creation; or
- an optional review/discovery report, written by `organic-reviewer`, `organic-security`, or `organic-scout` (discover mode) at an orchestrator-injected `report_destination` — no fixed path, created only when that destination is injected. Absent an injection, the result envelope is the sole record.

## Rules

### Writing

| Rule | Description |
|------|-------------|
| **Atomic writes** | Write complete files, not partial updates |
| **Timestamps** | Sub-agents MUST use the `current_iso_utc` value injected by the orchestrator for all timestamp fields. Generating timestamps from the sub-agent's own sense of "now" produces drift (observed in me-profile retro 2026-05-09: `2026-05-09T23:25:00Z` written when real date was `2026-05-08`). Format is ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`). If the Injected Context block lacks `current_iso_utc`, surface as a `risk:` and use `date -u +%Y-%m-%dT%H:%M:%SZ` from Bash. |
| **UTF-8 only** | All files MUST be UTF-8 encoded |
| **Brief File ownership** | Brief Files under `.ai-team/briefs/` are orchestrator-authored only — no delegated skill reads or writes them; a worker's Task Brief still arrives inline in the delegation prompt (unchanged). |

### Reading

| Rule | Description |
|------|-------------|
| **Config first** | Read `.ai-team/config.yaml` (if present) before orienting on the target repo — project conventions and declared commands live there. |
| **No assumptions** | Never assume a declared file exists — verify. `organic-implementer` verifies via its own Decision Gates; `work-unit-commits` verifies via its `group_files` staging discovery (stage only what `git status --porcelain` confirms is actually dirty). |
