# ai-team

A tool-agnostic framework for spec-driven development with AI agents.

## Architecture

Claude Code acts as the **orchestrator**: small tasks inline, large tasks via SDD with sub-agents. The orchestrator classifies every task by size and delegates accordingly.

```
User ↔ Claude Code (orchestrator)
           │
           ├── Small: inline (no delegation)
           ├── Medium: plan + delegate to sub-agent
           └── Large: full SDD pipeline with phase sub-agents
                         ↓
                    .ai-team/    ← filesystem is the shared memory
```

### Core Principles

- **Classification gate** -- Every task is classified (Small/Medium/Large) before execution
- **Specs as source of truth** -- Committed to git, living documentation
- **Filesystem-only persistence** -- Human-readable, version-controllable, no external services
- **Fresh context per delegation** -- Sub-agents start clean, receive instructions inline

## Project Structure

```
ai-team/
├── skills/
│   ├── _shared/                  # Protocols shared by all skills
│   │   ├── context-protocol.md   # Sub-agent startup sequence
│   │   ├── persistence-contract.md
│   │   ├── result-envelope.md    # Structured return format
│   │   ├── spec-convention.md    # Spec format and merge rules
│   │   └── sdd-orchestrator-protocol.md  # DAG, model routing, delegation
│   ├── sdd-scout/                # Project inspector + codebase explorer
│   ├── sdd-propose/              # Feature → proposal with ACs
│   ├── sdd-spec/                 # Proposal → domain delta specs
│   ├── sdd-design/               # Specs → technical design
│   ├── sdd-tasks/                # Design → ordered task plan
│   ├── sdd-apply/                # Tasks → code implementation
│   ├── sdd-verify/               # Two-layer compliance validation
│   └── sdd-archive/              # Merge specs + archive artifacts
├── adapters/
│   └── claude/                   # Claude Code orchestrator adapter
│       └── CLAUDE.md             # Injected into ~/.claude/CLAUDE.md
├── scripts/
│   └── install.sh                # Install skills + orchestrator
└── config/
    └── project-config.template.yaml
```

## Installation

```bash
./scripts/install.sh
```

This copies skills to `~/.claude/skills/` and injects the orchestrator into `~/.claude/CLAUDE.md` between `<!-- ai-team:orchestrator -->` markers. Re-run after pulling updates.

## How It Works

### Size Classification

The orchestrator classifies every feature/change request before acting:

| Size | Signals | Workflow |
|------|---------|----------|
| **Small** | 1 file, <50 lines, fully clear scope | Inline -- no delegation |
| **Medium** | 2-5 files, 50-300 lines | Plan, confirm with user, delegate |
| **Large** | 6+ files, crosses domains, needs discovery | Recommend SDD pipeline |

### SDD Pipeline

For large changes, the full Spec-Driven Development pipeline:

```
propose → spec ──→ tasks → apply → verify → archive
        → design ↗
```

| Phase | Skill | Model | What it does |
|-------|-------|-------|--------------|
| propose | sdd-propose | opus | Feature → proposal with scope, ACs, risks |
| spec | sdd-spec | sonnet | Proposal → domain delta specs (Given/When/Then) |
| design | sdd-design | opus | Specs → technical design grounded in codebase |
| tasks | sdd-tasks | sonnet | Design → ordered, grouped implementation plan |
| apply | sdd-apply | sonnet | Tasks → actual code, one task at a time |
| verify | sdd-verify | sonnet | Two-layer validation: static + behavioral |
| archive | sdd-archive | haiku | Merge delta specs into base, archive artifacts |

Approval gates pause after **propose** and before **apply** for user review.

### Verify: Two-Layer Compliance

The verify phase validates applied code through two complementary layers:

- **Static correctness** -- Code review: does the code structurally handle each spec scenario?
- **Behavioral compliance** -- Test execution: does a passing test prove each scenario works?

A scenario is only COMPLIANT when both layers pass. Code existing is not enough -- tests must prove it.

### Persistence

All SDD artifacts live in `.ai-team/` within the target project:

```
.ai-team/
├── config.yaml                  # Project stack, conventions, rules
├── specs/{domain}/spec.md       # Base specs (committed to git)
├── changes/{change-name}/       # Active change artifacts (gitignored)
│   ├── state.yaml               # Phase tracking (source of truth)
│   ├── proposal.md
│   ├── specs/{domain}/spec.md   # Delta specs
│   ├── design.md
│   ├── tasks.md
│   └── verification-report.md
└── changes/archive/             # Completed changes (committed)
```

## Commands

```
/ai-team new <change-name>       # Start a new SDD change
/ai-team continue [change-name]  # Resume an active change
/ai-team status [change-name]    # Show change progress
/ai-team explore <topic>         # Investigate without starting SDD
/ai-team baseline <domain>       # Document existing code as a spec
```

## Adapters

ai-team is tool-agnostic. The orchestrator protocol can be adapted to any AI coding tool:

| Adapter | Status |
|---------|--------|
| Claude Code | Done |
| Others | Contributions welcome |

## Status

All SDD pipeline phases are implemented:

| Skill | Status |
|-------|--------|
| sdd-scout | Done |
| sdd-propose | Done |
| sdd-spec | Done |
| sdd-design | Done |
| sdd-tasks | Done |
| sdd-apply | Done |
| sdd-verify | Done |
| sdd-archive | Done |

## License

MIT
