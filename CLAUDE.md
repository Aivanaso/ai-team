# ai-team — repository rules

This repository is the source of the `ai-team` framework: the orchestrator's cards, the five
`organic-*` skills, the shared protocols and the task state machine under
`domain/skills/`, installed into `~/.claude/skills/` by `scripts/install.sh`.

## Language

Every text an agent or the machine reads is written in English: the skills and cards, the
shared protocols, the design and plan templates, the machine's messages, the tests and the
commit messages. The conversation with the user runs in the user's language, and a quote
from the user stays verbatim in its own language. Canonical statement:
`domain/skills/_shared/common-rules.md` → Principle 7.

## Positive rules

A rule states what the agent does and which field or gate carries it. Write "a check is
`pass` only when executed in this cycle and its exit code observed", and the reader knows
the action; "never infer a check" leaves the alternative to be guessed and is processed less
reliably. A rule that matters becomes a schema field or a validator in the machine, and the
prose names that gate. "never" survives only where no positive form exists, and then names
the action to take instead. Canonical statement:
`domain/skills/_shared/skill-style-guide.md` → Prompt Composition Rules → Positive rules.

The same discipline applies to the machine's own output: an error names the missing thing
and the command that supplies it.

## Before every commit

```bash
scripts/tests/run-script-tests.sh        # the machine's suites: known negatives first
scripts/check-skill-budgets.sh           # SKILL.md ≤ 250 lines, cards ≤ 60
./scripts/install.sh --adapter=claude-code   # the installed copy is what runs
```

A new gate is proven able to fail before its green counts: write the test red, then break
the gate on purpose once it is green and watch the test go red again.

## Where things live

| Path | What |
|---|---|
| `domain/skills/_shared/machine.md` | the machine's verbs, ticket conditions, task JSON, calibration and tree fingerprint |
| `domain/skills/_shared/cards/` | the orchestrator's cards, one per moment |
| `domain/skills/_shared/scripts/ai_team/` | the machine (Python, stdlib only) |
| `scripts/tests/` | its unittest suites |
| `memorias-ivan/` | retros and design notes; the source of every change in this repo |
