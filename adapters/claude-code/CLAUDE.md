# ai-team — Claude Code Adapter

> Orchestrator overlay for Claude Code. Add this to your project's CLAUDE.md.

## Setup

Add the following to your project's `.claude/CLAUDE.md` (or append to existing):

```markdown
## ai-team Integration

This project uses ai-team for spec-driven development.

### Agent System

The orchestrator agent is defined at: {path-to-ai-team}/agents/orchestrator/AGENT.md

When the user invokes any `/ai-team` command:
1. Read the orchestrator's AGENT.md
2. Follow its instructions exactly
3. Use the Agent tool to delegate to sub-agents with fresh context

### Commands

- `/ai-team init` — Bootstrap ai-team in this project
- `/ai-team explore <topic>` — Investigate a codebase topic
- `/ai-team new <name>` — Start a new SDD change
- `/ai-team continue [name]` — Resume an active change
- `/ai-team status [name]` — Show change progress
```

## Model Routing

The orchestrator specifies a model **tier** per phase. The adapter resolves tiers to Claude models:

| Tier | Claude Model | Agent Tool `model` |
|------|-------------|--------------------|
| `reasoning` | Opus | `"opus"` |
| `balanced` | Sonnet | `"sonnet"` |
| `fast` | Haiku | `"haiku"` |

Always include the `model` parameter when calling the Agent tool. The orchestrator resolves the tier (checking project overrides first, then schema.yaml defaults) and the adapter maps it here.

## Delegation via Agent Tool

The orchestrator delegates to sub-agents using Claude Code's **Agent tool**. Each delegation:

1. Resolves the model tier for the phase (see Model Routing above)
2. Launches a new agent with `subagent_type: "general-purpose"` and the resolved `model`
3. Passes the sub-agent's `AGENT.md` content as part of the prompt
4. Includes explicit file paths for context (per context-protocol.md)
5. Receives a result envelope back

### Example Delegation Prompt

```
Agent({
  description: "sdd-scout: bootstrap project",
  model: "sonnet",  // tier "balanced" → sonnet
  prompt: `
You are the sdd-scout agent. Follow the instructions in your AGENT.md exactly.

## Your AGENT.md
{contents of agents/sdd-scout/AGENT.md}

## Shared Protocols
Read these files for operating rules:
- agents/_shared/context-protocol.md
- agents/_shared/persistence-contract.md
- agents/_shared/result-envelope.md

## Task
Bootstrap mode: detect the project stack and generate .ai-team/config.yaml and .ai-team/skill-registry.md.

## Project Root
/path/to/target/project

## Expected Output
Return a result envelope as defined in agents/_shared/result-envelope.md.
`
})
```

### Model Examples by Phase

```
// propose — architectural analysis
Agent({ model: "opus", description: "sdd-propose: analyze PRD", prompt: "..." })

// spec — structured writing from clear input
Agent({ model: "sonnet", description: "sdd-spec: generate delta specs", prompt: "..." })

// design — interface decisions, data flow
Agent({ model: "opus", description: "sdd-design: technical design", prompt: "..." })

// tasks — breaking down from clear design
Agent({ model: "sonnet", description: "sdd-tasks: task breakdown", prompt: "..." })

// apply — code generation
Agent({ model: "sonnet", description: "sdd-apply: implement tasks", prompt: "..." })

// archive — copy and close
Agent({ model: "haiku", description: "sdd-archive: merge and archive", prompt: "..." })
```

## State Recovery

After context compaction, the orchestrator recovers by:

1. Reading `.ai-team/changes/*/state.yaml` for active changes
2. Reconstructing phase progress from state files
3. Resuming from the current phase

This is automatic — no user intervention needed.

## Integration Rules

- This adapter does NOT replace your existing CLAUDE.md — it extends it
- The orchestrator respects all existing project rules and conventions
- Sub-agents inherit project context through `.ai-team/config.yaml`, not CLAUDE.md
- `/ai-team` commands coexist with any other slash commands you have
