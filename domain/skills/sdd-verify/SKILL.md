---
name: sdd-verify
description: "Trigger: orchestrator launches verify after apply (and code-audit gate). Validate change against ACs per group, run tests, emit Spec Compliance Matrix with failure_class, produce verification report."
disable-model-invocation: true
user-invocable: false
---

## Activation Contract

Run when the orchestrator launches the verify phase for an SDD change after apply completes. Produce: `verification-report.md` and `state.yaml` update. Never modify application code, specs, design, or any SDD artifact other than `state.yaml`.

## Hard Rules

- Follows common rules: read-only on app code, write-scope, envelope-always, seniority — see `_shared/common-rules.md`.
- Verify against specs, not opinion. If the code does what the spec says, it passes. -- because opinion-based verdicts produce false positives that erode orchestrator trust and cause unnecessary re-engage cycles.
- Evidence required. Every verdict needs a command output, file:line reference, or test name:result. "Looks correct" is not evidence. -- ECO-944 showed that framework assumptions without evidence produced 4 cascading bugs that required individual re-engage cycles.
- Run real commands. Compile, lint, test. Run compile, lint, and test commands — report actual exit codes. -- guessing build status caused 3 false-PASS verdicts in early SDDs.
- Tests are behavioral proof. A spec scenario is only COMPLIANT when a test that covers it has PASSED. Code existing in the codebase is structural evidence (Step 7), not behavioral proof (Step 9). -- structural evidence (file existence, line presence) confirms existence but not correctness; only test execution proves behavior.
- Citations resolve mechanically. Every COMPLIANT or FAILING scenario row carries exactly one citation token: `` `path::test_name` `` (path repo-relative, test_name a verbatim string in that file) or `` `checklist:C-{N}` `` (meta-project Bash criterion). Step 15b runs `_shared/scripts/check-verify-citations.sh` and downgrades unresolved rows to UNTESTED before the verdict. -- because a fabricated citation passed encryption ACs as COMPLIANT in a real run (2026-06-10 android-offline-first: the cited test did not exist, real coverage was zero, and no gate caught it until post-archive audit); a fabricated citation cannot survive a grep.
- Bash is available — see "Tool Availability by Phase: verify" in `_shared/sdd-orchestrator-protocol.md`. Step 5 (test execution) is non-skippable: if unable to execute, return `status: needs_input` listing the required commands — never declare COMPLIANT without test execution evidence.
- Spec Compliance Matrix per group: every scenario gets exactly one of {COMPLIANT | FAILING | UNTESTED | PARTIAL}. The matrix is per logical group (REQ-VERIFY-006) when tasks.md has >1 group. -- see Step 9 and Step 11.
- `failure_class` in envelope: emit exactly one of {implementation | test_contract | spec_gap} per failed group (null on PASS). Priority: spec_gap > test_contract > implementation. -- see Step 15 (envelope composition).
- `failure_class` breakdown in `executive_summary` (REQUIRED on FAIL): first line MUST be a scenario-fail count + failed-groups breakdown by class. Format: `{N} scenario fails across {M} failed groups — {k1} test_contract / {k2} implementation / {k3} spec_gap.` Burying the breakdown in findings forces the orchestrator to read the full report before re-engage routing. Empirical pattern (2026-05-19 zod-pipe-saneamiento retro): "27 fails" with no class breakdown read as apocalyptic; the truthful "27 fails, 5/6 groups test_contract → pipeline artifact, not production bugs" reframes the decision in one line. -- see Step 16 (envelope composition).
- Absorbed scope/coverage checks (Check 1-4): diff vs declared scope, resolution coverage, audit-trail completeness, test discovery sanity. -- see Step 3b inserted between Step 3 and Step 4.

## Decision Gates

| Condition | Action |
|---|---|
| `phases.apply.status` is not `done` | Return `status: blocked` immediately. |
| CRITICAL finding (broken build, failing test, MUST req missing) | Block archive. List in Issues/CRITICAL. Overall verdict: FAIL. |
| WARNING finding (SHOULD gap, scope creep, design deviation) | Flag and continue. Overall verdict: PASS WITH WARNINGS. |
| SUGGESTION only | Record. No gate action. Verdict not downgraded. |
| Failure in `baseline.md` | Not a regression -- pre-existing. Report as pre-existing (baseline.md match) — exclude from the CRITICAL count. |
| Design drift that has a `state.yaml.decisions:` entry with `task_ref` | Approved drift. Carry verbatim into Drift Summary table. Not scope creep. |
| Missing test infrastructure (no runner, no tests) | Execute Manual Review Checklist rows as Bash; map to COMPLIANT/FAILING/UNTESTED per row. |
| `baseline_path` not injected but `baseline.md` exists on disk | Recover from disk. Report `context_resolution: fallback`. |
| `config.yaml.stack.testing: []` (meta-project) | Execute Manual Review Checklist rows as Bash; map to COMPLIANT/FAILING/UNTESTED per row. |

