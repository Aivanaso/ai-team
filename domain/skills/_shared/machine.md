# The `ai-team` machine

> One JSON per task under `.ai-team/tasks/`. The machine owns what must always happen
> (timestamps, ticket conditions, attempt counts, receipt validation, the balance); the
> orchestrator keeps only what needs judgment. Design note: `memorias-ivan/_diseno__2026-09-05-rediseno-orquestador.md` §5, §8, §10.

Runs anywhere inside a project that has an `.ai-team/` directory (the CLI walks up from
the working directory). Python 3 standard library only. Installed copy:
`~/.claude/skills/_shared/scripts/ai-team`.

## Vocabulary

| Word | Meaning |
|---|---|
| task | the whole user request; one JSON, `kind: bounded \| large`, `status: active \| paused \| done` |
| design | what and why — `.ai-team/designs/<task>.md`, approved by the user (`status: approved` in its frontmatter); none for a bounded task |
| plan | how — `.ai-team/plans/<task>.md`, **generated** from the design plus the scout's scope report; one section per phase |
| phase | a deliverable slice of the plan; carries files, roots, checks, constraints; `status: pending \| implementing \| reviewing \| committed` |
| ticket | permission for one sub-agent launch; `kind: scout-map \| security-threat-model \| scout-scope \| implementer \| reviewer \| security-audit \| retro` |
| attempt | implementer cycle inside a phase; 1 = fresh; 2-4 = resume the same implementer with the findings (`SendMessage`); 5-6 = fresh implementer, stronger model; 7 = denied, reopen the design |
| ruling | the orchestrator's recorded adjudication of one open finding after the attempts are spent |
| balance | the settled tickets: tokens, tool uses, duration, outcome — computed on demand from the tickets |

## Verbs

| Verb | Effect |
|---|---|
| `status [--json]` | the task in progress, design status and security, phase N of M, open tickets, attempts used, pending question, **what is allowed now**, and the card for the current moment |
| `new <slug> --kind bounded\|large [--design <path>]` | creates the task JSON (slug is date-prefixed if it is not already) |
| `design approve <path>` | flips the design frontmatter to `status: approved` with `approved_at`; only after the user's "yes" |
| `plan generate [--scope <report.md> \| --scope-skipped "<why>"] [--check-timeout s]` | large: plan from the approved design plus the scope report's final fenced json block; the scout's calibrations travel into the plan, an un-run check becomes an open question. Under `--scope-skipped` the machine runs the design's checks itself. Bounded: `plan generate --objective … --decision … --check … --failure … --out-of-scope … --file …` (repeatable flags) writes a one-phase plan; the machine runs each `--check` now and records its calibration, `--failure` says how it fails (a known failure's signature when green today, why it is red today otherwise). A zero-work green or a timeout refuses the plan; a red-today check is printed with a `!` |
| `plan amend --phase n --reason "<why>" [--file p]… [--check c --failure f]… [--check-timeout s]` | widens a phase after an implementer `blocked` with a `scope_report`, or records a check the orchestrator ran after the scout could not; each `--check` runs now and is recorded calibrated; recorded in the plan and the JSON |
| `phase extract <n>` | writes `.ai-team/plans/<task>/phase-<n>.md`, the implementer's input |
| `tier --phase n <0\|1\|2> --reason "<one line>"` | the evidence tier of the phase's diff, decided after the candidate exists |
| `acquire <kind> [--phase n]` | checks the conditions below and issues a ticket, or refuses saying what is missing. Prints how the attempt is launched: implementer 1 fresh · 2–4 resumed · 5–6 fresh on the stronger model; a lens at attempt ≥ 2 gets `delta pass -- inject prior_report <path>` when an earlier report exists, else `full pass -- inject prior_report: none` |
| `settle <ticket> --outcome … [--model … --tokens … --tool-uses … --duration …] [--report <path>] [--defer F-1,…]` | closes the ticket with the harness figures. Reviewer / security-audit: validates the report's receipt block first; scout-scope: validates every check's calibration first; a violating report does not settle. Implementer: records the tree fingerprint; lens: the tree must match the implementer's, else the ticket stays open |
| `ruling <ticket> --finding <id> --text "<why>" --cost-if-wrong "<what>"` | adjudicates one open finding of a settled lens ticket |
| `commit-check --phase n` | exit 0 when the phase may be committed (tier 0 with a clean implementer, or the lens receipts re-validated and clear, or blocked only by ruled CRITICALs) |
| `phase done <n> --commit <hash>` | records the commit and flips the phase to `committed` (runs `commit-check` first) |
| `debt fix --match "<text>" --commit <hash>` | flips matching `.ai-team/tech-debt.md` rows to `fixed (<hash>)` |
| `pause [--question "<one line>"]` / `resume [<task>]` | parks / reactivates a task |
| `close` | every phase committed and no open ticket → `status: done` |
| `receipt check <report.md> [project_root]` | validates a review report's receipt block on its own (exit 0 / 1 VIOLATION / 2 ERROR) |
| `hook <pre-tool-use\|session-start>` | the Claude Code hook entry points; JSON on stdin |

