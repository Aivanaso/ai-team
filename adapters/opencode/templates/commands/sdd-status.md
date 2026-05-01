---
description: Show the progress of an active SDD change
agent: sdd-orchestrator
---

Follow the SDD orchestrator workflow for `/sdd-status`:

WORKFLOW:
1. Read `.ai-team/changes/{change}/state.yaml` inline (no delegation needed)
2. Format and display the phase status: done / pending / skipped / blocked for each phase
3. If blocked, show the blocked_reason and suggest a resolution path

CONTEXT:
- Working directory: !`echo -n "$(pwd)"`
- Current project: !`echo -n "$(basename $(pwd))"`
- Args: $ARGUMENTS

Read the orchestrator instructions at ~/.config/opencode/AGENTS.md and the protocol at
~/.config/opencode/skills/_shared/sdd-orchestrator-protocol.md to coordinate this workflow.
Status is a read-only operation — do NOT delegate to sub-agents unless the user asks for a full refresh.
