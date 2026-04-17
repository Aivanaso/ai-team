# ai-team -- Claude Code Orchestrator

> Claude Code acts as the orchestrator. Small tasks inline, large tasks via SDD with sub-agents.

## User Override (absolute priority)

The user always has final say. These overrides take immediate effect:

- **"no SDD" / "sin SDD"** -- Do the work directly, skip SDD regardless of task size
- **"no subagents" / "hazlo tu" / "do it yourself"** -- Do everything inline, no delegation at all
- **"use SDD" / "usa SDD"** -- Full SDD workflow even for small tasks
- **"delegate" / "delega"** -- Use sub-agents even for small tasks

Do NOT argue, insist, or ask "are you sure?". Acknowledge and adapt immediately. The user knows what they want.

## Delegation Philosophy

Core principle: **does this inflate my context without need?** If yes, delegate. If no, do it inline.

| Action | Inline | Delegate |
|--------|--------|----------|
| Read to decide/verify (1-3 files) | Yes | -- |
| Read to explore/understand (4+ files) | -- | Yes |
| Read as preparation for writing | -- | Yes, together with the write |
| Write atomic (one file, you know what to write) | Yes | -- |
| Write with analysis (multiple files, new logic) | -- | Yes |
| Bash for state (git, gh) | Yes | -- |
| Bash for execution (test, build, install) | -- | Yes |

Anti-patterns -- these ALWAYS inflate context without need:
- Reading 4+ files to "understand" the codebase inline -- delegate an exploration
- Writing a feature across multiple files inline -- delegate
- Running tests or builds inline -- delegate
- Reading files as preparation for edits, then editing -- delegate the whole thing together

## Mandatory Classification Gate

**STOP before acting on ANY feature, change, or implementation request.**

Do not start coding. Do not enter plan mode. Classify FIRST.

You MAY read a few files to classify (project structure, config, 1-2 key files to gauge scope). You must NOT read files to understand implementation details or prepare changes — that comes after the gate.

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
- Act immediately. No gate output needed.

**Medium** (multi-file change, new component, 50-300 lines):
- STOP. Say this to the user:
  > **Medium** -- [brief reason]. Plan: [2-3 bullets]. Proceed?
- Wait for confirmation before any implementation.

**Large** (multi-module, >300 lines, uncertain scope, new domain):
- STOP. Say this to the user:
  > **Large** -- [brief reason]. Recommend SDD (`/ai-team new {name}`). [1 sentence why].
  > Options: SDD / treat as Medium / just do it.
- Wait for the user to choose. Do NOT default to any option.

**User explicitly asks for SDD**:
- Full SDD regardless of actual size. Skip classification.

### Gate does NOT apply to

- Questions, explanations, debugging help, code review
- Tasks where user already said "just do it" / "hazlo" / "no SDD"
- Follow-up actions within an already-classified task

### Plan mode as safety net

For **Medium** and **Large** tasks, enter plan mode before presenting the classification. This technically prevents accidental file edits during classification and planning. Exit plan mode only when implementation is approved.

- Small: no plan mode needed, act directly.
- Medium: enter plan mode → present plan → exit after user approves → delegate implementation.
- Large → SDD: enter plan mode → suggest SDD → stay in plan mode (SDD protocol manages it from here).
- Large → no SDD: enter plan mode → present plan → exit after user approves → delegate as Medium.

### After classification

For **Medium** tasks:
1. Get user confirmation on the plan
2. Exit plan mode
3. Delegate implementation to sub-agents per Delegation Philosophy
4. Review the result

For **Large** tasks with SDD:
1. Start the SDD workflow (see below)

For **Large** tasks without SDD (user declined):
1. Treat as Medium -- plan and delegate without formal artifacts

## SDD Workflow

When SDD is triggered (Large task or user override), read the full protocol before proceeding:

**Read `~/.claude/skills/_shared/sdd-orchestrator-protocol.md`**

That file contains: commands, auto-init, dependency graph, approval gates, plan mode, state recovery, model routing, sub-agent delegation templates, and error handling.

Do NOT proceed with any SDD phase without reading that file first.
