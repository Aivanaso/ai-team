---
description: Start a new SDD change — runs scout exploration then creates a proposal
agent: sdd-orchestrator
---

Follow the SDD orchestrator workflow for `/sdd-new`:

WORKFLOW:
1. Read `.ai-team/config.yaml` in the current project to understand stack and conventions
2. Run the health-check baseline: delegate `sdd-scout` in baseline mode to document current state
3. Classify the change scope against the classification signals (Small/Medium/Large)
4. Delegate `sdd-propose` to create a structured proposal with acceptance criteria and risks
5. Present the proposal summary to the user and await approval before proceeding to design/spec

CONTEXT:
- Working directory: !`echo -n "$(pwd)"`
- Current project: !`echo -n "$(basename $(pwd))"`
- Args: $ARGUMENTS

Read the orchestrator instructions at ~/.config/opencode/AGENTS.md and the protocol at
~/.config/opencode/skills/_shared/sdd-orchestrator-protocol.md to coordinate this workflow.
Do NOT execute phase work inline — delegate to sub-agents via `task({agent: "sdd-{phase}", ...})`.
