# ai-team — OpenCode Adapter

Installs the ai-team organic evidence-tiered delegation framework into OpenCode (`~/.config/opencode/`).

## Prerequisites

- [OpenCode](https://opencode.ai/) installed
- `python3` on PATH — runs the `ai-team` machine (`skills/_shared/scripts/ai-team`); never used for the merge below
- [`jq`](https://jqlang.github.io/jq/) installed (`brew install jq` / `apt install jq`) — used
  only for the `opencode.json` deep-merge

## Install

```bash
# Via the top-level selector (recommended)
./scripts/install.sh --adapter=opencode

# Or directly
./adapters/opencode/install.sh
```

## What Gets Installed

| Artifact | Location |
|----------|----------|
| Orchestrator instructions | `~/.config/opencode/AGENTS.md` |
| Agent definitions | `~/.config/opencode/opencode.json` (merged) |
| Skills | `~/.config/opencode/skills/{organic-implementer,organic-reviewer,organic-scout,organic-security,organic-retro}/` |
| Shared protocols | `~/.config/opencode/skills/_shared/` |

## Usage

1. Select the **`orchestrator`** agent in OpenCode
2. Talk to it directly — there are no slash commands. It classifies every request aloud (question · bounded · large), designs large changes with you, runs the `ai-team` machine (`~/.config/opencode/skills/_shared/scripts/ai-team`) and delegates each phase (cards: `~/.config/opencode/skills/_shared/cards/`).

**Not covered on OpenCode:** the two Claude Code hooks (a launch without a ticket is denied; `status` printed at session start). On OpenCode the machine is the same but the discipline of calling it stays in `AGENTS.md` prose — see `.ai-team/tech-debt.md` in this repo for the pending OpenCode pass.

## opencode.json Merge Behavior

On each install run, the adapter deep-merges its `agent` definitions into your existing `opencode.json`. Rules:

- All of this framework's own agent entries are replaced (latest definitions win)
- Other agents in your `opencode.json` are preserved
- `agent.orchestrator.permission.task` (the orchestrator's sub-agent allow-list) is replaced wholesale on every install — a stale `allow` entry from a retired framework agent never persists
- Everything else under `agent.*` is additive-only — an agent key from a retired framework version (e.g. a name no longer in the overlay) is never auto-removed; a version migration that renames or drops agents needs a one-time manual `jq` cleanup of the stale keys

## Idempotency

Safe to re-run. Re-running after a `git pull` updates all skills, AGENTS.md, and opencode.json. Manifest-based pruning (`~/.config/opencode/.ai-team-manifest`) removes framework artifacts dropped by newer versions — with one blind spot: a pre-manifest install is never pruned on its first run; remove retired skill/command files manually once (or wipe the framework dirs and re-install).

## Uninstall

Remove manually:

```bash
rm -f ~/.config/opencode/AGENTS.md
rm -rf ~/.config/opencode/skills/organic-implementer ~/.config/opencode/skills/organic-reviewer \
       ~/.config/opencode/skills/organic-scout ~/.config/opencode/skills/organic-security \
       ~/.config/opencode/skills/organic-retro \
       ~/.config/opencode/skills/_shared
rm -f ~/.config/opencode/.ai-team-manifest
# Edit ~/.config/opencode/opencode.json to remove this framework's agent entries
```
