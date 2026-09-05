# ai-team

A tool-agnostic framework for delegated software work with a mechanical spine: a task state
machine gates every sub-agent launch, the plan is generated from an approved design, and the
orchestrator keeps only the decisions that need judgment.

## How It Works

The orchestrator (your AI coding tool's main conversation) classifies each request aloud,
writes the design **with** you when the change is large, and delegates each phase of a
generated plan to a sub-agent. What must always happen is not asked of the model — it is
taken away from it and given to the machine.

```
request ─► classify aloud ─┬─ question        → answer, nothing saved
                           ├─ bounded change  → 4 approved lines → one-phase plan → implementer
                           └─ large change    → map pass → design (approved by you) → threat-model?
                                                → scope pass → plan generated → phase by phase
each phase: implementer (attempt 1..6) → tier from the diff → reviewer [+ security] → commit
```

| Piece | What it owns |
|---|---|
| `ai-team` machine (`domain/skills/_shared/scripts/ai-team`, Python stdlib) | one JSON per task under `.ai-team/tasks/`; tickets for every launch; attempts per phase; plan generation; receipt validation; the commit gate; the balance |
| two hooks (Claude Code) | `PreToolUse` on `Agent`: an `organic-*` launch without a ticket is denied with the exact command to run; `SessionStart`: `ai-team status` lands in the session's context |
| eight cards (`domain/skills/_shared/cards/`) | the orchestrator's judgment, one short card per moment: classify · design · plan · delegate · ingest · review · commit · close |
| five skills (`domain/skills/organic-*/`) | scout (bootstrap · map · scope), implementer, reviewer, security (threat-model · code-audit), retro |

### The design is the source of constraints

A large change has a design file (`.ai-team/designs/<task>.md`) written in conversation and
approved by you, section by section. Its **decisions** are invariants, never mechanisms (if the
sentence stays true when the function is rewritten from scratch, it is a decision). Its
**phases** carry given/when/then scenarios and a runnable check. When a design touches a
sensitive surface, `organic-security` threat-models the file before approval and its
requirements become decisions. The plan is generated from the design plus the scout's scope
pass — the orchestrator never writes it.

### Attempts, not re-briefs

Per phase: attempt 1 is a fresh implementer; attempts 2–4 resume the same implementer with the
reviewer's findings; 5–6 are a fresh implementer on the stronger model; a 7th is denied — the
design is reopened. Findings that do not decrease between attempts mean the fix class is wrong.

### Evidence-tiered review

| Tier | Trigger | Review |
|------|---------|--------|
| **0** | docs, comments, non-runtime config, renames | none |
| **1** | any other code change | `organic-reviewer`: conformity to the design and phase, correctness, verification re-run |
| **2** | auth/authz, crypto, secrets, payments, PII, migrations, untrusted input, permission checks, public contracts | reviewer + `organic-security` code-audit (verifies the design's security measures are implemented) |

A lens writes one report whose final fenced json block is the Review Receipt; the machine
validates it when the ticket settles and again at `commit-check`. A blocked verdict is cleared
only by a further attempt or by a recorded ruling per CRITICAL finding.

## Project Structure

```
ai-team/
├── domain/skills/
│   ├── _shared/
│   │   ├── machine.md                # the machine's contract: verbs, ticket conditions, task JSON, parsed inputs
│   │   ├── cards/                    # orchestrator cards, one per moment (≤ 60 lines each)
│   │   ├── scripts/ai-team           # launcher → ai_team/ (cli, machine, receipt, design, plan, hook, debt, engram)
│   │   ├── context-protocol.md · persistence-contract.md · result-envelope.md · evidence-protocol.md · common-rules.md
│   │   └── skill-style-guide.md
│   ├── organic-scout/ · organic-implementer/ · organic-reviewer/ · organic-security/ · organic-retro/
├── adapters/
│   ├── claude-code/                  # install.sh, merge-hooks.py, templates/{CLAUDE.md,hooks.json,agents/}
│   └── opencode/                     # install.sh, templates/{AGENTS.md,opencode.json} — machine yes, hooks no
├── evals/                            # layer-3 evals: the orchestrator against fixture projects with stub agents
├── scripts/
│   ├── install.sh                    # adapter selector
│   ├── check-skill-budgets.sh        # SKILL.md ≤ 250 lines, cards ≤ 60
│   └── tests/                        # unittest suites: machine, hooks, design parser, receipt calibration, hook merge
└── config/                           # .ai-team/config.yaml reference and annotated template
```

## Installation

### Claude Code

```bash
./scripts/install.sh --adapter=claude-code
```

Copies skills to `~/.claude/skills/`, agents to `~/.claude/agents/`, registers the two hooks in
`~/.claude/settings.json` (backup first, foreign hooks untouched, idempotent) and injects a
short stub into `~/.claude/CLAUDE.md` between `<!-- ai-team:orchestrator -->` markers.

### OpenCode

```bash
./scripts/install.sh --adapter=opencode
```

Requires `jq`. Same skills and machine; no hooks (the discipline stays in `AGENTS.md` prose).

## A session, in short

```
~/.claude/skills/_shared/scripts/ai-team status        # what exists, what is allowed now, which card to read
ai-team new <slug> --kind bounded|large
ai-team design approve <path>                          # after your yes
ai-team plan generate [--scope <report> | --scope-skipped "<why>"]   # or --objective/--decision/--check/--file for bounded
ai-team phase extract <n> · acquire implementer --phase <n> · settle <ticket> --outcome … --model … --tokens … --tool-uses … --duration …
ai-team tier <0|1|2> --phase <n> --reason … · acquire reviewer --phase <n> · settle <ticket> … --report <report.md>
ai-team commit-check --phase <n> · phase done <n> --commit <hash> · close
```

Full contract: `domain/skills/_shared/machine.md`. Tests: `bash scripts/tests/run-script-tests.sh`.
Evals (cost tokens): `python3 evals/run.py`.

## Persistence

Everything lives under the project's `.ai-team/` (`domain/skills/_shared/persistence-contract.md`):
`tasks/` (the machine's JSON), `designs/`, `plans/`, `explorations/`, `reviews/`, `retros/`,
`tech-debt.md`, `config.yaml`. Engram, when installed, receives a mirror of approvals, closes
and deferrals — never read back to decide.

## License

MIT
