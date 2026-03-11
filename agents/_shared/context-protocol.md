# Context Protocol

> How every sub-agent loads context on startup.

## Purpose

Sub-agents are launched with **fresh context windows**. This protocol defines the exact sequence each agent follows to build situational awareness without inheriting orchestrator state.

## Startup Sequence

Every sub-agent MUST execute these steps in order:

### Step 1 — Load Skill Registry

```
Read .ai-team/skill-registry.md
```

- Scan the registry for skills matching your domain (e.g., if you're working on a React component, find `react`, `typescript`, `testing` skills)
- Read the `SKILL.md` files for each matched skill
- These skills define coding conventions, patterns, and constraints for the target project

### Step 2 — Load Project Config

```
Read .ai-team/config.yaml
```

- Understand the project's tech stack, conventions, and rules
- Note any project-specific constraints (e.g., "no default exports", "use pnpm")

### Step 3 — Load Artifacts Referenced by Orchestrator

The orchestrator passes explicit artifact paths in your launch prompt. Read ONLY those artifacts:

```
# Example orchestrator delegation:
"Read .ai-team/changes/user-auth/proposal.md and .ai-team/specs/auth/spec.md"
```

- Read each referenced artifact in full
- These are your source of truth for the current task

### Step 4 — Begin Work

With context loaded, execute your specific task as defined in your AGENT.md.

## Rules

| Rule | Description |
|------|-------------|
| **Minimal context** | NEVER load more than what the orchestrator explicitly references |
| **No exploration** | Do not scan the `.ai-team/` directory for "interesting" files |
| **No orchestrator state** | You have NO access to the orchestrator's conversation history |
| **Skill-first** | Always load skills before starting work — they define HOW you work |
| **Fail fast** | If a referenced artifact doesn't exist, return `status: blocked` immediately |

## Example: Full Startup

```
# 1. Skills
Read .ai-team/skill-registry.md
→ Found: react, typescript, testing
Read react/SKILL.md, typescript/SKILL.md, testing/SKILL.md

# 2. Config
Read .ai-team/config.yaml
→ Stack: React 19 + TypeScript + Vitest, monorepo with pnpm

# 3. Artifacts (from orchestrator prompt)
Read .ai-team/changes/user-auth/proposal.md
Read .ai-team/specs/auth/spec.md

# 4. Work
→ Execute task per AGENT.md instructions
```
