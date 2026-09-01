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
├── tech-debt.md           # queued/deferred findings ledger (orchestrator-authored only) — format: orchestrator-protocol.md
└── retros/                # per-task retrospectives, written by organic-retro (mode: retro) at
                           # an orchestrator-injected report_destination; format:
                           # organic-retro/references/retro-format.md
```

Everything else a skill produces is either:

- an application source file, written by `organic-implementer`, bounded by the Task Brief's `allowed_edit_roots`; or
- a git commit, created by `work-unit-commits`, the exclusive owner of commit creation; or
- a review/discovery report, written by `organic-reviewer`, `organic-security`, or `organic-scout` (discover mode) at an orchestrator-injected `report_destination` — no fixed path. Optional from the skill's side (written only when the destination is injected) but mandatory from the orchestrator's side for every review-plane (`organic-reviewer`, `organic-security`) and scope-authority (`organic-scout` discover mode feeding a Task Brief) delegation (`orchestrator-protocol.md` → Critical Context Forwarding) — "optional" survives only for a genuinely context-light output, e.g. a plain `organic-scout` bootstrap pass that feeds no brief, where the result envelope remains the sole record; or
- a retro file, written by `organic-retro` (mode: `retro` only) at the orchestrator-injected `report_destination` (`.ai-team/retros/...`) — mandatory whenever the orchestrator's Retro trigger delegates it (`orchestrator-protocol.md` → "Retro trigger"); `organic-retro` in `conventions` mode writes nothing, returning `conventions_proposed` in the envelope only.

## Rules

### Writing

| Rule | Description |
|------|-------------|
| **Atomic writes** | Write complete files, not partial updates |
| **Timestamps** | Sub-agents MUST use the `current_iso_utc` value injected by the orchestrator for all timestamp fields. Generating timestamps from the sub-agent's own sense of "now" produces drift (observed in me-profile retro 2026-05-09: `2026-05-09T23:25:00Z` written when real date was `2026-05-08`). Format is ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`). If the Injected Context block lacks `current_iso_utc`, surface as a `risk:` and use `date -u +%Y-%m-%dT%H:%M:%SZ` from Bash. |
| **UTF-8 only** | All files MUST be UTF-8 encoded |
| **Brief File ownership** | Brief Files under `.ai-team/briefs/` are orchestrator-authored only — no delegated skill writes them. Named READ exception: `organic-retro` (mode: `retro`) reads the injected `brief_file` as its primary evidence source — the sole delegated skill authorized to read a Brief File — and never writes it. A worker's Task Brief still arrives inline in the delegation prompt (unchanged). Every other delegated skill neither reads nor writes a Brief File. |
| **tech-debt.md ownership** | `.ai-team/tech-debt.md` is orchestrator-authored only — no delegated skill reads or writes it. `organic-retro`'s Brief File READ exception above does NOT extend to it: `organic-retro` never reads `.ai-team/tech-debt.md`, in either mode. |

### Reading

| Rule | Description |
|------|-------------|
| **Config first** | Read `.ai-team/config.yaml` (if present) before orienting on the target repo — project conventions and declared commands live there. |
| **No assumptions** | Never assume a declared file exists — verify. `organic-implementer` verifies via its own Decision Gates; `work-unit-commits` verifies via its `group_files` staging discovery (stage only what `git status --porcelain` confirms is actually dirty). |
