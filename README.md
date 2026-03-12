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
│   ├── sdd-propose/          # PRD → RFC proposal generator
│   │   └── AGENT.md
│   ├── sdd-spec/             # Proposal → domain specs (delta + greenfield)
│   │   └── AGENT.md
│   └── sdd-design/           # Specs → technical design (grounded in codebase)
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

### 3. Generate a baseline spec for existing code

```
/ai-team baseline shops
```

### 4. Start a new feature

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

**Phase 2** — Core SDD agents in progress.

| Agent | Status | Description |
|-------|--------|-------------|
| orchestrator | Done | Delegate-only coordinator with escalation logic |
| sdd-scout | Done | Bootstrap, explore, and baseline modes |
| sdd-propose | Done | PRD → proposal with ACs (blocks on vague input) |
| sdd-spec | Done | Proposal → delta/greenfield domain specs |
| sdd-design | Done | Specs → technical design grounded in codebase |
| sdd-tasks | Next | Design → file-level task breakdown |
| sdd-apply | Planned | Tasks → code generation |
| sdd-verify | Planned | Spec compliance verification |
| sdd-archive | Planned | Change archival and base spec promotion |

### Roadmap

- Phase 2: Core SDD loop — propose, spec, design, tasks (in progress)
- Phase 3: Apply + verify + archive (full lifecycle)
- Phase 4: code-review + refactor specialists
- Phase 5: Additional tool adapters
- Phase 6: setup.sh installer script
