# ai-team

A tool-agnostic AI agent team for spec-driven development.

## Architecture

ai-team uses a **delegate-only orchestrator** that never reads code itself. It delegates ALL work to sub-agents with fresh context windows, avoiding context bloat and compaction issues.

```
User ↔ Orchestrator ↔ Sub-agents (fresh context each)
              ↓
         .ai-team/          ← filesystem is the shared memory
```

### Core Principles

- **Orchestrator never reads code** — it only coordinates and processes summaries
- **Fresh context per delegation** — sub-agents start clean, load only what's needed
- **Specs as source of truth** — committed to git, living documentation
- **Filesystem-only persistence** — human-readable, version-controllable, no external services

## Project Structure

```
ai-team/
├── agents/
│   ├── _shared/              # Protocols shared by all agents
│   │   ├── context-protocol.md
│   │   ├── persistence-contract.md
│   │   ├── result-envelope.md
│   │   └── spec-convention.md
│   ├── orchestrator/         # Delegate-only coordinator
│   │   └── AGENT.md
│   ├── sdd-scout/            # Project inspector + codebase explorer
│   │   └── AGENT.md
│   └── sdd-propose/          # PRD → RFC proposal generator
│       └── AGENT.md
├── config/
│   ├── schema.yaml           # Artifact dependency graph (DAG)
│   └── project-config.template.yaml
├── adapters/
│   └── claude-code/          # Claude Code integration
│       └── CLAUDE.md
└── scripts/
    └── init-project.sh       # Bootstrap .ai-team/ in target projects
```

## Quick Start

### 1. Bootstrap a project

```bash
# Option A: Shell script (creates directories only)
./scripts/init-project.sh /path/to/your/project

# Option B: Inside Claude Code (full detection)
/ai-team init
```

### 2. Explore the codebase

```
/ai-team explore "authentication flow"
```

### 3. Start a change (Phase 2+)

```
/ai-team new user-authentication
```

## SDD Workflow

The Spec-Driven Development workflow follows a DAG of phases:

```
propose → spec ──→ tasks → apply → verify → archive
        → design ↗
```

Each phase produces artifacts that feed into the next. The orchestrator manages the flow and pauses at approval gates for user review.

## Adapters

ai-team is tool-agnostic. Adapters translate the orchestrator's delegation protocol to specific AI coding tools:

| Adapter | Status |
|---------|--------|
| Claude Code | Phase 1 |
| OpenCode | Planned |
| Cursor | Planned |
| Gemini CLI | Planned |

## Current Status

**Phase 2** — Core SDD loop in progress.

### Roadmap

- Phase 2: sdd-propose (done) + sdd-spec + sdd-apply (core SDD loop)
- Phase 3: sdd-design + sdd-tasks + sdd-verify + sdd-archive (full lifecycle)
- Phase 4: code-review + refactor specialists
- Phase 5: Additional tool adapters
- Phase 6: setup.sh installer script
