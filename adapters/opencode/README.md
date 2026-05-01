# ai-team — OpenCode Adapter

Installs the ai-team SDD framework into OpenCode (`~/.config/opencode/`).

## Prerequisites

- [OpenCode](https://opencode.ai/) installed
- [`jq`](https://jqlang.github.io/jq/) installed (`brew install jq` / `apt install jq`)

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
| SDD phase skills | `~/.config/opencode/skills/sdd-*/` |
| Shared protocols | `~/.config/opencode/skills/_shared/` |
| Slash commands | `~/.config/opencode/commands/sdd-*.md` |

## Usage

1. Select the **`sdd-orchestrator`** agent in OpenCode
2. Use slash commands to drive the SDD pipeline:

```
/sdd-new <change-name>     Start a new SDD change (scout → propose → approval gate)
/sdd-continue [change]     Resume an active change (runs next dependency-ready phase)
/sdd-explore <topic>       Investigate a topic without starting SDD
/sdd-baseline <domain>     Document existing code as a baseline spec
/sdd-status [change]       Show change progress
```

## Slash Command Naming

OpenCode adapter uses `/sdd-new`, `/sdd-continue`, etc. The Claude Code adapter uses `/ai-team new`, `/ai-team continue`. The underlying SDD pipeline is identical — only the command prefix differs.

## No Plan Mode

The OpenCode adapter does not implement Claude Code's plan-mode safety net. The mandatory classification gate is the only gate before implementation begins.

## opencode.json Merge Behavior

On each install run, the adapter deep-merges its `agent` definitions into your existing `opencode.json`. Rules:

- All `sdd-*` agent entries are replaced (latest definitions win)
- Other agents in your `opencode.json` are preserved
- `permission.task` stale `allow` entries may persist from previous installs — this is safe for ai-team re-installs because the overlay always writes all 8 allows

## Idempotency

Safe to re-run. Re-running after a `git pull` updates all skills, AGENTS.md, opencode.json, and slash commands. No manual cleanup needed.

## Uninstall

Remove manually:

```bash
rm -f ~/.config/opencode/AGENTS.md
rm -rf ~/.config/opencode/skills/sdd-*
rm -rf ~/.config/opencode/skills/_shared
rm -f ~/.config/opencode/commands/sdd-*.md
# Edit ~/.config/opencode/opencode.json to remove sdd-* agent entries
```