Outcomes: `ok | warning | needs_input | blocked | failed | infra-death`. `infra-death` needs no figures and does not count as an attempt.

## Ticket conditions (`acquire`)

| Kind | Requires |
|---|---|
| scout-map | a task in progress |
| security-threat-model | a design in `draft` whose frontmatter says `security: pending` |
| scout-scope | design `approved` |
| implementer | large: design `approved`; a plan with phase n; scope report recorded or skipped with a reason; earlier phases committed; fewer than 6 attempts on the phase (the 7th says "reopen the design"); at least one calibrated acceptance check on the phase (a phase whose checks were all demoted to open questions names them and the `plan amend --check … --failure …` that records one) |
| reviewer | tier ≥ 1 declared; the implementer ticket of the current attempt settled `ok` or `warning` |
| security-audit | as reviewer, tier 2 |
| retro | task `done` |

One ticket open at a time, with one exception: several `scout-map` tickets may be open together. The two review lenses run one after the other (`reviewer`, then `security-audit`): they audit one working tree, and a mutation probe by one would be a phantom defect for the other.

**Tree fingerprint.** `settle` of an implementer records the working tree's git tree id on the ticket (`tree`: tracked changes and untracked files, minus what the project ignores). `settle` of a lens computes it again and compares with the implementer ticket of the same attempt: a tree that moved names the paths and keeps the lens ticket open -- a mutation probe ends with a byte-for-byte restore.

## Task JSON

```json
{
  "schema": 1, "task": "2026-09-05-slug", "kind": "large", "status": "active",
  "created_at": "…Z", "updated_at": "…Z", "closed_at": null,
  "design": ".ai-team/designs/2026-09-05-slug.md", "plan": ".ai-team/plans/2026-09-05-slug.md",
  "scope_report": ".ai-team/explorations/2026-09-05-slug-scope.md", "scope_skipped": null,
  "pending_question": null,
  "phases": [ { "n": 1, "title": "…", "status": "pending", "attempts": 0, "tier": null, "tier_reason": null, "commit": null, "amendments": [] } ],
  "tickets": [ { "id": "t1", "kind": "implementer", "phase": 1, "attempt": 1, "issued_at": "…Z", "settled_at": null,
                 "outcome": null, "model": null, "tokens": null, "tool_uses": null, "duration_s": null,
                 "report": null, "verdict": null, "findings": null, "deferred": [], "tree": null } ],
  "rulings": [ { "at": "…Z", "ticket": "t7", "finding": "F-2", "text": "…", "cost_if_wrong": "…" } ]
}
```

Timestamps are the machine's.

## Inputs the machine parses

**Design file** (`.ai-team/designs/<task>.md`): frontmatter `title`, `created_at`, `status: draft | approved`, `map_report`, `security: not-needed | pending | done`; sections by `## ` heading, Spanish or English names accepted (`Objetivo`/`Objective`, `Decisiones`/`Decisions`, `Seguridad`/`Security`, `Fuera de alcance`/`Out of scope`, `Fases`/`Phases`, and under `## Diseño`/`## Design` the sub-heading `### Superficies nombradas`/`### Named surfaces`). Each phase is a `### Fase N — Title` (or `### Phase N — Title`) block with the lines `Entrega:`/`Delivers:`, `Escenarios:`/`Scenarios:` followed by `- ` bullets, and `Check:` followed by one backticked command per line or bullet.

**Scope report** (scout, `mode: scope`): a Markdown report whose final fenced ```json block is
`{"kind": "scope-report", "phases": [{"n": 1, "expected_files": [{"action": "MODIFY", "path": "…", "evidence": "file:line"}], "acceptance_checks": [{"command": "…", "expect": "exit N", "calibration": {…}}], "constraints_candidates": ["…"], "open_questions": ["…"]}]}`.
Every phase of the design must appear. A phase absent from the report fails `plan generate`.

**Calibration** of an acceptance check (scope report, plan, phase file) -- what the command did on the current tree:
- green today: `{"executed": true, "exit_code": N, "digest": "<last output lines>", "failure_signature": "<how a known failure shows>"}` with `exit_code` equal to `expect`'s N;
- red today: `{"executed": true, "exit_code": M, "digest": "…", "red_reason": "<why it fails now and that the phase turns it green>"}`;
- not run: `{"executed": false, "target": "file:line", "reason": "…"}` and no `expect` -- `plan generate` moves it to the phase's `open_questions`.
`expect` is always `exit N`. A digest that is a zero-work output (`No tests found`, `0 files analyzed`, `Tests: 0 total`) is refused. A phase whose design has checks and whose scope entry calibrates none and questions nothing fails `plan generate`. Checks the machine runs itself add `"tree": "<short HEAD>[+dirty]"`.

**Review report** (reviewer, security code-audit): a Markdown report whose final fenced ```json block is the Review Receipt (`result-envelope.md` → Review Receipt).

## Engram mirror

`design approve`, `close` and `settle --defer` call `engram save` when the binary is on `PATH`; failure or a timeout prints one warning and the verb still exits 0. Nothing is ever read back from engram to decide.
