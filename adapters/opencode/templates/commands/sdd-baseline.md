---
description: Document existing code as a baseline spec for a given domain
agent: sdd-orchestrator
---

Follow the SDD orchestrator workflow for `/sdd-baseline`:

WORKFLOW:
1. Delegate `sdd-scout` in baseline mode to read and document the existing code in the given domain
2. The scout writes the base spec to `.ai-team/specs/{domain}/spec.md` (baseline-mode output — not the health-check `baseline.md`)
3. Present a summary of what was documented

CONTEXT:
- Working directory: !`echo -n "$(pwd)"`
- Current project: !`echo -n "$(basename $(pwd))"`
- Args: $ARGUMENTS

Read the orchestrator instructions at ~/.config/opencode/AGENTS.md and the protocol at
~/.config/opencode/skills/_shared/sdd-orchestrator-protocol.md to coordinate this workflow.
Do NOT execute phase work inline — delegate to sub-agents via `task({agent: "sdd-{phase}", ...})`.