## Execution Steps

1. Read `_shared/context-protocol.md` (startup), `_shared/persistence-contract.md` (write rules). Validate injected context. Recover missing fields from `state.yaml`; report `context_resolution: fallback` if any were missing.
2. Load: `config.yaml` (stack, verify commands), `state.yaml` (`phases.apply.status`, apply progress, `decisions[]`), `tasks.md` (full), delta specs (all domains), `proposal.md` (ACs), `design.md`. If `baseline.md` exists, read it -- failures present there are pre-existing, not regressions.
3. File inventory: for each task/file pair verify CREATE exists, MODIFY exists-and-changed, REMOVE is gone. Run `git diff --name-only HEAD`; files in diff but not in any task = scope creep WARNING.

   **Step 3b — Absorbed scope/coverage checks (REQ-VERIFY-004):**
   - Check 1 — Diff vs declared scope: `git diff --name-only HEAD` vs tasks.md `Files:` blocks. Files in diff but not declared = WARNING per file.
   - Check 2 — Resolution coverage: grep `decisions[].decision` keywords against diff. Zero hits for a decision keyword = WARNING (may indicate unresolved change).
   - Check 3 — Audit-trail completeness: count `decisions[]` apply-phase entries vs `fix:` commits. `fix:` commits > decisions[] entries = WARNING (unlogged deviation).
   - Check 4 — Test discovery sanity: count new `*.spec.{ext}` files vs test count delta in test runner output. Significant discrepancy = WARNING. Meta-project: skip with note ("meta-project, no test runner").

4. Build: run compile command from `config.yaml`. Compilation error = CRITICAL. Run lint on created/modified files; lint error = CRITICAL, lint warning = WARNING.
5. Test execution: run new test files created by tasks (CRITICAL if failing). Run regression suite for affected modules (CRITICAL if regressions). No test runner configured = WARNING, not CRITICAL. Meta-project: execute Manual Review Checklist Bash criteria; map each row to COMPLIANT/FAILING/UNTESTED.
6. Task criteria: for each task verify each checklist item. Unmet critical criteria = CRITICAL; unmet optional criteria = WARNING.
7. Static correctness: for each delta-spec requirement, read implementing files (use tasks.md traceability). Assess Given/When/Then structurally. Verdict per requirement: Implemented / Partial / Missing. MUST gaps = CRITICAL; SHOULD gaps = WARNING.
8. Design coherence: for each key design decision verify the approach was followed. Deviation = WARNING (design is a guide, not law).
9. Behavioral compliance per group: cross-reference every spec scenario against Step 5 test results. COMPLIANT = test exists AND passed. FAILING = test failed = CRITICAL. UNTESTED MUST = CRITICAL (WARNING if no test infra). UNTESTED SHOULD = WARNING. Produce per-group results for Step 11.
10. **Step 8b -- Drift Summary:** Read `state.yaml.decisions:`. For each entry with `phase` and `task_ref`, write one row in the Drift Summary table -- these are approved drift, not scope creep. Unaccounted drift (diff files not in tasks.md and not in any `decisions:` entry) = WARNING. See [references/report-format.md](references/report-format.md) "Absorbed Checks Summary" subsection.

   Additionally, scan `state.yaml.decisions[]` for any entry where `phase: apply`
   AND `entry.date >= state.yaml.created` (ISO 8601 lexicographic comparison — detects
   in-lifecycle apply-authored entries). For each match:

   Emit one WARNING row in the Drift Summary with text:
   > "decisions[] entry at index {i} written by apply (phase: apply) — apply MUST NOT
   > author decisions per Seniority Model (REQ-CR-008); legacy archived entries
   > (date < state.yaml.created) are exempt."

   Severity: WARNING (not CRITICAL). Legacy entries (date < created) are silently treated
   as approved legacy drift — no WARNING.
