# ai-team

A tool-agnostic framework for organic, evidence-tiered AI agent delegation.

## How It Works

One execution model for every task size. The orchestrator (your AI coding tool's main
conversation) classifies each request, delegates implementation to `organic-implementer`,
and lets the evidence in the resulting diff — not the task's size — decide how much review
runs before commit.

```
User ↔ Claude Code (orchestrator)          User ↔ OpenCode (orchestrator agent)
           │                                             │
           ├── Small: delegate (no gate)                 ├── Small: delegate (no gate)
           ├── Medium: plan + delegate                    ├── Medium: plan + delegate
           └── Large: plan + optional discovery pass       └── Large: plan + optional discovery pass
                         ↓                                             ↓
                    domain/skills/    ←─── shared skills ───→    domain/skills/
```

### Classification (plan ceremony only)

| Size | Signals | Ceremony |
|------|---------|----------|
| **Small** | 1 file, <50 lines, fully clear scope | Delegate directly, no gate (trivial mechanical edits run inline) |
| **Medium** | 2-5 files, 50-300 lines | Present a plan, wait for confirmation, then delegate |
| **Large** | 6+ files, crosses modules, needs discovery | Present a plan, offer an optional `organic-scout` discovery pass, wait, then delegate |

Classification never decides review depth — only how much planning precedes delegation.

### Evidence-tiered review (post-candidate)

Once `organic-implementer` returns a candidate, the orchestrator classifies its diff into a
review tier and names the reason:

| Tier | Trigger | Review |
|------|---------|--------|
| **0** | Docs, comments, non-runtime config, renames | Result envelope only — no reviewer |
| **1** | Standard code change | `organic-reviewer` (correctness + verification) |
| **2** | Auth/authz, crypto, secrets, payments, PII, migrations, untrusted-input parsing, permission checks, public contracts | `organic-reviewer` + `organic-security` |

A tier ≥ 1 candidate produces a **Review Receipt**; `work-unit-commits` refuses to commit
tier ≥ 1 work without one. The user can accept-and-proceed over a finding instead of
re-engaging the worker (recorded in the receipt's `overrides` field).

### Review kill switch

"review off" / "sin review" turns the review plane off entirely — no tiers, nothing ever
reported as reviewed or approved while off. "review on" re-validates from the current state
only; nothing is retroactively resurrected.

## Project Structure

```
ai-team/
├── domain/
│   └── skills/
│       ├── _shared/                  # Protocols shared by every skill
│       │   ├── context-protocol.md
│       │   ├── persistence-contract.md
│       │   ├── result-envelope.md
│       │   ├── evidence-protocol.md
│       │   ├── common-rules.md
│       │   └── orchestrator-protocol.md   # classification, tiers, delegation, model routing
│       ├── organic-implementer/      # Task Brief → code
│       ├── organic-reviewer/         # correctness + verification review gate
│       ├── organic-security/         # threat-model / code-audit security lens
│       ├── organic-scout/            # bootstrap config.yaml / pre-brief discovery
│       └── work-unit-commits/        # atomic commits per logical group
├── adapters/
│   ├── claude-code/                  # Claude Code adapter
│   │   ├── install.sh
│   │   ├── templates/
│   │   │   ├── CLAUDE.md             # Stub injected into ~/.claude/CLAUDE.md
│   │   │   └── agents/               # Agent files → ~/.claude/agents/
│   │   └── README.md
│   └── opencode/                     # OpenCode adapter
│       ├── install.sh
│       ├── templates/
│       │   ├── AGENTS.md             # Copied to ~/.config/opencode/AGENTS.md
│       │   └── opencode.json         # Merged into ~/.config/opencode/opencode.json
│       └── README.md
├── scripts/
│   └── install.sh                    # Adapter selector (routes to adapters/<name>/install.sh)
└── config/
    ├── schema.yaml                   # .ai-team/config.yaml field reference
    └── project-config.template.yaml  # Annotated illustration of every config.yaml key (same key set as organic-scout's config-template.md)
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

Requires `jq`. Copies skills to `~/.config/opencode/skills/`, installs `AGENTS.md`, and merges agent definitions into `opencode.json`.

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

Each adapter installs an independent copy of the framework into its tool's config directory. Multi-adapter install is supported via `--adapter=both`. Adapters do not share installed files — `~/.claude/` and `~/.config/opencode/` are completely separate. Both adapters use the same `domain/skills/` source, so the delegation logic is identical regardless of which tool you use.

## Adapters

| Adapter | Status | Install target |
|---------|--------|----------------|
| Claude Code | Done | `~/.claude/` |
| OpenCode | Done | `~/.config/opencode/` |

Contributions for other tools welcome — see `adapters/claude-code/` or `adapters/opencode/` as reference implementations.

## No pipeline entry commands

There is no multi-phase pipeline and no slash-command entry point. Delegation is
conversational: describe the change, the orchestrator classifies it, and everything after
that follows the model above.

## Persistence

Every delegated worker is stateless: it reads its skill file and the delegation prompt, writes
the files its brief declares, and returns one bounded result envelope. There is no phase
tracking and no `state.yaml`. A project accumulates these filesystem artifacts:

- `.ai-team/config.yaml` — project stack, conventions, structure, architecture, and
  `commit_strategy` (default `auto`), written once by `organic-scout` on first bootstrap, then
  read by every worker. Optional keys (`strict_tdd`, `test_commands`, `model_overrides`,
  `rules`) are not written by bootstrap — they default safely when absent, and are added later
  by hand or via the orchestrator's Config Refresh Check.
- `.ai-team/skill-registry.md` and `.ai-team/.skill-registry.cache` — the stack/convention
  skill index and its freshness fingerprint, refreshed once per session (see the orchestrator
  protocol's Session Init → "Skill Registry Refresh").
- An on-disk report copy, only when a reviewer or security pass runs with a
  `report_destination` injected.

## Model Routing

Read `domain/skills/_shared/orchestrator-protocol.md` → "Model Routing" for the default model
per worker and the project-level `model_overrides` override mechanism.

## Skills

| Skill | Role |
|-------|------|
| `organic-implementer` | Task Brief → code, bounded by declared edit roots |
| `organic-reviewer` | Correctness + verification review gate (tier ≥ 1) |
| `organic-security` | Threat-model and code-audit security lens (tier 2, or standalone) |
| `organic-scout` | Bootstrap `config.yaml`, or run pre-brief discovery |
| `work-unit-commits` | Atomic commit per logical group; enforces the receipt gate |

## License

MIT
