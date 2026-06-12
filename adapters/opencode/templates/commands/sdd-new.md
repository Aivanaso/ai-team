---
description: Start a new SDD change — runs scout exploration then creates a proposal
agent: sdd-orchestrator
---

Follow the SDD orchestrator workflow for `/sdd-new`:

WORKFLOW:
1. Run the protocol's "Auto-Init" in full — it applies on EVERY run, not only when config is missing: existing `.ai-team/config.yaml` → Config Refresh Check; missing → delegate `sdd-scout` in bootstrap mode; both paths → Skill Registry Refresh (the fingerprint cache makes the repeat run free). Then read config.yaml for stack and conventions
2. Health-check baseline (protocol "Health Check"): run the `test_commands` from config.yaml and write `.ai-team/changes/{change}/baseline.md` (exit codes, pass/fail counts, pre-existing failures). In OpenCode run this inline — generic sub-agents are denied by permission.task. This is the test baseline sdd-verify diffs against; it is NOT scout baseline mode (that produces a domain spec)
3. Delegate `sdd-propose` to create a structured proposal with acceptance criteria and risks (an explicit /sdd-new skips the classification gate — the user already chose SDD)
4. Present the proposal summary to the user and await approval before proceeding to design/spec

CONTEXT:
- Working directory: !`echo -n "$(pwd)"`
- Current project: !`echo -n "$(basename $(pwd))"`
- Args: $ARGUMENTS

Read the orchestrator instructions at ~/.config/opencode/AGENTS.md and the protocol at
~/.config/opencode/skills/_shared/sdd-orchestrator-protocol.md to coordinate this workflow.
Do NOT execute phase work inline — delegate to sub-agents via `task({agent: "sdd-{phase}", ...})`.
