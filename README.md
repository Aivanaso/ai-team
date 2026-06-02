# ai-team

A tool-agnostic framework for spec-driven development with AI agents.

## Architecture

Each supported AI coding tool runs an **orchestrator** agent: small tasks inline, large tasks via SDD with sub-agents. The orchestrator classifies every task by size and delegates accordingly.

```
User ↔ Claude Code (orchestrator)          User ↔ OpenCode (sdd-orchestrator agent)
           │                                             │
           ├── Small: inline                             ├── Small: inline
           ├── Medium: plan + delegate                   ├── Medium: plan + delegate
           └── Large: full SDD pipeline                  └── Large: full SDD pipeline
                         ↓                                             ↓
                    domain/skills/    ←─── shared skills ───→    domain/skills/
```

### Core Principles

- **Classification gate** -- Every task is classified (Small/Medium/Large) before execution
- **Specs as source of truth** -- Committed to git, living documentation
- **Filesystem-only persistence** -- Human-readable, version-controllable, no external services
- **Named agent types** -- Sub-agents use dedicated agent files with tool restrictions; instructions read from disk (JIT)
- **Tool-agnostic skills** -- Skills in `domain/skills/` are adapter-independent

## Project Structure

```
ai-team/
├── domain/
│   └── skills/
│       ├── _shared/                  # Protocols shared by all skills
│       │   ├── context-protocol.md
│       │   ├── persistence-contract.md
│       │   ├── result-envelope.md
│       │   ├── spec-convention.md
│       │   ├── evidence-protocol.md
│       │   └── sdd-orchestrator-protocol.md  # DAG, model routing, delegation
│       ├── sdd-scout/
│       ├── sdd-propose/
│       ├── sdd-spec/
│       ├── sdd-design/
│       ├── sdd-tasks/
│       ├── sdd-apply/
│       ├── sdd-verify/
│       ├── sdd-archive/
│       ├── sdd-security/
│       └── work-unit-commits/
├── adapters/
│   ├── claude-code/                  # Claude Code adapter
│   │   ├── install.sh
│   │   ├── templates/
│   │   │   ├── CLAUDE.md             # Stub injected into ~/.claude/CLAUDE.md
│   │   │   └── agents/              # Agent files → ~/.claude/agents/sdd-*.md
│   │   └── README.md
│   └── opencode/                     # OpenCode adapter
│       ├── install.sh
│       ├── templates/
│       │   ├── AGENTS.md             # Copied to ~/.config/opencode/AGENTS.md
│       │   ├── opencode.json         # Merged into ~/.config/opencode/opencode.json
│       │   └── commands/             # Slash commands (sdd-new, sdd-continue, etc.)
│       └── README.md
├── scripts/
│   └── install.sh                    # Adapter selector (routes to adapters/<name>/install.sh)
└── config/
    └── project-config.template.yaml
```

## Installation

### Claude Code

```bash
./scripts/install.sh --adapter=claude-code
```

Copies skills to `~/.claude/skills/`, agent files to `~/.claude/agents/`, and injects a lightweight orchestrator stub into `~/.claude/CLAUDE.md` between `<!-- ai-team:orchestrator -->` markers.

### OpenCode

```bash
./scripts/install.sh --adapter=opencode
```

Requires `jq`. Copies skills to `~/.config/opencode/skills/`, installs `AGENTS.md`, merges agent definitions into `opencode.json`, and copies slash commands to `~/.config/opencode/commands/`.

### Both adapters

```bash
./scripts/install.sh --adapter=both
```

### Interactive prompt

```bash
./scripts/install.sh          # prompts if no adapter specified
```

Re-run after pulling updates to refresh skills and adapter templates.

## Choosing an Adapter

Each adapter installs an independent copy of the framework into its tool's config directory. Multi-adapter install is supported via `--adapter=both`. Adapters do not share installed files — `~/.claude/` and `~/.config/opencode/` are completely separate. Both adapters use the same `domain/skills/` source, so the SDD pipeline logic is identical regardless of which tool you use.

## Adapters

| Adapter | Status | Install target |
|---------|--------|----------------|
| Claude Code | Done | `~/.claude/` |
| OpenCode | Done | `~/.config/opencode/` |

Contributions for other tools welcome — see `adapters/claude-code/` or `adapters/opencode/` as reference implementations.

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
propose → spec ──→ tasks → apply → verify → review → archive
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
| archive | sdd-archive | sonnet | Merge delta specs into base, archive artifacts |
| security | sdd-security | opus | Threat-model (shift-left) and code-audit (post-apply) |
| review | sdd-reviewer | opus | Code-correctness gate: reviews the group's changed files, blocking verdict |

Approval gates pause after **propose** and before **apply**. Security gates (threat-model and code-audit) fire when the change touches sensitive surfaces.

### Fast-Forward

For straightforward changes you can chain the planning phases (propose → spec → design → tasks) in a single invocation:

```
/ai-team ff <change-name>
```

Default mode is `interactive` (pause with a summary after each phase). Switch to `auto` for back-to-back execution that only pauses at blocking gates. Apply, verify and archive remain manual.

### Verify: Two-Layer Compliance

The verify phase validates applied code through two complementary layers:

- **Static correctness** -- Code review: does the code structurally handle each spec scenario?
- **Behavioral compliance** -- Test execution: does a passing test prove each scenario works?

A scenario is only COMPLIANT when both layers pass.

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

### Claude Code

```
/ai-team new <change-name>       # Start a new SDD change
/ai-team ff <change-name>        # Fast-forward planning (propose → spec → design → tasks)
/ai-team continue [change-name]  # Resume an active change
/ai-team status [change-name]    # Show change progress
/ai-team explore <topic>         # Investigate without starting SDD
/ai-team baseline <domain>       # Document existing code as a spec
```

### OpenCode

OpenCode users invoke these as slash commands routed to the `sdd-orchestrator` agent:

```
/sdd-new <change-name>     Start a new SDD change
/sdd-continue [change]     Resume an active change
/sdd-status [change]       Show change progress
/sdd-explore <topic>       Investigate without starting SDD
/sdd-baseline <domain>     Document existing code as a spec
```

OpenCode uses `/sdd-new`, Claude Code uses `/ai-team new`. The underlying SDD pipeline is identical.

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
| sdd-security | Done |
| work-unit-commits | Done |
| sdd-reviewer | Done |

## License

MIT
