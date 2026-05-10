---
description: Explore a topic or area of the codebase without starting a full SDD change
agent: sdd-orchestrator
---

Follow the SDD orchestrator workflow for `/sdd-explore`:

WORKFLOW:
1. Delegate `sdd-scout` in explore mode to investigate the topic in the current codebase
2. Present the scout findings inline — no proposal, no pipeline, no state files created

CONTEXT:
- Working directory: !`echo -n "$(pwd)"`
- Current project: !`echo -n "$(basename $(pwd))"`
- Args: $ARGUMENTS

Read the orchestrator instructions at ~/.config/opencode/AGENTS.md and the protocol at
~/.config/opencode/skills/_shared/sdd-orchestrator-protocol.md to coordinate this workflow.
Do NOT execute phase work inline — delegate to sub-agents via `task({agent: "sdd-{phase}", ...})`.
