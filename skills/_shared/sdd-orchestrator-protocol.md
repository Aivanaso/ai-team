# SDD Orchestrator Protocol

> Loaded on demand by the orchestrator when SDD is triggered.
> Decision criteria (size classification, delegation, user overrides) live in the adapter's CLAUDE.md.

## Commands

- `/ai-team new <change-name>` -- Start a new SDD change
- `/ai-team continue [change-name]` -- Resume an active change
- `/ai-team status [change-name]` -- Show change progress
- `/ai-team explore <topic>` -- Investigate a codebase topic without starting SDD
- `/ai-team baseline <domain>` -- Document current state of an existing domain

## Auto-Init (before any SDD phase)

Before executing any SDD command (`/ai-team new`, `/ai-team continue`, `/ai-team explore`, `/ai-team baseline`):

1. Check if `.ai-team/config.yaml` exists in the project root
2. If it exists: proceed normally
3. If missing:
   a. Create `.ai-team/` directory structure inline (dirs + .gitignore)
   b. Delegate to sdd-scout in bootstrap mode to detect the stack
   c. Wait for the scout to finish and verify `config.yaml` was created
   d. Then proceed with the originally requested command

Do NOT ask the user to run init — handle it transparently.

### Directory structure (create inline)

```
.ai-team/
  specs/
  changes/archive/
  explorations/
  .gitignore
```

The `.gitignore` should ignore active changes and explorations but keep specs and archive:

```
/changes/*
!/changes/archive/
/explorations/
```

## Dependency Graph

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

Utility: **sdd-scout** (bootstrap, explore, baseline) -- invoked by the orchestrator, not part of the DAG.

Before starting any phase:

1. Check the Requires column -- verify all required artifacts exist
2. If any are missing, run the previous phase first
3. If all present, delegate to the phase's skill

## Automatic Baseline Detection

Before the **spec phase**, check if a base spec exists for each domain affected by the change:

1. Read the proposal to identify affected domains
2. For each domain, check if `.ai-team/specs/{domain}/spec.md` exists
3. If missing: inform user, delegate to sdd-scout in baseline mode, wait, then proceed
4. If all exist: proceed normally

## Approval Gates

| Gate | After | Before |
|------|-------|--------|
| **Proposal approval** | propose | spec, design |
| **Apply approval** | tasks | apply |

At each gate:
1. Present a concise summary of the completed phase
2. Ask the user: approve, request changes, or cancel
3. Do NOT proceed until explicitly approved

## Plan Mode (safety guardrail)

Use Claude Code's plan mode to prevent accidental file edits during SDD planning phases.

### On `/ai-team new` or `/ai-team continue` (resuming a planning phase):

1. Run auto-init if needed (creates `.ai-team/` dirs -- this happens BEFORE plan mode)
2. **Enter plan mode** (`EnterPlanMode`)
3. Run planning phases via sub-agents: propose → spec → design → tasks
4. Approval gates happen inside plan mode (ask the user normally)
5. When tasks phase completes and the user approves apply: **exit plan mode** (`ExitPlanMode`)
6. Delegate apply phase (now outside plan mode -- code can be written)

### What this protects against:

- Orchestrator accidentally editing application code during planning
- Sub-agents are NOT affected (they have their own context)
- `.ai-team/` artifact writing by sub-agents works normally

### When NOT to enter plan mode:

- `/ai-team explore` -- read-only investigation, no risk
- `/ai-team baseline` -- writes only to `.ai-team/`, delegated to sub-agent
- `/ai-team status` -- read-only
- Resuming at apply/verify/archive phase -- planning is already done

## State Recovery

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

IMPORTANT: Always use `subagent_type: "general-purpose"`. Do NOT invent custom subagent types like "sdd-propose" — they don't exist and will error.

When delegating to an SDD phase sub-agent:

1. Read `skills/sdd-{phase}/SKILL.md` yourself
2. Read the shared protocols yourself
3. Inject both as text into the prompt — sub-agents receive instructions inline, they do NOT read skill files

```
Agent({
  description: "sdd-{phase}: {brief task description}",
  subagent_type: "general-purpose",
  model: "{resolved-model}",
  prompt: `
You are the sdd-{phase} executor.
Do this phase's work yourself. Do NOT delegate or launch sub-agents.
Do NOT search for SKILL.md files or skill registries — your instructions are below.

## Instructions
{paste contents of skills/sdd-{phase}/SKILL.md here}

## Shared Protocols
{paste contents of skills/_shared/context-protocol.md}
{paste contents of skills/_shared/persistence-contract.md}
{paste contents of skills/_shared/result-envelope.md}
{paste contents of skills/_shared/spec-convention.md}

## Task
{Clear description of what to do}

## Context Files
{Explicit list of artifact paths the agent should read}

## Constraints
{Project-specific constraints or user preferences}

## Project Root
{absolute path to target project}

## Expected Output
Return a result envelope per the Result Envelope protocol above.
Include model_used: "{resolved-model}" in the envelope metadata.
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
  subagent_type: "general-purpose",
  model: "sonnet",
  prompt: `
{Clear task description with file paths and expected outcome}

## Project Context
{Relevant config, conventions, constraints}

When done, report: what you changed, what you tested, any issues found.
Include model_used in your response.
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
