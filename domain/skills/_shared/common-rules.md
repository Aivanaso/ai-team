# Common Rules

> Consolidated principles repeated across SDD SKILL.md files. Every SKILL.md MUST reference this file from its Hard Rules section instead of reproducing these principles.

## Why this exists

The redesign-v2 invariant grep (Evidence Protocol Rule 4) found these principles in 7/9 ("Read application code; never modify it"), 8/9 ("Result envelope always"), 7/9 ("Write only to .ai-team/") of the SDD SKILL.md files. Consolidation removes ~20+ duplicate Hard Rule lines across the framework.

## Reference line — required in every SKILL.md

Each SKILL.md Hard Rules section MUST contain exactly one reference line as the FIRST bullet:

    - Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.

Skill-specific rules follow this bullet. Verbatim reproduction of the three consolidated principles below is a REQ-CR-007 violation.

## Principle 1 — Read-only on application code (REQ-CR-002)

Read application code, never modify it. Source files are read only to verify design assumptions, gather evidence, or orient the current task. No skill phase writes to application source files. If a bug or improvement is found, surface it as a risk in the result envelope — never fix it in-place.

### Exception: sdd-apply

`sdd-apply` writes to application source files by design (per the Execution Steps in its SKILL.md, exactly the files declared in `tasks.md`). Apply's Hard Rules section MUST include the reference line AND a one-line exception note:

    - Writes application source files (exception to read-only principle — apply's primary responsibility).

## Principle 2 — Write-scope (REQ-CR-003)

Write only to `.ai-team/` (and declared application files for sdd-apply). No SDD skill writes to paths outside `.ai-team/` except sdd-apply (which writes to the paths declared in `tasks.md` for the current change). Shared protocols, SKILL.md files, project config files, and CI/CD pipelines are ALL read-only for SDD skills; they are modified only via the SDD pipeline itself running on the meta-project.

### Exception: work-unit-commits

`work-unit-commits` writes to the working tree via `git add` + `git commit` in auto mode (per REQ-WUC-003). This is a deliberate exception — work-unit-commits is the exclusive owner of commit creation. Apply uses only read-only git commands; `git commit` is exclusively owned by work-unit-commits (REQ-APPLY-021).

### Exception: orchestrator metric memory

The orchestrator writes to `~/.claude/projects/-home-ivan-Proyectos-ai-team/memory/project_post_apply_audit_hits.md` per REQ-ORCHESTRATOR-012.

## Principle 3 — Envelope-always (REQ-CR-004)

Every skill execution returns a result envelope. No skill exits silently. Even when blocked, the skill MUST return a `status: blocked` envelope with `executive_summary` explaining why. The envelope schema is defined in `_shared/result-envelope.md`. The `context_resolution` field MUST be populated on every execution: `injected` when all context arrived from the orchestrator, `fallback` when any field was recovered from disk, `none` when the phase is context-light.

## Principle 4 — Seniority Model (REQ-CR-008)

Each SDD pipeline role has a single authority and a single product. Each role operates within its single authority boundary — crossing authorities creates separation-of-duties failures (an executor cannot also be its own auditor; an auditor cannot also be its own decision-maker).

| Role | Authority | Product | Boundary |
|------|-----------|---------|----------|
| **Deciding skills** (`sdd-propose`, `sdd-spec`, `sdd-design`, `sdd-tasks`) | Decide their domain (scope, requirements, interfaces, task plan) | Domain artifacts (`proposal.md`, delta specs, `design.md`, `tasks.md`) | The orchestrator exclusively authors `decisions[]` entries (recorded against the approved plan these phases produce). |
| **Diagnosing skill** (`sdd-verify`) | Diagnose factual deviations from spec/design/tasks (run tests, build, lint; compute `failure_class`; emit Drift Summary) | `verification-report.md` + envelope `failure_class` | The orchestrator authors `decisions[]` entries. Verify reports drift via Drift Summary; orchestrator records it. |
| **Coordinating skill** (the orchestrator, in `_shared/sdd-orchestrator-protocol.md`) | Coordinate phase delegation, run Post-Apply Audit, write `decisions[]` for any approved drift surfaced by sub-agents | `decisions[]` entries in `state.yaml`; phase delegation prompts | Delegates all code execution, artifact writing, and test runs to skills. |
| **Implementing skill** (`sdd-apply`) | Implement `tasks.md` exactly; verify compilability; populate `execution_evidence`; OR return `status: blocked` with a structured `deviation_report` | Application source files; `state.yaml.phases.apply.*` (status, progress) | The orchestrator exclusively authors `decisions[]` entries; Reads SDD artifacts (`tasks.md`, `design.md`, specs, proposal) without modifying them; Uses only read-only git commands; state-changing commands (commit, add, push, stash, reset, rm) are exclusively owned by work-unit-commits. |
| **Mechanical skill** (`work-unit-commits`) | Stage declared files + create commit per group (auto/manual); backfill commit SHA into existing `decisions[]` entries | Commits in the working tree; `state.yaml.phases.apply.commits[group_id]`; commit SHA backfill into existing decisions[] entries | Updates the `commits[]` field of orchestrator-authored `decisions[]` entries (does not create new entries). |
| **Auditing skill** (`sdd-reviewer`) | Diagnose code-correctness defects in the group's changed files; emit a blocking verdict (`review-clear` / `review-blocked`) | `review-report.md` (per group); result envelope verdict | Read-only on application code; MUST NOT run state-changing git commands; MUST NOT write `decisions[]` entries (the orchestrator records review overrides exclusively) |

### Why this exists

The most common failure mode in apply phases is the executor laundering its own gaps through a
free-form audit field. The fix is structural: deny the executor the write surface. The audit
role moves to the orchestrator (which already coordinates and audits via Post-Apply Audit per
Rule 6 of evidence-protocol).

### Enforcement

- `sdd-apply` removes the `decisions[]` write path from Hard Rules, Decision Gates, Execution
  Steps, and references (REQ-APPLY-022 audit verifies this).
- `sdd-verify` Step 10 flags WARNING on any `decisions[]` entry with `phase: apply` AND
  `date >= state.yaml.created` (lifecycle-scoped check; legacy archives exempt).
- `persistence-contract.md` enumerates the Writer Set explicitly (orchestrator + user via
  orchestrator).
- The reference bullet in every affected SKILL.md's Hard Rules section names this principle
  by token ("seniority") so a downstream grep can verify propagation.

## Principle 5 — Startup sequence (REQ-CR-005)

Every skill begins by loading `_shared/context-protocol.md` (startup sequence) and `_shared/persistence-contract.md` (write rules, timestamp rules, decisions[] schema). These two protocols govern how the skill reads its context and how it writes state. They MUST be loaded before any application code is read or any artifact is written.

## Logical group — canonical definition (REQ-CR-006)

A **logical group** in `tasks.md` is a named set of one or more consecutive tasks that together produce a deployable or testable unit of the planned change. Groups are defined by the Execution Order table.

### Source of truth

`tasks.md` is the owning artifact. The canonical definition lives here in `common-rules.md`. The Execution Order table contains a `Group` column listing `G1`, `G2`, ..., with `## Group GN: {Name}` section headers below the table.

### Detecting the last task in a group (deterministic rule)

Task X is the last task in group G{N} if and only if the next row in the Execution Order table belongs to a different group (G{N+1}, G{N+2}, ...) OR task X is the last row in the table. This rule is referenced by:

- REQ-TASKS-021 (tasks.md structure)
- REQ-APPLY-007 (group boundary tests)
- REQ-APPLY-014 (group completion hand-off to orchestrator)
- REQ-VERIFY-006 (per-group Spec Compliance Matrix)
- REQ-ORCHESTRATOR-010 (work-unit-commits invocation per group)
- REQ-WUC-001 (work-unit-commits activation per group)

### Group numbering invariant

Groups MUST be numbered sequentially starting at G1 with no gaps (G1, G2, G3, ...). A gap (e.g., G1, G3) is a structural error caught by sdd-verify (REQ-VERIFY-004 Check 1).

### Task↔group mapping (D-4 resolution)

The canonical task→group mapping is the `Group` column of the `## Execution Order` table in tasks.md. Skills that need the mapping (work-unit-commits, verify, apply) MUST read the table column, not the section headers.
