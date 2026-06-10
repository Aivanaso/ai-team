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

### Step 2 — Load Referenced Artifacts

Read the artifact paths listed in `## Injected Context` (`proposal_path`, `design_path`, `spec_paths`, `tasks_path`, ...). Read each referenced artifact in full — these are your source of truth for the current task.

### Step 3 — Load Shared Protocols JIT

Read each `_shared/` protocol from the paths in your delegation prompt when the SKILL.md step that needs it begins (per your References section) — not all upfront. This keeps each protocol fresh in context at the step that uses it. If a protocol path does not exist: continue with loaded instructions, report `context_resolution: fallback`, and list the missing protocol in `risks`.

### Step 4 — Begin Work

Execute your Execution Steps. Report `context_resolution` honestly in the envelope: `self-loaded` (healthy disk-read), `fallback` (recovered missing inputs from disk — list them in `risks`), `none` (context-light phase).

## Rules

| Rule | Description |
|------|-------------|
| **Minimal context** | Read only the paths your delegation prompt and your SKILL.md References section declare. |
| **No exploration** | Skip `.ai-team/` content not referenced in the prompt (other changes, explorations, archives). |
| **No orchestrator state** | You have NO access to the orchestrator's conversation history. |
| **Own skill only** | Read the SKILL.md assigned in your prompt; do not hunt for or follow other skills. |
| **Fail fast** | If a referenced artifact doesn't exist, return `status: blocked` immediately. |
| **Honest canary** | If you recovered something the orchestrator should have injected, report `context_resolution: fallback` and list it in `risks` — silent fallback defeats the compaction canary. |

## Example: Full Startup

```
# 0. Primary instructions (path from delegation prompt)
Read ~/.claude/skills/sdd-spec/SKILL.md

# 1. Config
Read .ai-team/config.yaml
→ Stack: <frameworks> + <language(s)> + <test runner>, package manager <name>

# 2. Artifacts (paths from Injected Context)
Read .ai-team/changes/user-auth/proposal.md
Read .ai-team/specs/auth/spec.md

# 3. Protocols JIT (as each Execution Step needs them)
Read _shared/persistence-contract.md   # at the step that writes state.yaml

# 4. Work
→ Execute task per SKILL.md Execution Steps
```
