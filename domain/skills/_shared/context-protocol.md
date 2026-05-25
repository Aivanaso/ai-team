# Context Protocol

> How every sub-agent loads context on startup.

## Purpose

Sub-agents are launched with **fresh context windows**. The orchestrator injects instructions and protocols inline in the prompt. This protocol defines what the sub-agent reads from the filesystem.

## Startup Sequence

Every sub-agent MUST execute these steps in order:

### Step 1 — Load Project Config

```
Read .ai-team/config.yaml
```

- Understand the project's tech stack, conventions, and rules
- Note any project-specific constraints (e.g., "no default exports", "max line length 120", "snake_case file names")

### Step 2 — Load Artifacts Referenced by Orchestrator

The orchestrator passes explicit artifact paths in your launch prompt. Read ONLY those artifacts:

```
# Example orchestrator delegation:
"Read .ai-team/changes/user-auth/proposal.md and .ai-team/specs/auth/spec.md"
```

- Read each referenced artifact in full
- These are your source of truth for the current task

### Step 3 — Begin Work

With context loaded, execute your specific task as defined in your instructions.

## Rules

| Rule | Description |
|------|-------------|
| **Minimal context** | Load only what the orchestrator explicitly references in the delegation prompt. |
| **No exploration** | Read only artifacts listed in the delegation prompt; skip the `.ai-team/` directory unless explicitly referenced. |
| **No orchestrator state** | You have NO access to the orchestrator's conversation history |
| **No skill search** | Your instructions and protocols are already in your prompt — do NOT search for SKILL.md files |
| **Fail fast** | If a referenced artifact doesn't exist, return `status: blocked` immediately |

## Example: Full Startup

```
# 1. Config
Read .ai-team/config.yaml
→ Stack: <frameworks> + <language(s)> + <test runner>, package manager <name>

# 2. Artifacts (from orchestrator prompt)
Read .ai-team/changes/user-auth/proposal.md
Read .ai-team/specs/auth/spec.md

# 3. Work
→ Execute task per instructions
```
