---
description: Resume an active SDD change — runs the next dependency-ready phase
agent: sdd-orchestrator
---

Follow the SDD orchestrator workflow for `/sdd-continue`:

WORKFLOW:
1. Read `.ai-team/changes/{change}/state.yaml` to identify the current phase and blocked state
2. Determine which phases are dependency-ready (check the DAG in the orchestrator protocol)
3. Delegate the next pending phase to the appropriate sub-agent
4. Present the phase result to the user and ask whether to continue to the next phase

CONTEXT:
- Working directory: !`echo -n "$(pwd)"`
- Current project: !`echo -n "$(basename $(pwd))"`
- Args: $ARGUMENTS

Read the orchestrator instructions at ~/.config/opencode/AGENTS.md and the protocol at
~/.config/opencode/skills/_shared/sdd-orchestrator-protocol.md to coordinate this workflow.
Do NOT execute phase work inline — delegate to sub-agents via `task({agent: "sdd-{phase}", ...})`.