11. **Spec Compliance Matrix (REQ-VERIFY-006):** When tasks.md has >1 group, build a per-group matrix. For each group G{N}: collect all REQ-IDs covered by tasks in that group; for each REQ-ID, find its Given/When/Then scenarios in the delta spec; assign verdict {COMPLIANT | FAILING | UNTESTED | PARTIAL}. Format per [references/report-format.md](references/report-format.md) "Spec Compliance Matrix" section.
12. AC coverage: for each AC, combine static (Step 7) and behavioral (Step 9) verdicts. COVERED = all traced reqs Implemented + Compliant. PARTIAL = some gaps. NOT COVERED = missing or failing. Report in `| AC | Status | Evidence |` table.
13. **failure_class composition (REQ-VERIFY-003):** For each failed group, assign exactly one class using priority order:
    - `spec_gap` — any MUST scenario UNTESTED in the group (spec decomposition incomplete)
    - `test_contract` — any FAILING where the test assertion disagrees with the spec (not the code)
    - `implementation` — any FAILING where the code fails a correct test
    - `null` — no failures in this group (PASS)
14. Overall verdict: FAIL if any CRITICAL. PASS WITH WARNINGS if warnings only. PASS if zero findings.
15. Write `verification-report.md` per [references/report-format.md](references/report-format.md). Include: Spec Compliance Matrix (per-group), Re-engage Routing Hint (failure_class + failed_groups + rationale), Absorbed Checks Summary, Drift Summary, Citation Audit.

    **Step 15b — Citation audit (mechanical):** run `bash {install_dir}/skills/_shared/scripts/check-verify-citations.sh .ai-team/changes/{change}/verification-report.md .` from the repo root and paste its output verbatim into the report's "Citation Audit" section. Each `UNRESOLVED` line → downgrade that scenario to UNTESTED, recompute Steps 13-14, rewrite the report, re-run the script until it exits 0. Script missing on disk → perform the same check manually (extract `path::test_name` tokens from COMPLIANT/FAILING rows; verify the path exists and the name greps in the file with `grep -F`) and write `citation-audit: manual fallback` in the section.
16. Update `state.yaml`: `phases.verify.status → done`, `phases.verify.completed → ISO 8601`, `phases.verify.agent → sdd-verify`, `current_phase → verify`, `updated → now`. Compose `executive_summary` — when overall verdict is FAIL, the **first line MUST be** `{N} scenario fails across {M} failed groups — {k1} test_contract / {k2} implementation / {k3} spec_gap.` where N = sum of FAILING + UNTESTED-MUST scenarios across all failed groups, M = count of failed groups, and k1/k2/k3 = counts of failed groups bucketed by their assigned `failure_class` from Step 13. Non-FAIL verdicts omit this line. Return envelope per [references/envelope-examples.md](references/envelope-examples.md).

## Output Contract

Write `.ai-team/changes/{change}/verification-report.md`. Update `state.yaml`. Return a result envelope with `status`, `executive_summary` (on FAIL the first line MUST be `{N} scenario fails across {M} failed groups — {k1} test_contract / {k2} implementation / {k3} spec_gap.` — see Step 16; non-FAIL verdicts omit), `artifacts`, `failure_class` (null or one of {implementation | test_contract | spec_gap}), `failed_groups` (list of group IDs), `citations_unresolved` (int from Step 15b; 0 on any non-FAIL verdict — unresolved rows were downgraded to UNTESTED), `next_recommended`, `risks` (if any), `model_used`, `context_resolution`.

## References

- [references/report-format.md](references/report-format.md) — full verification-report template including Spec Compliance Matrix, Absorbed Checks Summary, Re-engage Routing Hint sections; load at Step 15.
- [references/envelope-examples.md](references/envelope-examples.md) — PASS, PASS WITH WARNINGS, FAIL, Blocked envelope variants; load at Step 16.
- [references/edge-cases.md](references/edge-cases.md) — Apply Partially Failed, No Tests, No Delta Specs, Large Codebase, Compilation Passes But Code Wrong, Resumed Verification, Verify Commands Missing, Design Missing; load when an unexpected condition arises.
- `../_shared/context-protocol.md` — startup sequence; load first.
- `../_shared/persistence-contract.md` — write rules, `decisions:` schema; load at Step 1.
- `../_shared/result-envelope.md` — envelope schema; load at Step 16.
- `../_shared/evidence-protocol.md` — Rules 1-6 (Rule 3 governs real-command execution; Rule 6 governs orchestrator post-apply audit handoff).
- `../_shared/common-rules.md` — consolidated principles; Logical group definition for per-group matrix.
- `../_shared/spec-convention.md` — REQ-ID format, RFC 2119 keywords; load at Step 7.
