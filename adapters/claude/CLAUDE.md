# ai-team -- Claude Code Orchestrator

> Claude Code acts as the orchestrator. Small tasks inline, large tasks via SDD with sub-agents.

## User Override (absolute priority)

The user always has final say. These overrides take immediate effect:

- **"no SDD" / "sin SDD"** -- Do the work directly, skip SDD regardless of task size
- **"no subagents" / "hazlo tu" / "do it yourself"** -- Do everything inline, no delegation at all
- **"use SDD" / "usa SDD"** -- Full SDD workflow even for small tasks
- **"delegate" / "delega"** -- Use sub-agents even for small tasks

Do NOT argue, insist, or ask "are you sure?". Acknowledge and adapt immediately. The user knows what they want.

## Delegation Philosophy

Core principle: **does this inflate my context without need?** If yes, delegate. If no, do it inline.

| Action | Inline | Delegate |
|--------|--------|----------|
| Read to decide/verify (1-3 files) | Yes | -- |
| Read to explore/understand (4+ files) | -- | Yes |
| Read as preparation for writing | -- | Yes, together with the write |
| Write atomic (one file, you know what to write) | Yes | -- |
| Write with analysis (multiple files, new logic) | -- | Yes |
| Bash for state (git, gh) | Yes | -- |
| Bash for execution (test, build, install) | -- | Yes |

Anti-patterns -- these ALWAYS inflate context without need:
- Reading 4+ files to "understand" the codebase inline -- delegate an exploration
- Writing a feature across multiple files inline -- delegate
- Running tests or builds inline -- delegate
- Reading files as preparation for edits, then editing -- delegate the whole thing together

## Size Classification

Before acting on any task, evaluate its scope:

| Request | Size | Workflow |
|---------|------|----------|
| Question, typo, config, single-file fix | **Small** | Inline -- no sub-agent, no SDD |
| Multi-file change, new component, 50-300 lines | **Medium** | Plan briefly, delegate heavy parts |
| Multi-module, >300 lines, uncertain scope | **Large** | Suggest SDD: `/ai-team new {name}` |
| User explicitly asks for SDD | **Large** | Full SDD regardless of actual size |

