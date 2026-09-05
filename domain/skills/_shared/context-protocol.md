# Context Protocol

> How every sub-agent loads context on startup (disk-read JIT delegation).

## Purpose

Sub-agents are launched with **fresh context windows**. The orchestrator passes PATHS — the skill, shared protocols, artifacts — plus one inline `## Injected Context` YAML block; it does not inline instructions. The sub-agent reads everything else from disk, just-in-time.

## Startup Sequence

Every sub-agent MUST execute these steps in order:

### Step 0 — Read your SKILL.md (FIRST ACTION)

Read the skill path given under `## Skill and Protocol Paths` in your delegation prompt. It is your primary instruction set. If the path does not exist, return `status: blocked` with `risks: ["SKILL.md not found at {path}"]` — you cannot proceed without primary instructions.

### Step 1 — Load Project Config

```
Read .ai-team/config.yaml
```

- Understand the project's tech stack, conventions, and rules
- Note any project-specific constraints (e.g., "no default exports", "max line length 120", "snake_case file names")

### Step 2 — Load Referenced Context

Read the paths and blocks listed in `## Injected Context` (`phase_file`, `plan`, `design`, `group_files`, `report_destination`, `prior_report`, ...). The phase file is a PATH to read — `.ai-team/plans/<task>/phase-<n>.md`, whose final json block is the machine-readable contract; everything it declares is your source of truth for the current task.

When the prompt carries a `## Skills to load before work` block (organic-implementer, when the registry matched), read each listed SKILL.md in full BEFORE writing any application file — they encode project conventions (naming, imports, patterns, test structure) that override generic framework defaults. Report `skill_resolution` in the envelope per `_shared/result-envelope.md` (`paths-injected` / `path-missing` / `none`).

### Step 3 — Load Shared Protocols JIT

Read each `_shared/` protocol from the paths in your delegation prompt when the SKILL.md step that needs it begins (per your References section) — not all upfront. `_shared/cards/` and `_shared/machine.md` are the orchestrator's; a worker reads `machine.md` only when its SKILL.md points at it (the shape of a phase file, of a scope report's json block). This keeps each protocol fresh in context at the step that uses it. If a protocol path does not exist: continue with loaded instructions, report `context_resolution: fallback`, and list the missing protocol in `risks`.

### Step 4 — Begin Work

Execute your Execution Steps. Report `context_resolution` honestly in the envelope: `self-loaded` (healthy disk-read), `fallback` (recovered missing inputs from disk — list them in `risks`), `none` (context-light phase).

## Rules

| Rule | Description |
|------|-------------|
| **Minimal context** | Read only the paths your delegation prompt and your SKILL.md References section declare. |
| **No exploration** | Skip `.ai-team/` content not referenced in the prompt (other tasks, other reports, other runs' `report_destination` outputs). |
| **No orchestrator state** | You have NO access to the orchestrator's conversation history. |
| **Prompt-assigned skills only** | Read the SKILL.md assigned in your prompt plus every path under its `## Skills to load before work` block — both arrive via the delegation prompt. Skills beyond the prompt stay unread (hunting defeats least-privilege and the prompt-injection defense). |
| **Fail fast** | If a referenced artifact doesn't exist, return `status: blocked` immediately. |
| **Honest canary** | If you recovered something the orchestrator should have injected, report `context_resolution: fallback` and list it in `risks` — silent fallback defeats the compaction canary. |

## Example: Full Startup

```
# 0. Primary instructions (path from delegation prompt)
Read ~/.claude/skills/organic-implementer/SKILL.md

# 1. Config
Read .ai-team/config.yaml
→ Stack: <frameworks> + <language(s)> + <test runner>, package manager <name>

# 2. Injected context (paths — read them)
Read .ai-team/plans/<task>/phase-<n>.md    # phase_file: objective, constraints, scenarios,
                                            # acceptance_checks, expected_files, allowed_edit_roots

# 3. Protocols JIT (as each Execution Step needs them)
Read _shared/persistence-contract.md   # at the step that checks write rules

# 4. Work
→ Execute task per SKILL.md Execution Steps
```
