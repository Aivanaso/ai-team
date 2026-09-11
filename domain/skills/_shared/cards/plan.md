# Card: plan

> Read when: the design is `approved` and `ai-team status` shows no plan.

The plan is **generated**, never written by you. Its inputs are the approved design and the
scout's scope pass.

## 1. Scope pass (scout, mode `scope`)

`ai-team acquire scout-scope` — sonnet, effort medium. Inject the design path and the map
reports. For every phase of the design the scout returns, with `file:line` evidence:
expected files (construction sites swept), acceptance checks **each with its calibration**
(run on the current tree: exit code, output digest, and how it fails), anchored constraint
candidates, open questions. Its report ends with the json block the machine reads
(`_shared/machine.md` → "Scope report" and "Calibration"). Settle with `--report`: the machine
validates every calibration; a violating report keeps the ticket open — relaunch the scout
with the printed lines.

Skip it only when the map pass already documented every named surface line by line:
`ai-team plan generate --scope-skipped "<why>"` — the machine then runs the design's checks
itself and records what it saw.

## 2. Generate

```
ai-team plan generate            # uses the recorded scope report
```
Objective → objective; Decisiones (+ Seguridad measures) → constraints, verbatim; Fuera de
alcance → out of scope; each phase's scenarios and calibrated checks → acceptance checks; a
check the scout could not run → an open question; the scout's files → expected files and
edit roots.

## 3. Read the `!` lines, then verify before the first delegation

The machine prints one `!` line per check that needs your judgment:
- **red today** — the scout's `red_reason` says the phase itself turns it green. Agree, or the
  check is a pre-existing failure: fix the baseline or drop the check before delegating.
- **not calibrated** — run the command yourself, then record it so the machine keeps it:
  `ai-team plan amend --phase <n> --reason "ran it: <what it showed>" --check "<cmd>" --failure "<how it fails>"`.
  A phase with no calibrated check does not reach an implementer.

Then:
- Every link of the flow the design describes has a file in some phase, or an open question.
- Every scout constraint candidate is either a design decision already, or a question to
  the user — adopted or dropped in the open, with the user's word.
- The plan names no mechanism the design did not decide.

Present the phase order to the user once, in their language. Their yes opens phase 1.

## Widening a phase later

An implementer that returns `blocked` with a scope report (a file it needs, a check that
cannot run) is a plan defect, not a worker defect:
```
ai-team plan amend --phase <n> --reason "<what was missing and how it was proven>" [--file <path>]… [--check "<cmd>" --failure "<how it fails>"]…
ai-team phase extract <n>
```
Each `--check` runs now and enters the plan calibrated. Then the next attempt (card: delegate).
The plan file is the machine's: `plan amend` is the only way it changes.
