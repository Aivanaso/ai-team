# ai-team — Claude Code Adapter

Install the ai-team framework — a task state machine, two hooks, eight orchestrator cards and
five sub-agent skills — for use with Claude Code.

## Install

```bash
# Via adapter directly:
./adapters/claude-code/install.sh

# Or via the top-level selector:
./scripts/install.sh --adapter=claude-code
```

## Prerequisites

Claude Code installed. `python3` (standard library only) on `PATH`: it runs the machine
(`~/.claude/skills/_shared/scripts/ai-team`) that the hooks and the orchestrator call.

## What the install does

1. **Copies skills** from `domain/skills/` to `~/.claude/skills/{organic-implementer,organic-reviewer,organic-scout,organic-security,organic-retro}/` and `~/.claude/skills/_shared/` (protocols, `machine.md`, `cards/`, `scripts/ai-team` + the `ai_team/` package). The launcher is made executable and smoke-run.
2. **Rewrites skill paths** in the installed `.md` files — relative `skills/_shared/…` references become `~/.claude/skills/_shared/…`, idempotently.
3. **Copies agent files** to `~/.claude/agents/` (model and effort per worker live in their frontmatter).
4. **Registers two hooks** in `~/.claude/settings.json` through `merge-hooks.py`: `PreToolUse` on `Agent` (a sub-agent named `organic-*` needs an open ticket, else the launch is denied with the exact command to run) and `SessionStart` on `startup|clear|compact` (prints `ai-team status` into the session's context). A backup `settings.json.bak-<UTC stamp>` is written first; every foreign hook and setting survives byte for byte; re-running is idempotent.
5. **Injects the orchestrator stub** from `templates/CLAUDE.md` into `~/.claude/CLAUDE.md` between `<!-- ai-team:orchestrator -->` markers.

User content outside the markers, and every hook not ours, is never modified.

## How a session runs

The stub tells the orchestrator to run `ai-team status` before any delegation and to read the
one card the moment names (`~/.claude/skills/_shared/cards/<card>.md`). The machine's
contract — verbs, ticket conditions, the task JSON, the inputs it parses — is
`~/.claude/skills/_shared/machine.md`.

## Idempotency

Safe to re-run after pulling. The installer replaces the stub between markers, wipes and
re-copies each skill directory, writes `~/.claude/.ai-team-manifest` and prunes paths a newer
version no longer ships, and re-merges the hooks (removing its own handlers first, so two runs
give a byte-identical `settings.json`).

## Evals

`evals/run.py` (repo-local) runs the orchestrator against fixture projects with stub agents and
this checkout's hooks — see `evals/README.md`.

## Uninstall

```bash
python3 adapters/claude-code/merge-hooks.py ~/.claude/settings.json adapters/claude-code/templates/hooks.json --remove
```
Then remove the block between the markers in `~/.claude/CLAUDE.md`, and delete
`~/.claude/skills/{organic-*,_shared}` and the framework's `~/.claude/agents/organic-*.md`.
