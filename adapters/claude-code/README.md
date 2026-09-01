# ai-team — Claude Code Adapter

Install the ai-team organic evidence-tiered delegation framework for use with Claude Code.

## Install

```bash
# Via adapter directly:
./adapters/claude-code/install.sh

# Or via the top-level selector:
./scripts/install.sh --adapter=claude-code
```

## Prerequisites

Claude Code must be installed and `~/.claude/` must exist. The installer aborts if that directory is missing. `python3` (standard library only, no third-party packages) must also be on `PATH` — it runs `check-receipt.py`, the blocking gate the review plane validates every Review Receipt and Brief File ledger sidecar against.

## What the install does

1. **Copies skills** from `domain/skills/` to `~/.claude/skills/{organic-implementer,organic-reviewer,organic-scout,organic-security,organic-retro}/` and `~/.claude/skills/_shared/`
2. **Rewrites skill paths** in `~/.claude/skills/_shared/orchestrator-protocol.md` — relative `skills/` references become absolute `~/.claude/skills/` paths so Claude can read them without knowing the repo location
3. **Injects orchestrator content** from `adapters/claude-code/templates/CLAUDE.md` inline into `~/.claude/CLAUDE.md`, between `<!-- ai-team:orchestrator -->` and `<!-- /ai-team:orchestrator -->` markers

User content outside the markers is never modified.

## Idempotency

Safe to re-run after pulling new changes. The installer:
- Replaces the existing orchestrator block between markers (marker-based injection, no drift)
- Wipes and re-copies each skill directory (including `_shared/`) on every run, so stale files *inside* a still-shipped skill are cleared automatically
- Writes `~/.claude/.ai-team-manifest` listing every installed path; on the next run, paths present in the previous manifest but gone from the source are pruned. Limitation: a pre-manifest install (no `.ai-team-manifest` yet) is never pruned on its first run — skills or agents that a newer framework version removed must be deleted manually once, or delete `~/.claude/skills/` + the framework's `~/.claude/agents/*.md` and re-install

## No slash commands

The organic route has no pipeline entry commands. Delegation is conversational: the orchestrator stub in `~/.claude/CLAUDE.md` classifies every request (Small/Medium/Large) and delegates to `organic-implementer`, with review and commit gated by evidence tier — see `~/.claude/skills/_shared/orchestrator-protocol.md` for the full model.

## Note on adapters

Both adapters install the same `domain/skills/` source, so the delegation model and skill files are identical — only the invocation surface differs (Claude Code: conversational, via the `CLAUDE.md` stub; OpenCode: conversational, via `AGENTS.md` and the primary agent).

## Uninstall

Remove the orchestrator block from `~/.claude/CLAUDE.md` (between the markers) and delete `~/.claude/skills/` (or just the `organic-*` and `_shared` subdirectories) plus `~/.claude/agents/*.md`. The installer does not provide an automated uninstall command.
