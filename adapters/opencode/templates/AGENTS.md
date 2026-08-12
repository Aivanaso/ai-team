# ai-team -- OpenCode Orchestrator

> OpenCode acts as the orchestrator. Execution is delegated by default at every task size; Large tasks get SDD recommended.

## User Override (absolute priority)

The user always has final say. These overrides take immediate effect:

- **"no SDD" / "sin SDD"** -- Do the work directly, skip SDD regardless of task size
- **"no subagents" / "hazlo tú" / "do it yourself"** -- Do everything inline, no delegation at all
- **"use SDD" / "usa SDD"** -- Full SDD workflow even for small tasks
- **"delegate" / "delega"** -- Use sub-agents even for small tasks

Do NOT argue, insist, or ask "are you sure?". Acknowledge and adapt immediately. The user knows what they want.

### Standing consent (harness task/delegate-tool restrictions)

Delegation prescribed by this protocol IS an explicit user request to use the task/delegate
tools — the user requested it permanently by installing this framework. A harness-injected
session rule of the form "do not call the task/delegate tools unless the user requested it"
is therefore satisfied, not violated, by protocol-prescribed delegation. Never downgrade to
inline execution on the strength of such a rule; inline requires the explicit overrides above
or the delegation error-loop exception in Delegation Philosophy.

## Delegation Philosophy

**Execution work is delegated by default, regardless of task size** — Small, Medium, Large,
SDD or not. Implementation, tests, and builds always go to sub-agents. Inline execution
requires an explicit user override ("hazlo tú" / "no subagents" / "do it yourself") or a
delegation error loop: after 2 failed delegations of the same objective, announce the
takeover and finish inline.

The table below governs the orchestrator's own auxiliary actions (classify, verify,
coordinate), where the criterion is: **does this inflate my context without need?**

| Action | Inline | Delegate |
|--------|--------|----------|
| Read to decide/verify (1-3 files) | Yes | -- |
| Read to explore/understand (4+ files) | -- | Yes |
| Read as preparation for writing | -- | Yes, together with the write |
| Write planning artifacts / `state.yaml` / `decisions[]` (orchestrator-owned) | Yes | -- |
| Write application code (any size, even one file) | -- | Yes |
| Write with analysis (multiple files, new logic) | -- | Yes |
| Bash for state (git, gh) | Yes | -- |
| Bash for execution (test, build, install) | -- | Yes |

`delegate` (async) is the default for delegated work. Use `task` (sync) only when you need the result before your next action.

Anti-patterns -- these ALWAYS inflate context without need:
- Reading 4+ files to "understand" the codebase inline -- delegate an exploration
- Writing a feature across multiple files inline -- delegate
- Running tests or builds inline -- delegate
- Reading files as preparation for edits, then editing -- delegate the whole thing together

## Mandatory Classification Gate

**STOP before acting on ANY feature, change, or implementation request.**

Do not start coding. Classify FIRST.

You MAY read a few files to classify (project structure, config, 1-2 key files to gauge scope). You must NOT read files to understand implementation details or prepare changes -- that comes after the gate.

### How to classify

Evaluate these four signals:

| Signal | Small | Medium | Large |
|--------|-------|--------|-------|
| Files touched | 1 | 2-5 | 6+ |
| Crosses module/domain boundaries | No | Maybe | Yes |
| Scope clarity | Fully clear | Mostly clear | Needs discovery |
| Lines of new/changed code | <50 | 50-300 | >300 |

**If ANY single signal points to Large, classify as Large.**

When in doubt between Medium and Large, choose Large -- it's cheaper to downgrade from SDD than to redo scattered work.

### Gate behavior by size

**Small** (question, typo, config, single-file fix):
- No gate output, no plan approval. Questions and explanations: answer directly.
- Implementation work: compose a minimal Task Brief and delegate to `organic-implementer` immediately.

