# ai-team — Claude Code Adapter

Install the ai-team SDD framework for use with Claude Code.

## Install

```bash
# Via adapter directly:
./adapters/claude-code/install.sh

# Or via the top-level selector:
./scripts/install.sh --adapter=claude-code
```

## Prerequisites

Claude Code must be installed and `~/.claude/` must exist. The installer aborts if that directory is missing.

## What the install does

1. **Copies skills** from `domain/skills/` to `~/.claude/skills/sdd-*/` and `~/.claude/skills/_shared/`
2. **Rewrites skill paths** in `~/.claude/skills/_shared/sdd-orchestrator-protocol.md` — relative `skills/` references become absolute `~/.claude/skills/` paths so Claude can read them without knowing the repo location
3. **Injects orchestrator content** from `adapters/claude-code/templates/CLAUDE.md` inline into `~/.claude/CLAUDE.md`, between `<!-- ai-team:orchestrator -->` and `<!-- /ai-team:orchestrator -->` markers

User content outside the markers is never modified.

## Idempotency

Safe to re-run after pulling new changes. The installer:
- Replaces the existing orchestrator block between markers (marker-based injection, no drift)
- Skips the path-rewrite sed if `~/.claude/skills/` is already in the protocol file (guard prevents double-prefixing)

## Slash commands

Claude Code users invoke the SDD pipeline as:

```
/ai-team new <change>      # Start a new SDD change
/ai-team continue          # Resume an active change
```

These are implemented as slash commands in `~/.claude/CLAUDE.md` (via the injected orchestrator section). The commands route through the orchestrator to SDD sub-agents delegated via the `Agent` tool.

## Note on adapters

Claude Code slash commands use the `/ai-team` namespace (`/ai-team new`, `/ai-team continue`). OpenCode users invoke the same SDD pipeline via `/sdd-new`, `/sdd-continue`. The underlying pipeline and skill files are identical — only the invocation layer differs.

## Uninstall

Remove the orchestrator block from `~/.claude/CLAUDE.md` (between the markers) and delete `~/.claude/skills/` (or just the `sdd-*` and `_shared` subdirectories). The installer does not provide an automated uninstall command.