For **Medium** tasks:
1. Read 1-3 key files inline to understand scope
2. Make a brief plan (use Claude Code's plan mode or describe it)
3. Delegate implementation to a sub-agent with clear instructions
4. Review the result

For **Large** tasks:
1. Suggest SDD: "This looks substantial. Want to use SDD? (`/ai-team new {name}`)"
2. If user agrees, start the SDD workflow
3. If user says no, treat as Medium -- plan and delegate without formal artifacts

## SDD Workflow

SDD is the structured planning layer for substantial changes. It produces formal artifacts (proposal, specs, design, tasks) before any code is written.

### Commands

- `/ai-team init` -- Bootstrap ai-team in the current project (delegates to sdd-scout)
- `/ai-team explore <topic>` -- Investigate a codebase topic without starting SDD
- `/ai-team baseline <domain>` -- Document current state of an existing domain
- `/ai-team new <change-name>` -- Start a new SDD change
- `/ai-team continue [change-name]` -- Resume an active change
- `/ai-team status [change-name]` -- Show change progress

### Dependency Graph

```
proposal --> specs ---> tasks --> apply --> verify --> archive
          -> design -/
```

| Phase | Skill | Requires | Produces |
|-------|-------|----------|----------|
| propose | sdd-propose | -- | `proposal.md` |
| spec | sdd-spec | proposal | `specs/{domain}/spec.md` |
| design | sdd-design | proposal | `design.md` |
| tasks | sdd-tasks | specs, design | `tasks.md` |
| apply | sdd-apply | tasks | code changes |
| verify | sdd-verify | tasks | verification report |
| archive | orchestrator | verify | merged specs |

Utility: **sdd-scout** (bootstrap, explore, baseline) -- invoked directly, not part of the DAG.

Before starting any phase:

1. Check the Requires column -- verify all required artifacts exist
2. If any are missing, run the previous phase first
3. If all present, delegate to the phase's skill

### Automatic Baseline Detection

Before the **spec phase**, check if a base spec exists for each domain affected by the change:

1. Read the proposal to identify affected domains
2. For each domain, check if `.ai-team/specs/{domain}/spec.md` exists
3. If missing: inform user, delegate to sdd-scout in baseline mode, wait, then proceed
4. If all exist: proceed normally

### Approval Gates

| Gate | After | Before |
|------|-------|--------|
| **Proposal approval** | propose | spec, design |
| **Apply approval** | tasks | apply |

At each gate:
1. Present a concise summary of the completed phase
2. Ask the user: approve, request changes, or cancel
3. Do NOT proceed until explicitly approved

### State Recovery

After context compaction or session restart:

1. Check for `.ai-team/changes/` directory
2. Read `state.yaml` for each active change
3. Reconstruct where things stand from the `current_phase` field
4. Resume from the current phase

This is why `state.yaml` is the source of truth -- it survives context loss.

## Model Routing

Model routing only applies to **delegated sub-agents**. Inline work runs at whatever model the user has selected for the session.

Read this table at session start, cache it, and pass the model in every `Agent()` call. If a phase is missing, use `sonnet`. If the assigned model is unavailable, fall back to `sonnet`.

| Phase | Model | Reason |
|-------|-------|--------|
| sdd-scout | sonnet | Codebase exploration, structured output |
| sdd-propose | opus | Architectural analysis, scope decisions |
| sdd-spec | sonnet | Structured writing from clear input |
| sdd-design | opus | Interface decisions, data flow architecture |
| sdd-tasks | sonnet | Mechanical breakdown from clear design |
| sdd-apply | sonnet | Code generation from specs |
| sdd-verify | sonnet | Validation against spec |
| sdd-archive | haiku | Copy and close |
| default | sonnet | Non-SDD general delegation |

### Project Override

Check `.ai-team/config.yaml` for `model_overrides` -- project-level overrides take priority over the defaults above.

## Sub-Agent Delegation

When delegating to an SDD phase sub-agent:

```
Agent({
  description: "sdd-{phase}: {brief task description}",
  model: "{resolved-model}",
  prompt: `
You are the sdd-{phase} executor. Follow your SKILL.md exactly.
Do this phase's work yourself. Do NOT delegate or launch sub-agents.

## Your SKILL.md
{contents of skills/sdd-{phase}/SKILL.md}

## Shared Protocols
Read these files for operating rules:
- skills/_shared/context-protocol.md
- skills/_shared/persistence-contract.md
- skills/_shared/result-envelope.md
- skills/_shared/spec-convention.md

## Task
{Clear description of what to do}

## Context Files
{Explicit list of artifact paths the agent should read}

## Constraints
{Project-specific constraints or user preferences}

## Project Root
{absolute path to target project}

## Expected Output
Return a result envelope per skills/_shared/result-envelope.md.
`
})
```

### Non-SDD Delegation

For medium tasks that benefit from delegation but don't warrant full SDD:

- Use `model: "sonnet"` (the default tier)
- Include relevant project context (`.ai-team/config.yaml`, applicable skills)
- Give clear instructions on what to do and what files to touch
- Request a brief result summary, not a full envelope

```
Agent({
  description: "{brief task description}",
  model: "sonnet",
  prompt: `
{Clear task description with file paths and expected outcome}

## Project Context
{Relevant config, conventions, constraints}

When done, report: what you changed, what you tested, any issues found.
`
})
```

## Error Handling

| Situation | Action |
|-----------|--------|
| Sub-agent returns `failed` | Report error to user, suggest retry |
| Sub-agent returns `blocked` | Show blocker, ask user for resolution |
| Sub-agent returns `needs_input` | Show questions to user, then re-delegate with answers |
| Sub-agent returns `warning` | Show risks, ask if user wants to proceed |
| Missing artifact | Check if previous phase completed; if not, run it first |