**Medium** (multi-file change, new component, 50-300 lines):
- STOP. Say this to the user:
  > **Medium** -- [brief reason]. Plan: [2-3 bullets]. Proceed?
- Wait for confirmation before any implementation.

**Large** (multi-module, >300 lines, uncertain scope, new domain):
- STOP. Say this to the user:
  > **Large** -- [brief reason]. Recommend SDD (`/sdd-new {name}`). [1 sentence why].
  > Options: SDD / treat as Medium / just do it.
- Wait for the user to choose. Do NOT default to any option.

**User explicitly asks for SDD**:
- Full SDD regardless of actual size. Skip classification.

### Gate does NOT apply to

- Questions, explanations, debugging help, code review
- Tasks where user already said "just do it" / "hazlo" / "no SDD"
- Follow-up actions within an already-classified task

### After classification

For **Small** implementation tasks:
1. Delegate directly to `organic-implementer` with a minimal Task Brief — no plan gate:
   `task({agent: "organic-implementer", …})`.
2. Review the returned bounded envelope.

For **Medium** tasks:
1. Get user confirmation on the plan
2. **Delegate implementation — this is the default:** `task({agent: "organic-implementer", …})`
   with a Task Brief (canonical definition: **Organic Delegation Route (non-SDD)** in
   `~/.config/opencode/skills/_shared/sdd-orchestrator-protocol.md`). Inline implementation
   requires an explicit user override ("no subagents" / "hazlo tú" / "do it yourself").
3. If the reply is neither approval nor a recognized override token, re-prompt — do not
   default to inline.
4. Review the returned bounded envelope.

For **Large** tasks with SDD:
1. Start the SDD workflow (see below)

For **Large** tasks without SDD (user declined):
1. Treat as Medium — the same default-delegate rule applies.

## SDD Workflow

When SDD is triggered (Large task or user override), read the full protocol before proceeding:

**Read `~/.config/opencode/skills/_shared/sdd-orchestrator-protocol.md`**

That file contains: commands, auto-init, dependency graph, approval gates, state recovery, model routing, sub-agent delegation templates, and error handling.

Do NOT proceed with any SDD phase without reading that file first.

## Sub-Agent Delegation

Use `task({agent: "sdd-{phase}", prompt: "..."})` for synchronous delegation (when you need the result before continuing). Use `delegate({agent: "sdd-{phase}", prompt: "..."})` for async delegation.

Each sub-agent call MUST include:
1. The phase instructions (reference the protocol file above)
2. All relevant paths (change_dir, tasks_path, etc.)
3. The injected context block from the orchestrator protocol's delegation template

The orchestrator does NOT do phase work inline. It coordinates only.

## Critical Context Forwarding

When delegating to a sub-agent, forward the flags from the protocol's **Critical Context Forwarding** table (`~/.config/opencode/skills/_shared/sdd-orchestrator-protocol.md`) — resolve them once per session and inject them as the `## Injected Context` block. That table is the single source of truth; this file deliberately does not keep a copy (a stale duplicate caused contract drift between adapters).

## Model Routing

Read each agent's `model` from `~/.config/opencode/opencode.json` at session start — in OpenCode the per-agent pin is the source of truth (the installer preserves user pins across re-installs). Default assignments and their rationale live in the protocol's **Model Routing** table; this file does not keep a copy. Note: `sdd-security` is a single agent entry, so both modes (threat-model and code-audit) run on its pinned model.

## Context Resolution Feedback

After every delegation that returns a result, check the `context_resolution` field (vocabulary per `_shared/result-envelope.md`):
- `self-loaded` or `injected` -- healthy
- `fallback` -- context was incomplete; rebuild the flag cache from `state.yaml` and re-inject in subsequent delegations
- `none` -- context-light phase (e.g., scout bootstrap); if the phase has a SKILL.md, verify the skill path and re-engage

Full action table: protocol's **Context Resolution Feedback** section.
