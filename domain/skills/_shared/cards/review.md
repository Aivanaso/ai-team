# Card: review

> Read when: the implementer of the current attempt settled `ok`/`warning` and the phase is not committable yet.

## 1. Tier — from the diff, never from size or memory

```
ai-team tier <0|1|2> --phase <n> --reason "<one line>"
```
| Tier | The diff | Lenses |
|---|---|---|
| 0 | docs, comments, non-runtime config, pure renames | none |
| 1 | any other code change | `organic-reviewer` |
| 2 | auth/authz, crypto, secrets, payments, PII, migrations or deletion, untrusted-input parsing, permission checks, public contracts, a blocking gate of the review plane | reviewer + `organic-security` (mode `code-audit`) |

Escalate, never de-escalate: a worker envelope with failed checks, skipped verification or
self-declared uncertainty adds one tier.

## 2. Lenses (sonnet · high; the two may run together)

```
ai-team acquire reviewer --phase <n>        [ai-team acquire security-audit --phase <n>]
```
Inject: `design` (or none), `phase_file`, `group_files` (expected files ∪ artifacts),
`tier`, `tier_reason`, `attempt`, the implementer's `check_results` and `decisions_taken`,
`report_destination: .ai-team/reviews/<task>-phase-<n>-attempt-<k>-<lens>.md`; from attempt 2,
`prior_report` and `delta_scope {findings_to_verify, changed_files, prior_verdict_history}`.
The reviewer checks **conformity** (every decision and every scenario of the phase met,
nothing missing, nothing extra) and correctness, and re-runs the checks. Security at tier 2
verifies the `## Seguridad` measures are implemented.

Settle with `--report`: the machine validates the receipt block; a violating report keeps the
ticket open — relaunch the lens with the printed lines.

## 3. Verdict

- `review-clear` (no CRITICAL) → card: commit.
- `review-blocked` → next attempt with the findings (card: delegate). Attempts 2–4 resume the
  same implementer; findings that do not decrease between attempts mean the fix class is
  wrong: reopen the design, not another attempt.
- After the 6th attempt: rule each open CRITICAL or stop.
  `ai-team ruling <ticket> --finding F-n --text "<why>" --cost-if-wrong "<what>"`
- Pre-existing or out-of-phase CRITICAL/MAJOR findings: `--defer F-n,…` at settle time
  (they land in `.ai-team/tech-debt.md`); fixing one inside this task needs the user's yes.
- MINOR by reading with no trigger: report as one line, no re-engage.

You never touch code yourself; a small fix is still an attempt.
