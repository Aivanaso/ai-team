# Card: plan

> Read when: the design is `approved` and `ai-team status` shows no plan.

The plan is **generated**, never written by you. Its inputs are the approved design and the
scout's scope pass.

## 1. Scope pass (scout, mode `scope`)

`ai-team acquire scout-scope` — sonnet, effort medium. Inject the design path and the map
reports. For every phase of the design the scout returns, with `file:line` evidence:
expected files (construction sites swept), acceptance checks verified runnable **and able to
fail**, anchored constraint candidates, open questions. Its report ends with the json block
the machine reads (`_shared/machine.md` → "Scope report"). Settle with `--report`.

Skip it only when the map pass already documented every named surface line by line:
`ai-team plan generate --scope-skipped "<why>"`.

## 2. Generate

```
ai-team plan generate            # uses the recorded scope report
```
Objective → objective; Decisiones (+ Seguridad measures) → constraints, verbatim; Fuera de
alcance → out of scope; each phase's scenarios and checks → acceptance checks; the scout's
files → expected files and edit roots.

## 3. Verify before the first delegation

- Every link of the flow the design describes has a file in some phase, or an open question.
- Spot-check one acceptance check yourself: it runs, and a known failure makes it fail. A
  zero-work green (`No tests found`, `0 files analyzed`) is a fail, never a pass.
- Every scout constraint candidate is either a design decision already, or a question to
  the user — never silently adopted, never silently dropped.
- The plan names no mechanism the design did not decide.

Present the phase order to the user once, in their language. Their yes opens phase 1.

## Widening a phase later

An implementer that returns `blocked` with a scope report (a file it needs, a check that
cannot run) is a plan defect, not a worker defect:
```
ai-team plan amend --phase <n> --reason "<what was missing and how it was proven>" [--file <path>]… [--check "<cmd>"]…
ai-team phase extract <n>
```
Then the next attempt (card: delegate). Never edit `.ai-team/plans/*.md` by hand.
