# Card: delegate

> Read when: `ai-team status` allows `acquire implementer --phase n`.

```
ai-team phase extract <n>                 # writes .ai-team/plans/<task>/phase-<n>.md
ai-team acquire implementer --phase <n>   # the ticket; its output names the attempt and the model
```

| Attempt | Who | Model · effort |
|---|---|---|
| 1 | fresh `organic-implementer` | sonnet · high |
| 2–4 | **the same** implementer, resumed with `SendMessage` and the findings | (its own) |
| 5–6 | fresh implementer | opus · high |
| 7 | denied — reopen the design (amend, approve, regenerate) | — |

## The launch prompt (attempt 1, 5, 6)

Paths, not content. Shape:

1. `You are the organic-implementer executor. FIRST ACTION: read your skill at <install_dir>/skills/organic-implementer/SKILL.md.`
2. `## Skill and Protocol Paths` — the SKILL.md, `_shared/context-protocol.md`, `persistence-contract.md`, `common-rules.md`, `result-envelope.md`, `evidence-protocol.md`.
3. `## Injected Context` — `project_root`, `current_iso_utc`, `install_dir`, `phase_file` (the extracted path), `plan`, `design` (or `none`), `attempt`, `strict_tdd` (only when config says so and a test runner is declared).
4. `## Skills to load before work` — matching rows of `.ai-team/skill-registry.md`, when any.
5. The UNTRUSTED CONTENT tail (`_shared/common-rules.md` → Principle 6), verbatim.

The phase file IS the contract: objective, constraints, scenarios, checks, files, roots. You
add nothing to it in the prompt. `Agent(model=…)` wins over the agent file's default.

## The resume message (attempts 2–4)

`SendMessage` to the attempt-1 agent: the reviewer's findings by id with `file:line`, the
case each fix must handle (never a patch to paste), the checks to re-run, "return a fresh
envelope". Batch every finding into one message.

## While it runs

Nothing. No reading the files it edits, no parallel fixes. When it returns: card: ingest.
