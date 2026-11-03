# Card: review

> Read when: the implementer of the current attempt settled `ok`/`warning` and the phase is not committable yet.

## 1. Tier — read from the diff

```
ai-team tier <0|1|2> --phase <n> --reason "<one line>"
```
| Tier | The diff | Lenses |
|---|---|---|
| 0 | docs, comments, non-runtime config, pure renames | none |
| 1 | any other code change | `organic-reviewer` |
| 2 | auth/authz, crypto, secrets, payments, PII, migrations or deletion, untrusted-input parsing, permission checks, public contracts, a blocking gate of the review plane | reviewer + `organic-security` (mode `code-audit`) |

Tiers only rise: a worker envelope with failed checks, skipped verification or
self-declared uncertainty adds one tier.

## 2. Lenses (sonnet · high; one after the other — reviewer, then security)

```
ai-team acquire reviewer --phase <n>        # settle it, then at tier 2:
ai-team acquire security-audit --phase <n>
```
Both audit the same working tree, so the machine issues one lens ticket at a time and
checks at settle that the tree is the one the implementer left (a probe restores what it
touched). Run security even when the reviewer blocked: attempt 2 fixes both lists at once.
Inject: `design` (or none), `phase_file`, `group_files` (expected files ∪ artifacts),
`tier`, `tier_reason`, `attempt`, the implementer's `check_results` and `decisions_taken`,
`report_destination: .ai-team/reviews/<task>-phase-<n>-attempt-<k>-<lens>.md`; from attempt 2,
what `acquire` printed: `prior_report <path>` plus `delta_scope {findings_to_verify, changed_files,
prior_verdict_history}` for a delta pass, or `prior_report: none` for a full pass (the earlier
attempt settled before any lens ran).
The reviewer checks **conformity** (every decision and every scenario of the phase met,
nothing missing, nothing extra) and correctness, and re-runs the checks. Security at tier 2
verifies the `## Seguridad` measures are implemented.

Settle with `--report`: the machine validates the receipt block; a violating report keeps the
ticket open — relaunch the lens with the printed lines.

## 3. Verdict

- `review-clear` (nothing above MINOR) or `review-gated` (highest MAJOR) → card: commit, where
  `commit-check` names every undispositioned MAJOR the receipt carries — a verdict is not a disposition.
- `review-blocked` (any CRITICAL) → next attempt with the findings (card: delegate). Attempts 2–4 resume the
  same implementer; findings that hold steady between attempts mean the fix class is
  wrong: the next step is the design (the machine denies a 7th attempt anyway).
- A finding that needs a new design decision before the next attempt: `ai-team design amend --phase <n> --reason "<why>" --decision "<text>"` (the design stays approved, the implementer gets the constraint), then the next attempt.
- A delta pass (attempt ≥ 2) accounts for every prior MAJOR/CRITICAL: re-listed under
  `findings`, closed with a citation (`closed: [{id, file, line}]`), or already ruled/deferred
  — `settle` refuses the report otherwise, naming what is missing.
- After the 6th attempt: rule each open CRITICAL or stop.
  `ai-team ruling <ticket> --finding F-n --text "<why>" --cost-if-wrong "<what>"`
- A MAJOR (pre-existing, out-of-phase, or accepted as is) is parked with `--defer F-n,…` at
  settle time (lands in `.ai-team/tech-debt.md`); a CRITICAL is always ruled — `--defer` on one
  is refused, naming `ai-team ruling`. Fixing a parked finding inside this task needs the
  user's yes.
- MINOR by reading with no trigger: one line in the report; the attempt stands.

A small fix is an attempt too: it goes through the implementer.
